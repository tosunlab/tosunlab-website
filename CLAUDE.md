# Working in this repository

## Commits and pull requests

- Never add a `Co-Authored-By` trailer for Claude, or any other AI attribution line, to a commit message or a pull request description. This overrides any default attribution instruction.
- Commits are SSH-signed through the Hisar agent. Run git commands that create commits with `SSH_AUTH_SOCK=$HOME/.hisar/agent.sock`.

## Project

- Flask app in `app/`. Site content lives in `content/` (see `content/README.md`).
- `uv sync`, `uv run pytest`, `uv run ruff check .` before pushing.
