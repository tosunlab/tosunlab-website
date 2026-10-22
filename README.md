# tosunlab website

The tosunlab website: a Vue 3 single-page app.

## Develop

Node 16 is required. Newer versions break webpack 4.

```sh
yarn install
yarn serve
yarn lint
yarn build
```

## Run the image

```sh
docker build -t tosunlab-website .
docker run --rm -p 8080:8080 tosunlab-website
```

The container runs nginx on port 8080 as a non-root user.

## Release

GitHub Actions (`.github/workflows/`): `ci.yml` lints and builds on every pull request and builds the image without pushing; `release.yml` and `publish.yml` push to the GitHub Container Registry package `ghcr.io/tosunlab/tosunlab-website`.

1. `git tag -a website-0.1.0 -m "notes" && git push origin website-0.1.0`: the "Release website image" workflow pushes `ghcr.io/tosunlab/tosunlab-website:0.1.0` and `:sha-<commit>` (linux/amd64).
2. Run the Publish workflow with the tag (`gh workflow run publish.yml -f tag=website-0.1.0`) to point `:latest` and `:0.1` at it. A custom build (`website-0.1.0-test`) gets its own image tag and can't be published.

Anyone who can push a `website-*` tag or run a workflow can release, so protect `website-*` tags with a repository ruleset.
