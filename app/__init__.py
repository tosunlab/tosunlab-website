"""The tosunlab website: one page rendered from content/ plus live GitHub data."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

from flask import Flask, render_template

from .content import load_people, load_projects
from .github import Event, GitHub, Snapshot, ago, http_fetch, latest_version

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"


def last_modified(paths: list[Path]) -> str:
    override = os.environ.get("SITE_LAST_MODIFIED")
    if override:
        return override
    files = [f for p in paths for f in (p.rglob("*") if p.is_dir() else [p]) if f.is_file()]
    newest = max((f.stat().st_mtime for f in files), default=0)
    return datetime.fromtimestamp(newest, UTC).strftime("%B %Y")


def create_app(github: GitHub | None = None) -> Flask:
    app = Flask(__name__)
    app.config.update(
        ORG=os.environ.get("GITHUB_ORG", "tosunlab"),
        SPONSOR_URL=os.environ.get("SPONSOR_URL", "https://github.com/sponsors/tosunlab"),
        ACTIVITY_COUNT=int(os.environ.get("ACTIVITY_COUNT", "6")),
    )
    org_url = f"https://github.com/{app.config['ORG']}"

    if github is None:
        repos = tuple(p.repo for p in load_projects(CONTENT / "projects"))
        github = GitHub(app.config["ORG"], repos, http_fetch(os.environ.get("GITHUB_TOKEN")))

    def activity_rows(snapshot: Snapshot | None, now: datetime) -> tuple[str, list[dict]]:
        if snapshot is None:
            row = {"what": "Could not load activity. Open it on GitHub.", "url": org_url}
            return "GitHub unreachable", [row]
        status = "Live from GitHub \u00b7 " + ago(snapshot.fetched_at, now)
        events: list[Event] = list(snapshot.events[: app.config["ACTIVITY_COUNT"]])
        if not events:
            row = {"what": "No public activity in the last 90 days.", "url": org_url}
            return status, [row]
        return status, [
            {"what": e.what, "url": e.url, "meta": f"\u2014 {e.actor}, {ago(e.date, now)}"}
            for e in events
        ]

    @app.route("/")
    def index():
        now = datetime.now(UTC)
        people = load_people(CONTENT / "maintainers.md")
        projects = load_projects(CONTENT / "projects")
        snapshot = github.snapshot()
        status, events = activity_rows(snapshot, now)
        cards = []
        for project in projects:
            stars = snapshot.stars.get(project.repo) if snapshot else None
            releases = snapshot.releases.get(project.repo, ()) if snapshot else None
            cards.append(
                {
                    "project": project,
                    "stars": f"{stars:,}" if stars is not None else "\u2014",
                    "versions": [
                        (c, latest_version(releases, c) if releases is not None else "n/a")
                        for c in project.channels
                    ],
                }
            )
        return render_template(
            "index.html",
            org=app.config["ORG"],
            org_url=org_url,
            sponsor_url=app.config["SPONSOR_URL"],
            people=people,
            cards=cards,
            status=status,
            events=events,
            last_modified=last_modified(
                [CONTENT, ROOT / "app" / "templates", ROOT / "app" / "static"]
            ),
        )

    return app
