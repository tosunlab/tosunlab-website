from pathlib import Path

import pytest

from app.content import ContentError, load_people, load_project, load_projects


def test_people_table_and_intro(tmp_path: Path):
    path = tmp_path / "maintainers.md"
    path.write_text(
        "Two people.\n\n| Name | GitHub | Role |\n|---|---|---|\n"
        "| Ada Lovelace | @ada | maintainer |\n| Bob | bob | contributor |\n"
    )
    people = load_people(path)
    assert people.intro_html == "<p>Two people.</p>"
    assert [(m.name, m.github, m.role) for m in people.maintainers] == [
        ("Ada Lovelace", "ada", "maintainer"),
        ("Bob", "bob", "contributor"),
    ]


def test_people_role_defaults_to_maintainer(tmp_path: Path):
    path = tmp_path / "maintainers.md"
    path.write_text("| Name | GitHub |\n|---|---|\n| Ada | ada |\n")
    assert load_people(path).maintainers[0].role == "maintainer"


def test_people_missing_column_is_an_error(tmp_path: Path):
    path = tmp_path / "maintainers.md"
    path.write_text("| Name |\n|---|\n| Ada |\n")
    with pytest.raises(ContentError, match="github"):
        load_people(path)


def test_project_front_matter_and_body(tmp_path: Path):
    path = tmp_path / "hisar.md"
    path.write_text(
        "---\nname: Hisar\nrepo: tosunlab/hisar\nsite: https://tryhisar.com\n"
        "badges:\n  solid: [MCP]\n  outline: [E2E]\nchannels: [Desktop, CLI]\n---\n"
        "A *tagline*.\n\n- **For agents:** `hisar mcp` does things.\n"
    )
    project = load_project(path)
    assert project.slug == "hisar"
    assert project.github_url == "https://github.com/tosunlab/hisar"
    assert [(b.label, b.solid) for b in project.badges] == [("MCP", True), ("E2E", False)]
    assert project.channels == ("Desktop", "CLI")
    assert project.tagline_html == "A <em>tagline</em>."
    assert (
        "<li><strong>For agents:</strong> <code>hisar mcp</code> does things.</li>"
        in project.body_html
    )


def test_project_without_front_matter_is_an_error(tmp_path: Path):
    path = tmp_path / "x.md"
    path.write_text("# no front matter\n")
    with pytest.raises(ContentError, match="front matter"):
        load_project(path)


def test_projects_sort_by_order_then_name(tmp_path: Path):
    for name, order in (("b", 1), ("a", 1), ("c", 0)):
        (tmp_path / f"{name}.md").write_text(
            f"---\nname: {name}\nrepo: o/{name}\norder: {order}\n---\n"
        )
    assert [p.name for p in load_projects(tmp_path)] == ["c", "a", "b"]


def test_real_content_loads():
    root = Path(__file__).resolve().parent.parent / "content"
    assert len(load_people(root / "maintainers.md").maintainers) >= 1
    assert len(load_projects(root / "projects")) >= 1
