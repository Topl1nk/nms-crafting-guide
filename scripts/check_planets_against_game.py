"""Check desktop/planet_gen.py against the game's own solar-system generator.

    No Man's Sky must be running (any menu or save will do; the generator's tables are loaded at start).

    uv run --with pefile --with unicorn --with numpy python scripts/check_planets_against_game.py [--game DIR] [--pid PID] [--systems 200]

The game's code is run in an x86 emulator (Unicorn): NMS.exe's routine that builds a solar system (0x635500) is called for random
addresses, over a copy of the running game's memory that is read when the emulator needs a page (read-only: nothing is ever written
to the game). What it makes of each system (the seed, size class, biome and variant of every body) is compared with
planet_gen.bodies(). The same copy is what shows that a piece of the port is exact, since the tables it needs (the game's own
structures in memory) are there as the game has them.

Build 184271 addresses (the first bytes of the routine are checked, and the script stops if they are not there). In a newer build
find the routine again: it is the one that calls the planet routine of the planet-data code (the callers of 0x16c44c0 each call
0x635500 just before it), which in turn calls the generator with the address, a working structure and a table holder.
"""
from __future__ import annotations

import argparse
import ctypes
import os
import random
import struct
import subprocess
import sys
from ctypes import wintypes as wt
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "desktop"))

STACK, STACK_SIZE = 0x10000000000, 0x2000000
HEAP, HEAP_SIZE = 0x10100000000, 0x8000000
STUBS, RET_AT, TEB, TLS = 0x10200000000, 0x10300000000, 0x10400000000, 0x10400010000
SYSTEM_RVA = 0x635500
START = bytes.fromhex("48895c2408" "4889742410" "48897c2418" "55" "488d6c24a9")  # the first bytes of 0x635500


class Process:
    """Read-only view of the running game."""

    def __init__(self, pid: int):
        self.k32 = k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.OpenProcess.restype = wt.HANDLE
        k32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
        self.handle = k32.OpenProcess(0x10 | 0x400, False, pid)  # PROCESS_VM_READ | PROCESS_QUERY_INFORMATION
        if not self.handle:
            sys.exit(f"cannot open process {pid} for reading")

        class Module(ctypes.Structure):
            _fields_ = [("size", wt.DWORD), ("id", wt.DWORD), ("pid", wt.DWORD), ("g", wt.DWORD), ("p", wt.DWORD), ("base", ctypes.c_void_p),
                        ("module_size", wt.DWORD), ("handle", wt.HMODULE), ("name", wt.WCHAR * 256), ("path", wt.WCHAR * 260)]
        k32.CreateToolhelp32Snapshot.restype = wt.HANDLE
        snap = k32.CreateToolhelp32Snapshot(0x18, pid)
        module = Module()
        module.size = ctypes.sizeof(module)
        self.base = 0
        ok = k32.Module32FirstW(snap, ctypes.byref(module))
        while ok:
            if module.name.lower() == "nms.exe":
                self.base = module.base
                break
            ok = k32.Module32NextW(snap, ctypes.byref(module))
        k32.CloseHandle(snap)
        if not self.base:
            sys.exit(f"process {pid} is not NMS.exe")

    def read(self, address: int, size: int) -> bytes:
        buf, got = ctypes.create_string_buffer(size), ctypes.c_size_t(0)
        if not self.k32.ReadProcessMemory(self.handle, ctypes.c_void_p(address), buf, size, ctypes.byref(got)):
            raise OSError(f"cannot read {address:x}")
        return buf.raw[:got.value]


def find_pid(exe: Path) -> int:
    """The process that runs this NMS.exe (other programs may be called nms.exe too)."""
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.OpenProcess.restype = wt.HANDLE
    out = subprocess.run(["tasklist", "/fi", "imagename eq NMS.exe", "/fo", "csv", "/nh"], capture_output=True, text=True).stdout
    for line in out.splitlines():
        parts = line.replace('"', "").split(",")
        if len(parts) < 2 or parts[0].lower() != "nms.exe":
            continue
        handle = k32.OpenProcess(0x1000, False, int(parts[1]))  # PROCESS_QUERY_LIMITED_INFORMATION
        if handle:
            buf, size = ctypes.create_unicode_buffer(1024), wt.DWORD(1024)
            ok = k32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size))
            k32.CloseHandle(handle)
            if ok and Path(buf.value).resolve() == exe.resolve():
                return int(parts[1])
    sys.exit("No Man's Sky is not running: start the game first (or pass --pid)")


class Emulator:
    def __init__(self, process: Process, exe: Path):
        import pefile
        from unicorn.x86_const import UC_X86_REG_RAX
        from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_FETCH_UNMAPPED, UC_HOOK_MEM_READ_UNMAPPED, UC_HOOK_MEM_WRITE_UNMAPPED, UC_ARCH_X86, UC_MODE_64, Uc
        self.process, self.base = process, process.base
        self.uc = uc = Uc(UC_ARCH_X86, UC_MODE_64)
        for start, size in ((STACK, STACK_SIZE), (HEAP, HEAP_SIZE), (STUBS, 0x100000), (RET_AT, 0x1000), (TEB, 0x20000)):
            uc.mem_map(start, size)
        uc.mem_write(RET_AT, b"\xf4")
        uc.mem_write(TEB + 0x58, struct.pack("<Q", TLS))
        uc.mem_write(TLS, struct.pack("<Q", TLS + 0x1000))
        uc.msr_write(0xC0000101, TEB)  # the thread block the code reads its thread-local data through
        self.heap = HEAP + 0x1000
        self.stubs: dict[int, str] = {}
        self.hooks: dict[int, object] = {}
        uc.hook_add(UC_HOOK_MEM_READ_UNMAPPED | UC_HOOK_MEM_WRITE_UNMAPPED | UC_HOOK_MEM_FETCH_UNMAPPED, self._page)
        uc.hook_add(UC_HOOK_CODE, self._code)
        # the calls into Windows and the C library go through the import table: each slot is pointed at a stub emulated here
        pe = pefile.PE(str(exe), fast_load=True)
        pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"]])
        n = 0
        for entry in pe.DIRECTORY_ENTRY_IMPORT:
            for imp in entry.imports:
                if imp.name:
                    stub = STUBS + 16 * n
                    n += 1
                    self.stubs[stub] = imp.name.decode()
                    uc.mem_write(stub, b"\xc3")
                    slot = self.base + imp.address - pe.OPTIONAL_HEADER.ImageBase
                    self.rd(slot, 8)
                    uc.mem_write(slot, struct.pack("<Q", stub))
        chkstk = self.base + 0x34900A0  # the compiler's stack probe: nothing to emulate
        self.hooks[chkstk] = lambda e: self._ret(e.uc.reg_read(UC_X86_REG_RAX))  # it leaves the frame size in rax

    def _page(self, uc, access, address, size, value, user):
        page = address & ~0xFFF
        try:
            data = self.process.read(page, 0x1000)
        except OSError:
            return False
        uc.mem_map(page, 0x1000)
        uc.mem_write(page, data.ljust(0x1000, b"\0"))
        return True

    def cstr(self, address: int, limit: int = 1 << 16) -> bytes:
        out = b""
        while len(out) < limit:
            c = self.rd(address + len(out), 1)
            if c == b"\0":
                break
            out += c
        return out

    def rd(self, address: int, size: int) -> bytes:
        from unicorn import UcError
        for page in range(address & ~0xFFF, address + size, 0x1000):
            try:
                self.uc.mem_read(page, 1)
            except UcError:
                self._page(self.uc, 0, page, 1, 0, None)
        return bytes(self.uc.mem_read(address, size))

    def wr(self, address: int, data: bytes) -> None:
        self.rd(address, len(data))
        self.uc.mem_write(address, data)

    def q(self, address: int) -> int:
        return struct.unpack("<Q", self.rd(address, 8))[0]

    def alloc(self, size: int) -> int:
        self.heap = (self.heap + 63) & ~63
        address, self.heap = self.heap, self.heap + size
        return address

    def _ret(self, rax: int) -> None:
        from unicorn.x86_const import UC_X86_REG_RAX, UC_X86_REG_RIP, UC_X86_REG_RSP
        rsp = self.uc.reg_read(UC_X86_REG_RSP)
        self.uc.reg_write(UC_X86_REG_RAX, rax)
        self.uc.reg_write(UC_X86_REG_RIP, struct.unpack("<Q", self.rd(rsp, 8))[0])
        self.uc.reg_write(UC_X86_REG_RSP, rsp + 8)

    def _code(self, uc, address, size, user):
        import math
        from unicorn.x86_const import UC_X86_REG_RCX, UC_X86_REG_RDX, UC_X86_REG_R8, UC_X86_REG_XMM0, UC_X86_REG_XMM1
        hook = self.hooks.get(address)
        if hook:
            hook(self)
            return
        name = self.stubs.get(address)
        if name is None:
            return
        rcx, rdx, r8 = (uc.reg_read(r) for r in (UC_X86_REG_RCX, UC_X86_REG_RDX, UC_X86_REG_R8))
        rax = 0
        if name in ("memcpy", "memmove"):
            self.wr(rcx, self.rd(rdx, r8))
            rax = rcx
        elif name == "memset":
            self.wr(rcx, bytes([rdx & 0xFF]) * r8)
            rax = rcx
        elif name in ("malloc", "operator new"):
            rax = self.alloc(rcx)
        elif name == "HeapAlloc":
            rax = self.alloc(r8)
        elif name == "__stdio_common_vsprintf":  # sprintf with %s and %d, which is all the game's code asks of it here
            from unicorn.x86_const import UC_X86_REG_R9, UC_X86_REG_RSP
            fmt = self.cstr(uc.reg_read(UC_X86_REG_R9)).decode("latin1")
            va = self.q(uc.reg_read(UC_X86_REG_RSP) + 0x30)
            text, i, n = "", 0, 0
            while i < len(fmt):
                if fmt[i] == "%" and i + 1 < len(fmt):
                    arg = self.q(va + 8 * n)
                    n += 1
                    text += self.cstr(arg).decode("latin1") if fmt[i + 1] == "s" else str(struct.unpack("<i", struct.pack("<I", arg & 0xFFFFFFFF))[0])
                    i += 2
                else:
                    text += fmt[i]
                    i += 1
            data = text.encode("latin1")[:r8 - 1] + b"\0"
            self.wr(rdx, data)
            rax = len(data) - 1
        elif name in ("strstr", "strchr"):
            haystack = self.cstr(rcx)
            at = haystack.find(self.cstr(rdx) if name == "strstr" else bytes([rdx & 0xFF]))
            rax = 0 if at < 0 else rcx + at
        elif name in ("strcmp", "strncmp", "_stricmp", "_strnicmp", "memcmp"):
            a, b = (self.rd(rcx, r8), self.rd(rdx, r8)) if name == "memcmp" else (self.cstr(rcx), self.cstr(rdx))
            if name.endswith("icmp"):
                a, b = a.lower(), b.lower()
            if name in ("strncmp", "_strnicmp"):
                a, b = a[:r8], b[:r8]
            rax = 0 if a == b else 1 if a > b else 0xFFFFFFFF
        elif name == "strlen":
            rax = len(self.cstr(rcx))
        elif name in ("toupper", "towupper"):
            rax = rcx - 32 if 97 <= (rcx & 0xFF) <= 122 else rcx & 0xFF
        elif name in ("tolower", "towlower"):
            rax = rcx + 32 if 65 <= (rcx & 0xFF) <= 90 else rcx & 0xFF
        elif name in ("strcpy", "strncpy"):
            text = self.cstr(rdx)
            size_ = len(text) + 1 if name == "strcpy" else r8
            self.wr(rcx, (text + b"\0" * size_)[:size_])
            rax = rcx
        elif name in ("strcat", "strncat"):
            text = self.cstr(rdx)[:r8] if name == "strncat" else self.cstr(rdx)
            self.wr(rcx + len(self.cstr(rcx)), text + b"\0")
            rax = rcx
        elif name in ("GetTickCount64", "GetTickCount", "timeGetTime"):
            rax = 100000
        elif name.startswith(("_Mtx", "_Cnd", "Sleep", "Interlocked", "TryAcquire", "WakeCondition", "Initialize", "_Thrd")):
            rax = 0
        elif name in ("free", "HeapFree"):
            rax = 1
        elif name in ("SetLastError", "EnterCriticalSection", "LeaveCriticalSection", "AcquireSRWLockExclusive", "ReleaseSRWLockExclusive",
                      "AcquireSRWLockShared", "ReleaseSRWLockShared", "GetCurrentThreadId"):
            rax = 0
        elif name.rstrip("f") in ("floor", "ceil", "sqrt", "sin", "cos", "tan", "atan", "acos", "asin", "exp", "log", "fabs", "pow", "atan2", "fmod",
                                   "frexp", "ldexp") or name in ("floorf", "ceilf"):
            double = not name.endswith("f")
            fmt, mask, size_ = ("<d", 2**64 - 1, 8) if double else ("<f", 2**32 - 1, 4)
            a = struct.unpack(fmt, (uc.reg_read(UC_X86_REG_XMM0) & mask).to_bytes(size_, "little"))[0]
            b2 = struct.unpack(fmt, (uc.reg_read(UC_X86_REG_XMM1) & mask).to_bytes(size_, "little"))[0]
            base = name[:-1] if name.endswith("f") else name
            if base == "frexp":
                mant, exp = math.frexp(a)
                self.wr(rdx, struct.pack("<i", exp))
                x = mant
            elif base == "ldexp":
                x = math.ldexp(a, struct.unpack("<i", (rdx & 0xFFFFFFFF).to_bytes(4, "little"))[0])
            else:
                x = {"floor": math.floor, "ceil": math.ceil, "sqrt": math.sqrt, "sin": math.sin, "cos": math.cos, "tan": math.tan, "atan": math.atan,
                     "acos": math.acos, "asin": math.asin, "exp": math.exp, "log": math.log, "fabs": abs, "pow": math.pow, "atan2": math.atan2,
                     "fmod": math.fmod}[base](*((a, b2) if base in ("pow", "atan2", "fmod") else (a,)))
            if not double:
                x = struct.unpack("<f", struct.pack("<f", x))[0]
            uc.reg_write(UC_X86_REG_XMM0, int.from_bytes(struct.pack(fmt, x), "little"))
        else:
            raise RuntimeError(f"the game's code calls {name}, which this script does not emulate (rcx={rcx:x})")
        from unicorn.x86_const import UC_X86_REG_RAX
        uc.reg_write(UC_X86_REG_RAX, rax)

    def call(self, rva: int, *args: int) -> None:
        from unicorn.x86_const import UC_X86_REG_R9, UC_X86_REG_R8, UC_X86_REG_RCX, UC_X86_REG_RDX, UC_X86_REG_RSP
        rsp = (STACK + STACK_SIZE - 0x10000) & ~0xF
        self.uc.mem_write(rsp + 8, b"\0" * 0x20)
        self.uc.mem_write(rsp, struct.pack("<Q", RET_AT))
        self.uc.reg_write(UC_X86_REG_RSP, rsp)
        for reg, value in zip((UC_X86_REG_RCX, UC_X86_REG_RDX, UC_X86_REG_R8, UC_X86_REG_R9), args):
            self.uc.reg_write(reg, value)
        self.uc.emu_start(self.base + rva, RET_AT, count=300_000_000)

    def system(self, address: int) -> list[tuple[int, int, int, int, bool]]:
        """The game's solar-system generator for an address: (seed, size class, biome, variant, start planet) of every body.
        Built the way the game's own callers set its working structures up (0x633680)."""
        b = self.base
        frame = self.alloc(0x3400)
        self.wr(frame, b"\0" * 0x3400)
        system, holder = frame + 0x9B0, frame + 0x240
        c1, c2, c3 = (self.rd(b + rva, 16) for rva in (0x4BFFF40, 0x4BFF280, 0x4BFF440))
        for i in range(0x42):
            self.call(0x27B6040, system + 0x70 * i)
        self.call(0x1E68720, system)
        self.wr(frame + 0x2690, c1 * 0x20)
        self.wr(frame + 0x2890, c1)
        self.wr(frame + 0x28A0, c1)
        self.call(0x1E87200, frame + 0x2890)
        self.call(0x227A630, frame + 0x29D0)
        for offset in range(0x2A70, 0x2AF0, 16):
            self.wr(frame + offset, c1)
        self.call(0x1DD8670, frame + 0x2AF0)
        self.wr(frame + 0x2B20, c1)
        self.call(0x458EB0, frame + 0x2B30)
        for offset in (0x2DFC, 0x2E1C, 0x2E2C, 0x2E5C):
            self.wr(frame + offset, struct.pack("<H", 0x100))
        self.call(0x1E871E0, frame + 0x2E80)
        self.call(0x1E871E0, frame + 0x2E94)
        for offset, value in ((0x2ED4, 1), (0x2EE0, 1), (0x2EE4, 7)):
            self.wr(frame + offset, struct.pack("<I", value))
        self.call(0x1EA2160, system)
        self.call(0x21F5DD0, holder)
        self.wr(frame + 0x2F0, b"\0" * 0x200)
        self.wr(frame + 0x970, c2)
        self.wr(frame + 0x98C, struct.pack("<Q", 7))
        for offset in range(0x930, 0x970, 16):
            self.wr(frame + offset, c3)
        self.call(0x21F5AC0, frame + 0x2F0)
        self.wr(frame + 0x9A0, b"\0")
        where = self.alloc(16)
        self.wr(where, struct.pack("<Q", address))
        self.call(SYSTEM_RVA, where, system, holder)
        self.system_at = system
        total = struct.unpack("<I", self.rd(system + 0x2544, 4))[0]
        bodies = []
        for i in range(total):
            d = self.rd(system + 0x2180 + i * 0x58, 0x58)
            bodies.append((struct.unpack_from("<Q", d, 0x20)[0], struct.unpack_from("<I", d, 0x40)[0], struct.unpack_from("<I", d, 0x30)[0],
                           struct.unpack_from("<I", d, 0x34)[0], struct.unpack_from("<I", d, 0x38)[0] == 1))
        return bodies

    def levels(self, count: int) -> list[dict]:
        """The planet routine (0x16c44c0) for the first `count` bodies of the system made last: what stage A and the weather made of
        each (the fields of the routine's working structure). The texts are not made: the routine that picks them is stood in for."""
        from unicorn.x86_const import UC_X86_REG_RBP, UC_X86_REG_RSP
        base = self.base
        g = self.q(base + 0x6F6C288)
        planet_generator = self.q(g + 0x72B610) + 0x522B40
        captured: dict[str, bytes] = {}

        def after_texts(e) -> None:
            captured["G"] = e.rd(e.uc.reg_read(UC_X86_REG_RBP) + 0x160, 0x3C00)

        def texts(e) -> None:  # 0x16cdf20 draws a number under a loc key; nothing here needs the key
            rsp = e.uc.reg_read(UC_X86_REG_RSP)
            e.uc.reg_write(UC_X86_REG_RAX, e.uc.reg_read(UC_X86_REG_RDX))
            e.uc.reg_write(UC_X86_REG_RIP, e.q(rsp))
            e.uc.reg_write(UC_X86_REG_RSP, rsp + 8)

        from unicorn.x86_const import UC_X86_REG_RAX, UC_X86_REG_RDX, UC_X86_REG_RIP
        self.hooks[base + 0x16C503B] = after_texts
        self.hooks[base + 0x16CDF20] = texts
        out = []
        for i in range(count):
            work = self.alloc(0x400)
            self.wr(work, b"\0" * 0x400)
            captured.clear()
            self.call(0x16C44C0, planet_generator, work, self.system_at + 0x2180 + i * 0x58, 0)
            if "G" not in captured:  # the routine ended before its texts (a body the game builds differently): not compared
                out.append(None)
                continue
            G = captured["G"]
            gi = lambda o: struct.unpack_from("<i", G, o)[0]
            out.append({"flora": gi(0x3538), "extra": gi(0x3540), "sentinels": [gi(0x34CC + 24 * k) for k in range(4)], "weather_kind": gi(0x1E54),
                        "weather_class": gi(0x1E48), "weather_extreme": gi(0x1E50)})
        return out

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--game", help="No Man's Sky install (default $NMS_GAME_DIR)")
    ap.add_argument("--pid", type=int)
    ap.add_argument("--systems", type=int, default=200)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--data", action="store_true", help="also check planet_data.py: flora, sentinels and weather of every body")
    args = ap.parse_args()
    game = Path(args.game or os.environ.get("NMS_GAME_DIR") or "")
    exe = game / "Binaries" / "NMS.exe"
    if not exe.is_file():
        sys.exit(f"{exe} not found: pass --game or set NMS_GAME_DIR")
    import planet_data
    import planet_gen
    import pefile
    pe = pefile.PE(str(exe), fast_load=True)
    offset = pe.get_offset_from_rva(SYSTEM_RVA)
    if exe.read_bytes()[offset:offset + len(START)] != START:
        sys.exit("The system generator is not where build 184271 has it: see the note at the top of this file.")
    emulator = Emulator(Process(args.pid or find_pid(exe)), exe)
    rnd = random.Random(args.seed)
    differ = 0
    for _ in range(args.systems):
        address = (rnd.randrange(1, 0x7FF) << 40) | (rnd.randrange(0, 8) << 32) | (rnd.randrange(0, 255) << 24) | (rnd.randrange(0, 4096) << 12) | rnd.randrange(0, 4096)
        theirs = emulator.system(address)
        mine = [(b.seed, b.size, b.biome, b.subtype, b.start) for b in planet_gen.bodies(address)]
        if mine != theirs:
            differ += 1
            print(f"{address:013x}: the game makes {theirs}, planet_gen {mine}")
        if args.data and mine == theirs:
            ours = planet_gen.bodies(address)
            for body, game_says in zip(ours, emulator.levels(len(ours))):
                if game_says is None:
                    continue
                got = planet_data.levels(body.seed, body, body.star, body.galaxy, body.index)
                if any(got[k] != game_says[k] for k in game_says):
                    differ += 1
                    print(f"{address:013x} body {body.index}: the game makes {game_says}, planet_data {({k: got[k] for k in game_says})}")
    print(f"{args.systems} systems, {differ} differ from the game's generator")
    return 1 if differ else 0


if __name__ == "__main__":
    sys.exit(main())
