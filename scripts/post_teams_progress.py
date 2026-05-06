#!/usr/bin/env python3
"""Post a Nexus deploy notification to a Teams webhook."""
from __future__ import annotations
import argparse, json, os, sys
from datetime import datetime, timezone
from urllib import error, request


def post_to_webhook(url: str, payload: dict) -> str:
    data = json.dumps(payload).encode()
    req = request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with request.urlopen(req, timeout=20) as resp:
            return resp.read().decode(errors="replace").strip() or f"HTTP {resp.status}"
    except error.HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code}: {exc.read().decode(errors='replace')}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Webhook unreachable: {exc.reason}") from exc


def build_card(version: str, status: str, repo: str, sha: str) -> dict:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    ok = status == "success"
    return {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "themeColor": "00B36B" if ok else "D40000",
        "summary": f"NEXUS {version} — {'Deploy succeeded' if ok else 'Deploy FAILED'}",
        "title": f"NEXUS Deploy — {version}",
        "sections": [{
            "facts": [
                {"name": "Version",  "value": version},
                {"name": "Status",   "value": "✅ Succeeded" if ok else "❌ Failed"},
                {"name": "Deployed", "value": now},
                {"name": "Commit",   "value": sha[:8] if sha else "—"},
                {"name": "Repo",     "value": repo or "noc-spark/noc-configmaker-api"},
            ]
        }],
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("subcommand", choices=["release-tag"])
    p.add_argument("--webhook-url", default=os.getenv("TEAMS_DEPLOY_WEBHOOK_URL", ""))
    p.add_argument("--version",     default=os.getenv("NEXUS_VERSION", "unknown"))
    p.add_argument("--status",      default=os.getenv("DEPLOY_STATUS", "success"))
    p.add_argument("--repo",        default=os.getenv("GITHUB_REPOSITORY", ""))
    p.add_argument("--sha",         default=os.getenv("GITHUB_SHA", ""))
    args = p.parse_args()

    if not args.webhook_url:
        print("No webhook URL — skipping notification.", file=sys.stderr)
        return 0

    result = post_to_webhook(args.webhook_url, build_card(args.version, args.status, args.repo, args.sha))
    print(f"Teams notified: {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
