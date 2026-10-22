# tosunlab website

The tosunlab website: one page rendered by Flask from Markdown content plus live GitHub data.

## Edit the content

The maintainer list and the projects live in `content/`. See `content/README.md` for the file formats.

- `content/maintainers.md`: the People section.
- `content/projects/*.md`: one file per project.

The app reads these files on every request, so a running server shows an edit after a refresh.

## Develop

Python 3.12 or newer and [uv](https://docs.astral.sh/uv/).

```sh
uv sync
uv run flask --app app run --debug
uv run pytest
uv run ruff check .
```

The server fetches stars, releases and recent activity from the GitHub API and caches them in memory for 10 minutes. Without a token the API allows 60 requests an hour per IP, enough for the three requests each refresh makes. Set `GITHUB_TOKEN` to raise the limit.

Environment variables, all optional:

| Variable | Default | Purpose |
|---|---|---|
| `GITHUB_TOKEN` | unset | Bearer token for the GitHub API. |
| `GITHUB_ORG` | `tosunlab` | Organization whose events feed "What's new". |
| `ACTIVITY_COUNT` | `6` | Number of rows in "What's new". |
| `SPONSOR_URL` | `https://github.com/sponsors/tosunlab` | Target of "Become a sponsor". |
| `SITE_LAST_MODIFIED` | newest file time | Footer "Last modified" text, for example `October 2026`. |

## Run the image

```sh
docker build -t tosunlab-website .
docker run --rm -p 8080:8080 tosunlab-website
```

The container runs gunicorn on port 8080 as a non-root user.

To deploy a released image, copy `docker-compose.yml` to the host and run `docker compose up -d`. Put `GITHUB_TOKEN=...` in a `.env` file next to it to raise the GitHub API limit.

## Release

GitHub Actions (`.github/workflows/`): `ci.yml` lints, tests and builds the image without pushing on every pull request; `release.yml` and `publish.yml` push to the GitHub Container Registry package `ghcr.io/tosunlab/tosunlab-website`.

1. `git tag -a website-1.0.0 -m "notes" && git push origin website-1.0.0`: the "Release website image" workflow pushes `ghcr.io/tosunlab/tosunlab-website:1.0.0` and `:sha-<commit>` (linux/amd64).
2. Run the Publish workflow with the tag (`gh workflow run publish.yml -f tag=website-1.0.0`) to point `:latest` and `:1.0` at it. A custom build (`website-1.0.0-test`) gets its own image tag and can't be published.

Anyone who can push a `website-*` tag or run a workflow can release, so protect `website-*` tags with a repository ruleset.
