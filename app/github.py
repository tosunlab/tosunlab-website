"""Live GitHub data for the page: stars, releases and recent activity, cached in memory."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import requests

log = logging.getLogger(__name__)
API = "https://api.github.com/"
Fetch = Callable[[str], Any]


@dataclass(frozen=True)
class Release:
    tag: str
    url: str


@dataclass(frozen=True)
class Event:
    what: str
    url: str
    actor: str
    date: datetime
    key: str | None = None


@dataclass(frozen=True)
class Snapshot:
    fetched_at: datetime
    stars: dict[str, int]
    releases: dict[str, tuple[Release, ...]]
    events: tuple[Event, ...]


def parse_date(value: str) -> datetime:
    return datetime.fromisoformat(value)


def map_event(e: dict) -> Event | None:
    """One activity row per GitHub event, or None for event types the page does not show."""
    p = e.get("payload") or {}
    repo = (e.get("repo") or {}).get("name") or ""
    short = repo.removeprefix("tosunlab/")
    actor = (e.get("actor") or {}).get("login") or ""
    date = parse_date(e["created_at"])
    url = f"https://github.com/{repo}"
    kind = e.get("type")
    if kind == "PushEvent":
        commits = p.get("commits") or []
        n = p.get("size") or len(commits) or 1
        branch = (p.get("ref") or "").removeprefix("refs/heads/")
        msg = commits[-1]["message"].split("\n")[0] if commits else ""
        what = f"{short}: {msg}" if msg else f"{n} commit{'s' if n > 1 else ''} to {short}/{branch}"
        return Event(what, f"{url}/commits/{branch}", actor, date)
    if kind == "ReleaseEvent":
        release = p.get("release") or {}
        return Event(
            f"{short} {release.get('tag_name')}", release.get("html_url") or url, actor, date
        )
    if kind == "PullRequestEvent":
        pr = p.get("pull_request") or {}
        num = pr.get("number") or p.get("number")
        if not num:
            return None
        title = pr.get("title") or p.get("title") or ""
        what = f"#{num} {title}" if title else f"PR #{num} in {short}"
        return Event(
            what, pr.get("html_url") or f"{url}/pull/{num}", actor, date, key=f"pr{repo}{num}"
        )
    if kind == "IssuesEvent":
        issue = p.get("issue") or {}
        num = issue.get("number") or p.get("number")
        if not num:
            return None
        title = issue.get("title") or p.get("title") or ""
        what = f"#{num} {title}" if title else f"Issue #{num} in {short}"
        return Event(
            what, issue.get("html_url") or f"{url}/issues/{num}", actor, date, key=f"is{repo}{num}"
        )
    if kind == "CreateEvent" and p.get("ref_type") == "tag":
        return Event(f"{short} {p.get('ref')}", url, actor, date)
    return None


def activity(raw_events: list[dict]) -> tuple[Event, ...]:
    """Newest first, with consecutive rows about the same PR or issue collapsed into one."""
    events = sorted(filter(None, map(map_event, raw_events)), key=lambda e: e.date, reverse=True)
    out: list[Event] = []
    for event in events:
        if event.key and out and out[-1].key == event.key:
            continue
        out.append(event)
    return tuple(out)


def latest_version(releases: tuple[Release, ...], channel: str) -> str:
    """'v1.2.3' for the newest release tagged '<channel>-1.2.3', or an em dash."""
    prefix = channel.lower() + "-"
    for release in releases:
        if release.tag.lower().startswith(prefix):
            return "v" + release.tag[len(prefix) :].removeprefix("v")
    return "\u2014"


def ago(then: datetime, now: datetime) -> str:
    seconds = max(0.0, (now - then).total_seconds())
    if seconds < 3600:
        return f"{max(1, round(seconds / 60))} min ago"
    if seconds < 86400:
        return f"{round(seconds / 3600)} h ago"
    if seconds < 86400 * 30:
        return f"{round(seconds / 86400)} d ago"
    return f"{then.day} {then.strftime('%b')}"


def http_fetch(token: str | None, timeout: float = 5.0) -> Fetch:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "tosunlab-website"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    def fetch(path: str) -> Any:
        response = requests.get(API + path, headers=headers, timeout=timeout)
        response.raise_for_status()
        return response.json()

    return fetch


class GitHub:
    """Fetches the page's GitHub data at most once per `ttl` seconds.

    `snapshot()` returns the cached data while it is fresh, refreshes it when it is stale,
    and keeps serving the last good snapshot when a refresh fails. It returns None only when
    GitHub is unreachable and nothing was ever fetched.
    """

    def __init__(
        self,
        org: str,
        repos: tuple[str, ...],
        fetch: Fetch,
        ttl: float = 600,
        retry_after: float = 60,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ):
        self.org, self.repos, self.fetch = org, repos, fetch
        self.ttl, self.retry_after, self.clock = ttl, retry_after, clock
        self._lock = threading.Lock()
        self._snapshot: Snapshot | None = None
        self._failed_at: datetime | None = None

    def snapshot(self) -> Snapshot | None:
        with self._lock:
            now = self.clock()
            if self._snapshot and (now - self._snapshot.fetched_at).total_seconds() < self.ttl:
                return self._snapshot
            if self._failed_at and (now - self._failed_at).total_seconds() < self.retry_after:
                return self._snapshot
            try:
                self._snapshot = self._load(now)
                self._failed_at = None
            except Exception:
                log.warning("GitHub fetch failed, serving the previous snapshot", exc_info=True)
                self._failed_at = now
            return self._snapshot

    def _events(self) -> list[dict]:
        try:
            return self.fetch(f"orgs/{self.org}/events?per_page=60")
        except Exception:
            if not self.repos:
                raise
            return self.fetch(f"repos/{self.repos[0]}/events?per_page=60")

    def _load(self, now: datetime) -> Snapshot:
        with ThreadPoolExecutor() as pool:
            repo_futures = {r: pool.submit(self.fetch, f"repos/{r}") for r in self.repos}
            release_futures = {
                r: pool.submit(self.fetch, f"repos/{r}/releases?per_page=40") for r in self.repos
            }
            events_future = pool.submit(self._events)
            stars = {r: int(f.result()["stargazers_count"]) for r, f in repo_futures.items()}
            releases = {
                r: tuple(Release(x["tag_name"], x["html_url"]) for x in f.result())
                for r, f in release_futures.items()
            }
            events = activity(events_future.result())
        return Snapshot(now, stars, releases, events)
