# Site content

Edit these files to change the people and projects on the site. The app reads them on every page load, so a change shows after a refresh.

## maintainers.md

Any text before the table is the intro paragraph of the People section, in Markdown. The table needs the columns `Name` and `GitHub`. `Role` is optional and defaults to `maintainer`. The avatar comes from the GitHub handle.

## projects/*.md

One file per project. The YAML front matter needs `name` and `repo` (the GitHub `owner/name`). Optional keys:

- `site`: a homepage, linked after the name.
- `badges.solid` and `badges.outline`: short labels shown as filled and outlined badges.
- `channels`: release channels for the versions table. A channel named `Desktop` picks up the newest GitHub release whose tag starts with `desktop-`.
- `order`: sort key, lowest first. Ties sort by name.

The first paragraph of the body is the tagline. Everything after it is rendered as Markdown under the badges.
