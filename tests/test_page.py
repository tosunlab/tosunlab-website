from datetime import UTC, datetime

from app import create_app
from app.github import Event, GitHub, Release, Snapshot


class Stub(GitHub):
    def __init__(self, snapshot):
        self._snap = snapshot

    def snapshot(self):
        return self._snap


def page(snapshot):
    app = create_app(github=Stub(snapshot))
    app.testing = True
    return app.test_client().get("/").get_data(as_text=True)


def test_page_renders_content_and_live_data():
    now = datetime.now(UTC)
    snap = Snapshot(
        fetched_at=now,
        stars={"tosunlab/hisar": 1532},
        releases={
            "tosunlab/hisar": (Release("desktop-0.1.15", "u"), Release("server-0.1.13", "u"))
        },
        events=(Event("#9 Add thing", "https://github.com/tosunlab/hisar/pull/9", "alperb", now),),
    )
    html = page(snap)
    assert "<h1>tosunlab</h1>" in html
    assert "Alper Berber" in html and "@alperb" in html
    assert "https://github.com/alperb.png?size=96" in html
    assert "Four maintainers review every change that lands." in html
    assert ">Hisar</a>" in html and "tryhisar.com</a>" in html
    assert "1,532 stars" in html
    assert "<td>v0.1.15</td><td>v0.1.13</td><td>—</td><td>—</td>" in html
    assert "Live from GitHub · 1 min ago" in html
    assert '#9 Add thing</a> <span class="meta">— alperb, 1 min ago</span>' in html
    assert "https://github.com/sponsors/tosunlab" in html
    assert "border-radius" not in html


def test_page_when_github_is_unreachable():
    html = page(None)
    assert "GitHub unreachable" in html
    assert "— stars" in html
    assert "<td>n/a</td>" in html
    assert "Could not load activity. Open it on GitHub." in html
