#!/usr/bin/env python3
"""Post a Nexus deploy notification to a Teams webhook — ACS-style release card."""
from __future__ import annotations
import argparse, json, os, re, subprocess, sys
from datetime import datetime, timezone
from urllib import error, request


def get_highlights(repo_path: str, current_tag: str, max_items: int = 8) -> list[str]:
    try:
        tags = subprocess.run(
            ["git", "tag", "--sort=-version:refname"],
            cwd=repo_path, capture_output=True, text=True, timeout=10,
        ).stdout.splitlines()
        tags = [t.strip() for t in tags if t.strip() and t.strip() != current_tag]
        prev_tag = tags[0] if tags else None
        ref_range = f"{prev_tag}..{current_tag}" if prev_tag else f"{current_tag}~10..{current_tag}"
        log = subprocess.run(
            ["git", "log", ref_range, "--pretty=format:%s", "--no-merges"],
            cwd=repo_path, capture_output=True, text=True, timeout=10,
        ).stdout.splitlines()
        return [s.strip() for s in log if s.strip()][:max_items]
    except Exception:
        return []


def _readable(subject: str) -> str:
    m = re.match(r"^(?:feat|fix|refactor|chore|test|docs|ci|perf|style)\(([^)]+)\):\s*(.+)$", subject, re.I)
    if m:
        return f"{m.group(2).strip().capitalize()} ({m.group(1)})"
    m2 = re.match(r"^(?:feat|fix|refactor|chore|test|docs|ci|perf|style):\s*(.+)$", subject, re.I)
    if m2:
        return m2.group(1).strip().capitalize()
    return subject.strip().capitalize()


def build_card(version: str, status: str, repo: str, sha: str, highlights: list[str]) -> dict:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    ok = status == "success"
    sections: list[dict] = [
        {
            "activityTitle": f"{'Production deploy complete' if ok else 'Production deploy FAILED'} for {version}",
            "facts": [
                {"name": "Repository",  "value": repo or "NX-Whamza/nexus"},
                {"name": "Release tag", "value": version},
                {"name": "Commit",      "value": sha[:8] if sha else "—"},
                {"name": "Status",      "value": "✅ Succeeded" if ok else "❌ Failed"},
                {"name": "Deployed",    "value": now},
            ],
        }
    ]
    if highlights:
        sections.append({
            "title": "Current highlights",
            "text": "\n\n".join(f"• **{_readable(h)}**" for h in highlights),
        })
    return {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "themeColor": "00B36B" if ok else "D40000",
        "summary": f"NEXUS {version} — {'Deploy succeeded' if ok else 'Deploy FAILED'}",
        "title": "NEXUS Release Update",
        "sections": sections,
    }


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


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("subcommand", choices=["release-tag"])
    p.add_argument("--webhook-url", default=os.getenv("TEAMS_DEPLOY_WEBHOOK_URL", ""))
    p.add_argument("--version",     default=os.getenv("NEXUS_VERSION", "unknown"))
    p.add_argument("--status",      default=os.getenv("DEPLOY_STATUS", "success"))
    p.add_argument("--repo",        default=os.getenv("GITHUB_REPOSITORY", ""))
    p.add_argument("--sha",         default=os.getenv("GITHUB_SHA", ""))
    p.add_argument("--repo-path",   default=os.getenv("GITHUB_WORKSPACE", "."))
    args = p.parse_args()

    if not args.webhook_url:
        print("No webhook URL — skipping notification.", file=sys.stderr)
        return 0

    highlights = get_highlights(args.repo_path, args.version)
    payload = build_card(args.version, args.status, args.repo, args.sha, highlights)
    result = post_to_webhook(args.webhook_url, payload)
    print(f"Teams notified: {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
