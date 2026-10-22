"""Site content read from Markdown files under content/."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import markdown
import yaml


@dataclass(frozen=True)
class Maintainer:
    name: str
    github: str
    role: str


@dataclass(frozen=True)
class People:
    intro_html: str
    maintainers: tuple[Maintainer, ...]


@dataclass(frozen=True)
class Badge:
    label: str
    solid: bool


@dataclass(frozen=True)
class Project:
    slug: str
    name: str
    repo: str
    site: str | None
    badges: tuple[Badge, ...]
    channels: tuple[str, ...]
    tagline_html: str
    body_html: str
    order: int

    @property
    def github_url(self) -> str:
        return f"https://github.com/{self.repo}"


class ContentError(ValueError):
    pass


def render(text: str) -> str:
    return markdown.markdown(text)


_SEPARATOR_ROW = re.compile(r"^\|[\s:\-|]+\|$")


def _parse_table(lines: list[str]) -> list[dict[str, str]]:
    rows = [line.strip() for line in lines if line.strip().startswith("|")]
    if not rows:
        return []
    header = [cell.strip().lower() for cell in rows[0].strip("|").split("|")]
    records = []
    for row in rows[1:]:
        if _SEPARATOR_ROW.match(row):
            continue
        cells = [cell.strip() for cell in row.strip("|").split("|")]
        records.append(dict(zip(header, cells)))
    return records


def load_people(path: Path) -> People:
    lines = path.read_text(encoding="utf-8").splitlines()
    intro = [line for line in lines if not line.strip().startswith("|")]
    maintainers = []
    for row in _parse_table(lines):
        try:
            name, github = row["name"], row["github"]
        except KeyError as exc:
            raise ContentError(f"{path}: the table needs a {exc.args[0]!r} column") from exc
        maintainers.append(Maintainer(name, github.lstrip("@"), row.get("role") or "maintainer"))
    return People(render("\n".join(intro)), tuple(maintainers))


_FRONT_MATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)


def _split_front_matter(text: str, path: Path) -> tuple[dict, str]:
    match = _FRONT_MATTER.match(text)
    if not match:
        raise ContentError(f"{path}: expected YAML front matter between --- lines")
    meta = yaml.safe_load(match.group(1)) or {}
    return meta, text[match.end() :]


def _inline(html: str) -> str:
    """Strip the single <p> wrapper markdown puts around one paragraph."""
    return re.sub(r"^<p>(.*)</p>$", r"\1", html.strip(), flags=re.DOTALL)


def load_project(path: Path) -> Project:
    meta, body = _split_front_matter(path.read_text(encoding="utf-8"), path)
    for key in ("name", "repo"):
        if key not in meta:
            raise ContentError(f"{path}: front matter needs {key!r}")
    tagline, _, rest = body.strip().partition("\n\n")
    badges = meta.get("badges") or {}
    return Project(
        slug=path.stem,
        name=str(meta["name"]),
        repo=str(meta["repo"]),
        site=meta.get("site"),
        badges=tuple(
            [Badge(str(b), True) for b in badges.get("solid") or []]
            + [Badge(str(b), False) for b in badges.get("outline") or []]
        ),
        channels=tuple(str(c) for c in meta.get("channels") or []),
        tagline_html=_inline(render(tagline)),
        body_html=render(rest),
        order=int(meta.get("order", 0)),
    )


def load_projects(directory: Path) -> tuple[Project, ...]:
    projects = [load_project(p) for p in sorted(directory.glob("*.md"))]
    return tuple(sorted(projects, key=lambda p: (p.order, p.name.lower())))
