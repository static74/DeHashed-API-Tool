#!/usr/bin/env python3
"""
DeHashed v2 Search API caller for the dehashed-recon skill.

Sends one broad query, paginates automatically under a safety cap, and emits
JSON results to stdout or a file. Designed for the "broad-then-prune" workflow
where a single wide query replaces many narrow ones to save API credits.

Key discovery order (first hit wins):
  1. DEHASHED_API_KEY environment variable
  2. Filesystem search for a dehashapitool config.txt in known install locations
     (dev checkout under ~/git, pipx venvs under ~/.local).
  3. Interactive prompt on a TTY.

Dependencies: requests (install with `pip install requests`).
"""
import argparse
import json
import os
import sys
from pathlib import Path
from time import sleep

import requests

SEARCH_URL = "https://api.dehashed.com/v2/search"
RATE_LIMIT_SLEEP = 0.1

CONFIG_SEARCH_GLOBS = [
    "~/git/DeHashed-API-Tool/dehashapitool/config.txt",
    "~/dev/DeHashed-API-Tool/dehashapitool/config.txt",
    "~/code/DeHashed-API-Tool/dehashapitool/config.txt",
    "~/.local/pipx/venvs/dehashapitool/lib/python*/site-packages/dehashapitool/config.txt",
    "~/.local/share/pipx/venvs/dehashapitool/lib/python*/site-packages/dehashapitool/config.txt",
]


def log(msg: str) -> None:
    print(msg, file=sys.stderr)


def _read_key_from_file(path: Path) -> str | None:
    try:
        lines = path.read_text().splitlines()
    except OSError:
        return None
    if not lines:
        return None
    candidate = lines[0].strip()
    if not candidate or candidate == "<api-key>":
        return None
    return candidate


def get_api_key() -> str:
    key = os.environ.get("DEHASHED_API_KEY", "").strip()
    if key:
        return key

    tried: list[str] = []
    for pattern in CONFIG_SEARCH_GLOBS:
        expanded = Path(os.path.expanduser(pattern))
        if "*" in str(expanded):
            matches = sorted(Path("/").glob(str(expanded).lstrip("/")))
        else:
            matches = [expanded] if expanded.is_file() else []
        for match in matches:
            tried.append(str(match))
            found = _read_key_from_file(match)
            if found:
                return found

    if not sys.stdin.isatty():
        log("[!] No API key found. Checked:")
        log(f"    - DEHASHED_API_KEY env var (unset)")
        for path in tried:
            log(f"    - {path}")
        log("    Run `dat --store-key` or `export DEHASHED_API_KEY=...` and retry.")
        raise SystemExit(2)

    key = input("DeHashed API Key: ").strip()
    if not key:
        raise SystemExit("[!] No API key provided; aborting.")
    return key


def call_api(query: str, page: int, size: int, wildcard: bool, regex: bool, de_dupe: bool, api_key: str) -> dict:
    response = requests.post(
        SEARCH_URL,
        json={
            "query": query,
            "page": page,
            "size": size,
            "wildcard": wildcard,
            "regex": regex,
            "de_dupe": de_dupe,
        },
        headers={
            "Content-Type": "application/json",
            "Dehashed-Api-Key": api_key,
        },
        timeout=60,
    )
    if response.status_code != 200:
        log(f"[!] HTTP {response.status_code} from DeHashed")
        log(f"    Body: {response.text}")
        raise SystemExit(response.status_code)
    try:
        return response.json()
    except ValueError:
        log("[!] Non-JSON response from DeHashed")
        log(f"    Body: {response.text[:500]}")
        raise SystemExit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Broad-query caller for DeHashed v2 Search API",
        epilog="Examples:\n"
               "  %(prog)s --query 'domain:acme.com' --output /tmp/acme.json\n"
               "  %(prog)s --query 'email:user@example.com' --size 100\n"
               "  %(prog)s --query '(domain:a.com OR domain:b.com)' --probe\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--query", required=True, help="Raw DeHashed query string (e.g., 'domain:acme.com').")
    parser.add_argument("--size", type=int, default=10000, help="Page size 1-10000. Default 10000 (max) for credit efficiency.")
    parser.add_argument("--wildcard", action="store_true", help="Enable wildcard matching (? works; * was broken as of May 2025).")
    parser.add_argument("--regex", action="store_true", help="Enable regex matching. Mutex with --wildcard.")
    parser.add_argument("--de-dupe", dest="de_dupe", action="store_true", help="Deduplicate across sources.")
    parser.add_argument("--probe", action="store_true", help="Fire a single size=1 call to validate grammar, then exit. Use before complex boolean queries.")
    parser.add_argument("--max-calls", type=int, default=25, help="Safety cap on paginated calls. Script errors out if exceeded. Default 25.")
    parser.add_argument("--output", help="Path to write JSON results. Default: stdout.")
    args = parser.parse_args()

    if args.wildcard and args.regex:
        raise SystemExit("[!] --wildcard and --regex are mutually exclusive.")
    if not 1 <= args.size <= 10000:
        raise SystemExit("[!] --size must be between 1 and 10000.")

    api_key = get_api_key()

    if args.probe:
        log(f"[*] Probing grammar with: {args.query!r}")
        data = call_api(args.query, page=1, size=1, wildcard=args.wildcard, regex=args.regex, de_dupe=args.de_dupe, api_key=api_key)
        log(f"[+] Probe OK. total={data.get('total')} balance={data.get('balance')} took={data.get('took')}")
        sys.stdout.write(json.dumps(data, indent=2) + "\n")
        return

    entries: list = []
    balance = None
    total = None
    page = 0

    while True:
        page += 1
        if page > args.max_calls:
            log(f"[!] --max-calls cap of {args.max_calls} hit. Raise it to continue paginating.")
            log(f"    Results collected so far: {len(entries)} of {total} total.")
            break

        data = call_api(args.query, page=page, size=args.size, wildcard=args.wildcard, regex=args.regex, de_dupe=args.de_dupe, api_key=api_key)
        balance = data.get("balance")
        total = data.get("total")
        batch = data.get("entries") or []
        entries.extend(batch)
        log(f"[*] page {page}: {len(batch)} entries (running total {len(entries)} / API total {total}). balance={balance}")

        if total is None or len(entries) >= total:
            break
        if args.size * page >= 10000:
            log("[!] Hit 10,000 result pagination boundary. Deep pagination not implemented in this script.")
            break

        sleep(RATE_LIMIT_SLEEP)

    result = {
        "balance": balance,
        "total": total,
        "collected": len(entries),
        "query": args.query,
        "entries": entries,
    }

    payload = json.dumps(result, indent=2)
    if args.output:
        Path(args.output).write_text(payload + "\n")
        log(f"[+] Wrote {len(entries)} entries to {args.output}")
    else:
        sys.stdout.write(payload + "\n")

    log(f"[+] Credits remaining: {balance}")


if __name__ == "__main__":
    main()
