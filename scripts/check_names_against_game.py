"""Check the made-up words of names against the game's own routine: run NMS.exe's word generator and compare.

    uv run --with pefile --with unicorn --with numpy python scripts/check_names_against_game.py [--game DIR] [--cases 20000]

Every name the game makes up (planets, systems, regions) is built from words by one routine in NMS.exe. This loads the
executable into an x86 emulator (Unicorn), runs that routine on random inputs and compares word and generator state with
desktop/word_filter.py's generator (nms_namegen's, with the game's differences and filter). After a game update run it again:
no differences means the words are still the game's; differences mean the routine changed.

The addresses below are those of build 184271 (the first bytes of the routine are checked, and the script stops if they are
not there). In a newer build find the routine again: it is the one that refers to the table functions and calls the filter;
the strings "%PROCNORM%" and "NAMEGEN_PLANET_STYLE_%i" lead to the routine that calls it.
"""
from __future__ import annotations

import argparse
import os
import random
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "desktop"))
sys.path.insert(0, str(ROOT / "third_party" / "nms_namegen"))

WORD_RVA = 0xEA03C0     # the word generator
CHKSTK_RVA = 0x34900A0  # the compiler's stack probe: nothing to emulate
START = bytes.fromhex("488bc448895810" "4c894018" "48894808" "55565741")  # its first bytes


def load(exe: Path):
    import pefile
    from unicorn import UC_ARCH_X86, UC_HOOK_CODE, UC_MODE_64, Uc
    from unicorn.x86_const import (UC_X86_REG_R8, UC_X86_REG_R9, UC_X86_REG_RAX, UC_X86_REG_RCX, UC_X86_REG_RDX, UC_X86_REG_RIP,
                                   UC_X86_REG_RSP)

    pe = pefile.PE(str(exe), fast_load=True)
    data = exe.read_bytes()
    base = pe.OPTIONAL_HEADER.ImageBase
    mu = Uc(UC_ARCH_X86, UC_MODE_64)
    for s in pe.sections:
        if s.Name.startswith((b".text", b".rdata", b".data", b"_RDATA", b"ZSTD")):
            mu.mem_map(base + s.VirtualAddress, (max(s.Misc_VirtualSize, s.SizeOfRawData) + 0xFFF) & ~0xFFF)
            mu.mem_write(base + s.VirtualAddress, data[s.PointerToRawData:s.PointerToRawData + s.SizeOfRawData])
    start = pe.get_offset_from_rva(WORD_RVA)
    if data[start:start + len(START)] != START:
        sys.exit("The word generator is not where build 184271 has it: see the note at the top of this file.")

    stack, stack_size, heap, ret_at, stubs = 0x70000000, 0x1000000, 0x20000000, 0x60000000, 0x50000000
    mu.mem_map(stack, stack_size)
    mu.mem_map(heap, 0x10000)
    mu.mem_map(ret_at, 0x1000)
    mu.mem_write(ret_at, b"\xf4")
    mu.mem_map(stubs, 0x100000)

    # The executable calls the C library through its import table; each import is pointed at a stub emulated here.
    pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"]])
    names: dict[int, str] = {}
    for entry in getattr(pe, "DIRECTORY_ENTRY_IMPORT", []):
        for imp in entry.imports:
            if imp.name:
                addr = stubs + 16 * len(names)
                names[addr] = imp.name.decode()
                mu.mem_write(imp.address - pe.OPTIONAL_HEADER.ImageBase + base, struct.pack("<Q", addr))
                mu.mem_write(addr, b"\xc3")

    def cstr(addr: int) -> bytes:
        out = b""
        while (c := bytes(mu.mem_read(addr + len(out), 1))) != b"\0":
            out += c
        return out

    def hook(uc, addr, size, user):
        if addr == base + CHKSTK_RVA:
            rsp = uc.reg_read(UC_X86_REG_RSP)
            uc.reg_write(UC_X86_REG_RIP, struct.unpack("<Q", bytes(uc.mem_read(rsp, 8)))[0])
            uc.reg_write(UC_X86_REG_RSP, rsp + 8)
            return
        name = names.get(addr)
        if name is None:
            return
        rcx, rdx, r8 = (uc.reg_read(r) for r in (UC_X86_REG_RCX, UC_X86_REG_RDX, UC_X86_REG_R8))
        rax = 0
        if name in ("memcpy", "memmove"):
            uc.mem_write(rcx, bytes(uc.mem_read(rdx, r8)))
            rax = rcx
        elif name == "memset":
            uc.mem_write(rcx, bytes([rdx & 0xFF]) * r8)
            rax = rcx
        elif name == "strlen":
            rax = len(cstr(rcx))
        elif name in ("toupper", "towupper"):
            rax = rcx - 32 if 97 <= (rcx & 0xFF) <= 122 else rcx & 0xFF
        elif name in ("tolower", "towlower"):
            rax = rcx + 32 if 65 <= (rcx & 0xFF) <= 90 else rcx & 0xFF
        elif name in ("strncpy", "strcpy"):
            text = cstr(rdx)
            size_ = r8 if name == "strncpy" else len(text) + 1
            uc.mem_write(rcx, (text + b"\0" * size_)[:size_])
            rax = rcx
        elif name in ("strncat", "strcat"):
            text = cstr(rdx)[:r8] if name == "strncat" else cstr(rdx)
            uc.mem_write(rcx + len(cstr(rcx)), text + b"\0")
            rax = rcx
        else:
            sys.exit(f"The routine calls {name}, which this script does not emulate.")
        uc.reg_write(UC_X86_REG_RAX, rax)

    mu.hook_add(UC_HOOK_CODE, hook, begin=base + CHKSTK_RVA, end=base + CHKSTK_RVA)
    mu.hook_add(UC_HOOK_CODE, hook, begin=stubs, end=stubs + 0x100000)

    params, state, out = heap, heap + 0x100, heap + 0x200

    def run(alphaset: int, shortest: int, longest: int, low: int, high: int):
        mu.mem_write(params, struct.pack("<III", alphaset, shortest, longest))
        mu.mem_write(state, struct.pack("<II", low, high))
        mu.mem_write(out, b"\0" * 128)
        rsp = stack + stack_size - 0x2000
        mu.mem_write(rsp, struct.pack("<Q", ret_at))
        mu.reg_write(UC_X86_REG_RSP, rsp)
        mu.reg_write(UC_X86_REG_RCX, 0)
        mu.reg_write(UC_X86_REG_RDX, state)
        mu.reg_write(UC_X86_REG_R8, params)
        mu.reg_write(UC_X86_REG_R9, out)
        mu.emu_start(base + WORD_RVA, ret_at, count=2_000_000)
        text = bytes(mu.mem_read(out, 64))
        return text[:text.index(b"\0")].decode(), struct.unpack("<II", bytes(mu.mem_read(state, 8)))

    return run


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--game", help="No Man's Sky install (default $NMS_GAME_DIR)")
    ap.add_argument("--cases", type=int, default=20000)
    args = ap.parse_args()
    game = Path(args.game or os.environ.get("NMS_GAME_DIR") or "")
    exe = game / "Binaries" / "NMS.exe"
    if not exe.is_file():
        sys.exit(f"{exe} not found: pass --game or set NMS_GAME_DIR")

    import word_filter
    from nms_namegen.prng import PRNG

    generate = word_filter._game_word_generator()
    run = load(exe)
    rnd = random.Random(5)
    wrong = []
    for _ in range(args.cases):
        alphaset, shortest = rnd.randint(0, 7), rnd.randint(3, 7)
        longest = shortest + rnd.randint(0, 5)
        low, high = rnd.getrandbits(32), rnd.getrandbits(32)
        rng = PRNG((high << 32) | low)
        mine = (generate(rng, alphaset, shortest, longest), (rng.seed & 0xFFFFFFFF, rng.seed >> 32))
        theirs = run(alphaset, shortest, longest, low, high)
        if mine != theirs:
            wrong.append(((alphaset, shortest, longest, low, high), theirs, mine))
    print(f"{args.cases} words, {len(wrong)} differ from the game's routine")
    for case in wrong[:10]:
        print("  ", case)
    return 1 if wrong else 0


if __name__ == "__main__":
    sys.exit(main())
