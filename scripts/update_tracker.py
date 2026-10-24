#!/usr/bin/env python3
"""
Repo Tracker — collects every public repo on the account and writes:
  * docs/data.json  -> read by the GitHub Pages dashboard (docs/index.html)
  * README.md       -> table between the TRACKER markers is regenerated

Status comes from repo topics:
  status-completed | status-in-progress | status-needs-improvement
Repos without one of these topics are shown as "Not tagged".

Category comes from a topic starting with "cat-", e.g. cat-ml-project -> "ML Project".
Live link = the repo's Website field (About > Website), or its GitHub Pages URL.

Standard library only, so no pip install is needed.
"""
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API = "https://api.github.com"
OWNER = os.environ.get("TRACK_USER") or os.environ.get("GITHUB_REPOSITORY_OWNER")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
STALE_DAYS = int(os.environ.get("STALE_DAYS", "180"))

STATUS_TOPICS = {
    "status-completed": "completed",
    "status-in-progress": "in-progress",
    "status-needs-improvement": "needs-improvement",
}
STATUS_ORDER = ["needs-improvement", "in-progress", "untagged", "completed"]
CATEGORY_PREFIX = "cat-"
ACRONYMS = {"ml", "ai", "nlp", "llm", "sql", "vba", "ui", "api", "eda", "bi"}
README_LABELS = {
    "completed": "✅ Completed",
    "in-progress": "🚧 In progress",
    "needs-improvement": "🛠️ Needs improvement",
    "untagged": "❔ Not tagged",
}
START, END = "<!-- TRACKER:START -->", "<!-- TRACKER:END -->"


def api_get(path):
    """GET from the GitHub API. Returns parsed JSON, or None on 404."""
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "repo-tracker",
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    req = urllib.request.Request(API + path, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as err:
        if err.code == 404:
            return None
        raise


def list_repos(owner):
    repos, page = [], 1
    while True:
        batch = api_get(f"/users/{owner}/repos?type=owner&per_page=100&page={page}")
        if not batch:
            break
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return repos


def days_since(iso):
    if not iso:
        return None
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return (datetime.now(timezone.utc) - dt).days


def category_label(topic):
    words = topic[len(CATEGORY_PREFIX):].split("-")
    return " ".join(w.upper() if w in ACRONYMS else w.capitalize() for w in words)


def live_url(repo):
    home = (repo.get("homepage") or "").strip()
    if home:
        return home if home.startswith("http") else "https://" + home
    if repo.get("has_pages"):
        owner = repo["owner"]["login"].lower()
        name = repo["name"]
        if name.lower() == f"{owner}.github.io":
            return f"https://{owner}.github.io/"
        return f"https://{owner}.github.io/{name}/"
    return ""


def build_record(repo):
    topics = repo.get("topics") or []
    status = next((STATUS_TOPICS[t] for t in topics if t in STATUS_TOPICS), "untagged")
    cat_topic = next((t for t in topics if t.startswith(CATEGORY_PREFIX)), None)
    category = category_label(cat_topic) if cat_topic else "Uncategorized"
    has_readme = api_get(f"/repos/{repo['full_name']}/readme") is not None
    idle = days_since(repo.get("pushed_at"))

    warnings = []
    if not has_readme:
        warnings.append("No README")
    if not repo.get("description"):
        warnings.append("No description")
    if not repo.get("license"):
        warnings.append("No license")
    if idle is not None and idle > STALE_DAYS:
        warnings.append(f"No commits in {idle} days")

    return {
        "name": repo["name"],
        "url": repo["html_url"],
        "description": repo.get("description") or "",
        "status": status,
        "category": category,
        "topics": [t for t in topics if t not in STATUS_TOPICS and not t.startswith(CATEGORY_PREFIX)],
        "language": repo.get("language") or "—",
        "stars": repo.get("stargazers_count", 0),
        "forks": repo.get("forks_count", 0),
        "open_issues": repo.get("open_issues_count", 0),
        "is_fork": repo.get("fork", False),
        "live_url": live_url(repo),
        "created_at": repo.get("created_at"),
        "pushed_at": repo.get("pushed_at"),
        "days_since_push": idle,
        "has_readme": has_readme,
        "license": (repo.get("license") or {}).get("spdx_id") or "",
        "warnings": warnings,
    }


def render_readme_table(data):
    counts = data["counts"]
    lines = [
        f"_Last updated: {data['generated_at'][:16].replace('T', ' ')} UTC · "
        f"{counts['total']} repos · "
        f"✅ {counts['completed']} · 🚧 {counts['in-progress']} · "
        f"🛠️ {counts['needs-improvement']} · ❔ {counts['untagged']}_",
        "",
        "| Repository | Category | Status | Live | Last push | Health |",
        "|---|---|---|---|---|---|",
    ]
    for r in data["repos"]:
        pushed = (r["pushed_at"] or "")[:10] or "—"
        health = ", ".join(r["warnings"]) if r["warnings"] else "OK"
        desc = r["description"].replace("|", "\\|")
        name = f"[{r['name']}]({r['url']})" + (f"<br><sub>{desc}</sub>" if desc else "")
        live = f"[Open ↗]({r['live_url']})" if r["live_url"] else "—"
        lines.append(
            f"| {name} | {r['category']} | {README_LABELS[r['status']]} | {live} | {pushed} | {health} |"
        )
    return "\n".join(lines)


def update_readme(table):
    path = ROOT / "README.md"
    text = path.read_text(encoding="utf-8") if path.exists() else "# Repo Tracker\n"
    block = f"{START}\n{table}\n{END}"
    if START in text and END in text:
        before = text.split(START)[0]
        after = text.split(END, 1)[1]
        text = before + block + after
    else:
        text = text.rstrip() + "\n\n" + block + "\n"
    path.write_text(text, encoding="utf-8")


def main():
    if not OWNER:
        sys.exit("Set TRACK_USER (or run inside GitHub Actions).")

    raw = [r for r in list_repos(OWNER) if not r.get("archived")]
    repos = [build_record(r) for r in raw]
    repos.sort(key=lambda r: (STATUS_ORDER.index(r["status"]), r["name"].lower()))

    counts = {s: 0 for s in STATUS_ORDER}
    for r in repos:
        counts[r["status"]] += 1
    counts["total"] = len(repos)

    categories = {}
    for r in repos:
        c = categories.setdefault(r["category"], {s: 0 for s in STATUS_ORDER})
        c[r["status"]] += 1

    data = {
        "owner": OWNER,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "stale_days": STALE_DAYS,
        "counts": counts,
        "categories": categories,
        "repos": repos,
    }

    out = ROOT / "docs" / "data.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2), encoding="utf-8")
    update_readme(render_readme_table(data))
    print(f"Tracked {len(repos)} repos for {OWNER}: {counts}")


if __name__ == "__main__":
    main()
