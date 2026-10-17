"""Manage the GitHub Pages site at nmsii.dlu.one.

The site is built and deployed by .github/workflows/pages.yml on every push to
main. What the workflow cannot do is configure Pages itself -- turn it on, point
it at Actions, own the custom domain, enforce HTTPS -- because those are repo
settings, and an Actions deploy ignores a CNAME file. This does them, through
the `gh` CLI, idempotently:

    setup    turn Pages on with the Actions source and set the domain
    https    enforce HTTPS, once GitHub has issued the certificate
    status   DNS, the Pages settings, the certificate and the last deploy

DNS lives in Cloudflare and is not touched here: `nms` is a CNAME to
rdlu.github.io, DNS only (grey cloud), so GitHub can issue the certificate.

Run via `mise run pages-setup`, `mise run pages-https`, `mise run pages-status`.
"""

from __future__ import annotations

import json
import socket
import subprocess
import sys

REPO = "rdlu/nms-items"
DOMAIN = "nmsii.dlu.one"
TARGET = "rdlu.github.io"
WORKFLOW = "pages.yml"


def gh(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["gh", *args], capture_output=True, text=True, check=check)


def pages() -> dict | None:
    """The Pages settings, or None when Pages is not on yet."""
    result = gh("api", f"repos/{REPO}/pages", check=False)
    return json.loads(result.stdout) if result.returncode == 0 else None


def setup() -> None:
    site = pages()
    if site is None:
        gh("api", "-X", "POST", f"repos/{REPO}/pages", "-f", "build_type=workflow")
        print("Pages turned on, deploying from GitHub Actions")
    elif site.get("build_type") != "workflow":
        gh("api", "-X", "PUT", f"repos/{REPO}/pages", "-f", "build_type=workflow")
        print("Pages switched to deploy from GitHub Actions")
    else:
        print("Pages already on, deploying from GitHub Actions")

    if (pages() or {}).get("cname") != DOMAIN:
        gh("api", "-X", "PUT", f"repos/{REPO}/pages", "-f", f"cname={DOMAIN}")
        print(f"Custom domain set to {DOMAIN}")
    else:
        print(f"Custom domain already {DOMAIN}")
    print("Next: push to main to deploy, then `mise run pages-https` once the certificate is issued.")


def https() -> None:
    site = pages()
    if site is None:
        sys.exit("Pages is not on yet: run `mise run pages-setup` first.")
    if site.get("https_enforced"):
        print("HTTPS is already enforced")
        return
    result = gh("api", "-X", "PUT", f"repos/{REPO}/pages", "-F", "https_enforced=true", check=False)
    if result.returncode != 0:
        # GitHub refuses until the certificate exists; that is the usual case.
        sys.exit("GitHub refused - the certificate is probably not issued yet.\n"
                 "Check `mise run pages-status` and try again in a few minutes.\n"
                 + result.stderr.strip())
    print(f"HTTPS enforced on https://{DOMAIN}")


def status() -> None:
    # getaddrinfo, not gethostbyname_ex: that one is IPv4 only, and some
    # resolvers answer this name with GitHub's IPv6 addresses alone.
    try:
        found = socket.getaddrinfo(DOMAIN, 443, proto=socket.IPPROTO_TCP, flags=socket.AI_CANONNAME)
        name = next((info[3] for info in found if info[3]), DOMAIN)
        addresses = sorted({info[4][0] for info in found})
        print(f"DNS       {DOMAIN} -> {name} {', '.join(addresses[:4])}")
        if name != TARGET:
            print(f"          expected a CNAME to {TARGET}: is the Cloudflare proxy on?")
    except OSError as exc:
        print(f"DNS       {DOMAIN} does not resolve ({exc})")

    site = pages()
    if site is None:
        print("Pages     off - run `mise run pages-setup`")
    else:
        cert = site.get("https_certificate") or {}
        # `status` only tracks branch builds; with the Actions source it stays
        # empty on a working site, so the deploy line below is the real answer.
        print(f"Pages     on, source {site.get('build_type')}, domain {site.get('cname') or '-'}")
        print(f"HTTPS     certificate {cert.get('state', 'none')}, "
              f"{'enforced' if site.get('https_enforced') else 'not enforced'}")
        print(f"URL       {site.get('html_url')}")

    runs = gh("run", "list", "-R", REPO, "-w", WORKFLOW, "-L", "1",
              "--json", "status,conclusion,headSha,createdAt,url", check=False)
    last = json.loads(runs.stdout or "[]")
    if last:
        run = last[0]
        print(f"Deploy    {run['conclusion'] or run['status']} for {run['headSha'][:7]} "
              f"at {run['createdAt']}\n          {run['url']}")
    else:
        print("Deploy    no runs yet - push to main")


def main() -> None:
    commands = {"setup": setup, "https": https, "status": status}
    if len(sys.argv) != 2 or sys.argv[1] not in commands:
        sys.exit(f"usage: pages.py {{{','.join(commands)}}}")
    commands[sys.argv[1]]()


if __name__ == "__main__":
    main()
