"""
End-to-end smoke: POST /api/search then poll GET /api/runs/{id} until not RUNNING.

Usage (from repo root, backend reachable):
  python scripts/e2e_search_run.py
  python scripts/e2e_search_run.py --query "your query" --max 1 --api http://127.0.0.1:8000
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request


def request_json(method: str, url: str, body: dict | None = None, timeout: int = 120) -> dict:
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--api", default="http://127.0.0.1:8000", help="Base URL of FastAPI backend")
    p.add_argument("--query", default="boutique email marketing agency", help="Search query (like dashboard)")
    p.add_argument("--max", type=int, default=1, help="max_companies (keep small for smoke)")
    p.add_argument("--poll", type=float, default=4.0, help="Seconds between polls")
    p.add_argument("--timeout", type=int, default=900, help="Max total seconds to wait for terminal status")
    args = p.parse_args()

    base = args.api.rstrip("/")
    health_url = f"{base}/api/health"
    search_url = f"{base}/api/search"

    try:
        health = request_json("GET", health_url, None, timeout=10)
    except urllib.error.URLError as e:
        print(f"FAIL: cannot reach {health_url}: {e}", file=sys.stderr)
        return 1
    print("GET /api/health ->", health)

    print(f"POST /api/search query={args.query!r} max_companies={args.max} ...")
    try:
        start = request_json("POST", search_url, {"query": args.query, "max_companies": args.max}, timeout=30)
    except urllib.error.HTTPError as e:
        print(f"FAIL: HTTP {e.code} {e.reason}", file=sys.stderr)
        print(e.read().decode("utf-8", errors="replace"), file=sys.stderr)
        return 1

    run_id = start.get("run_id")
    if not run_id:
        print("FAIL: no run_id in response:", start, file=sys.stderr)
        return 1
    print("run_id:", run_id)

    deadline = time.monotonic() + args.timeout
    n = 0
    last: dict = {}
    while time.monotonic() < deadline:
        n += 1
        run_url = f"{base}/api/runs/{run_id}"
        last = request_json("GET", run_url, None, timeout=60)
        st = last.get("status")
        dc = last.get("discovered_companies")
        pc = last.get("processed_companies")
        lc = len(last.get("leads") or [])
        print(f"[{n}] status={st} discovered={dc} processed={pc} leads_in_payload={lc}")
        if st != "RUNNING":
            break
        time.sleep(args.poll)
    else:
        print("FAIL: timeout waiting for terminal run status", file=sys.stderr)
        print(json.dumps(last, indent=2, default=str))
        return 2

    print("--- Final GET /api/runs/{run_id} ---")
    print(json.dumps(last, indent=2, default=str))

    leads = last.get("leads") or []
    ready = [L for L in leads if L.get("status") == "READY_TO_SEND"]
    print(f"Summary: terminal_status={last.get('status')} READY_TO_SEND_leads={len(ready)} total_leads_in_run={len(leads)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
