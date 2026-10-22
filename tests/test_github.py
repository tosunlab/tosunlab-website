from datetime import UTC, datetime, timedelta

import pytest

from app.github import GitHub, Release, activity, ago, latest_version, map_event

NOW = datetime(2026, 10, 23, 12, 0, tzinfo=UTC)


def raw(kind, payload, created="2026-10-23T11:00:00Z", repo="tosunlab/hisar"):
    return {
        "type": kind,
        "payload": payload,
        "repo": {"name": repo},
        "actor": {"login": "alperb"},
        "created_at": created,
    }


def test_push_uses_last_commit_message():
    e = map_event(
        raw(
            "PushEvent",
            {
                "ref": "refs/heads/main",
                "commits": [{"message": "a"}, {"message": "fix: thing\n\nbody"}],
            },
        )
    )
    assert (e.what, e.url) == (
        "hisar: fix: thing",
        "https://github.com/tosunlab/hisar/commits/main",
    )


def test_push_without_commits_counts_them():
    e = map_event(raw("PushEvent", {"ref": "refs/heads/main", "size": 3}))
    assert e.what == "3 commits to hisar/main"


def test_pull_request_and_issue_fall_back_to_number():
    pr = map_event(raw("PullRequestEvent", {"number": 7}))
    assert (pr.what, pr.url, pr.key) == (
        "PR #7 in hisar",
        "https://github.com/tosunlab/hisar/pull/7",
        "prtosunlab/hisar7",
    )
    issue = map_event(raw("IssuesEvent", {"issue": {"number": 2, "title": "Bug", "html_url": "u"}}))
    assert (issue.what, issue.url) == ("#2 Bug", "u")


def test_release_tag_and_dropped_kinds():
    assert (
        map_event(raw("ReleaseEvent", {"release": {"tag_name": "cli-1.0.0", "html_url": "r"}})).what
        == "hisar cli-1.0.0"
    )
    assert map_event(raw("CreateEvent", {"ref_type": "tag", "ref": "v1"})).what == "hisar v1"
    assert map_event(raw("CreateEvent", {"ref_type": "branch", "ref": "x"})) is None
    assert map_event(raw("WatchEvent", {})) is None
    assert map_event(raw("PullRequestEvent", {})) is None


def test_activity_sorts_newest_first_and_collapses_same_pr():
    rows = activity(
        [
            raw("PullRequestEvent", {"number": 1, "action": "opened"}, "2026-10-23T10:00:00Z"),
            raw("PushEvent", {"ref": "refs/heads/main"}, "2026-10-23T09:00:00Z"),
            raw("PullRequestEvent", {"number": 1, "action": "closed"}, "2026-10-23T11:00:00Z"),
            raw("WatchEvent", {}, "2026-10-23T11:30:00Z"),
        ]
    )
    assert [r.what for r in rows] == ["PR #1 in hisar", "1 commit to hisar/main"]


def test_latest_version_per_channel():
    releases = (
        Release("server-0.1.13", "a"),
        Release("desktop-v0.1.15", "b"),
        Release("server-0.1.12", "c"),
    )
    assert latest_version(releases, "Desktop") == "v0.1.15"
    assert latest_version(releases, "Server") == "v0.1.13"
    assert latest_version(releases, "CLI") == "—"


@pytest.mark.parametrize(
    "delta, text",
    [
        (timedelta(seconds=10), "1 min ago"),
        (timedelta(minutes=5), "5 min ago"),
        (timedelta(hours=3), "3 h ago"),
        (timedelta(days=2), "2 d ago"),
        (timedelta(days=40), "13 Sep"),
    ],
)
def test_ago(delta, text):
    assert ago(NOW - delta, NOW) == text


def canned(path):
    if path == "repos/tosunlab/hisar":
        return {"stargazers_count": 1234}
    if path.startswith("repos/tosunlab/hisar/releases"):
        return [{"tag_name": "cli-2.0.0", "html_url": "u"}]
    if path.startswith("orgs/"):
        return [raw("PushEvent", {"ref": "refs/heads/main", "commits": [{"message": "hi"}]})]
    raise AssertionError(path)


def test_snapshot_is_cached_for_ttl_and_refreshed_after():
    calls, clock = [], {"now": NOW}

    def fetch(path):
        calls.append(path)
        return canned(path)

    gh = GitHub("tosunlab", ("tosunlab/hisar",), fetch, ttl=600, clock=lambda: clock["now"])
    first = gh.snapshot()
    assert first.stars == {"tosunlab/hisar": 1234}
    assert first.events[0].what == "hisar: hi"
    assert gh.snapshot() is first
    assert len(calls) == 3
    clock["now"] += timedelta(seconds=601)
    assert gh.snapshot() is not first
    assert len(calls) == 6


def test_snapshot_serves_stale_data_when_github_fails():
    clock, broken = {"now": NOW}, {"on": False}

    def fetch(path):
        if broken["on"]:
            raise ConnectionError(path)
        return canned(path)

    gh = GitHub("tosunlab", ("tosunlab/hisar",), fetch, ttl=600, clock=lambda: clock["now"])
    first = gh.snapshot()
    broken["on"] = True
    clock["now"] += timedelta(seconds=601)
    assert gh.snapshot() is first


def test_snapshot_is_none_when_nothing_was_ever_fetched():
    calls = []

    def fetch(path):
        calls.append(path)
        raise ConnectionError(path)

    gh = GitHub("tosunlab", ("tosunlab/hisar",), fetch, retry_after=60)
    assert gh.snapshot() is None
    seen = len(calls)
    assert gh.snapshot() is None
    assert len(calls) == seen


def test_org_events_fall_back_to_repo_events():
    def fetch(path):
        if path.startswith("orgs/"):
            raise ConnectionError(path)
        if path.startswith("repos/tosunlab/hisar/events"):
            return []
        return canned(path)

    assert GitHub("tosunlab", ("tosunlab/hisar",), fetch).snapshot().events == ()
