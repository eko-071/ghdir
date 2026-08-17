# ghdir

Download a single folder from a GitHub repo, without cloning the whole thing.

Point it at a GitHub tree URL and it grabs just that folder, keeping the
directory structure intact. You should probably use `git clone` if you're
downloading an entire repo, but this tool works for that as well.

## Install

```sh
pip install ghdir
```

or with [uv](https://docs.astral.sh/uv/):

```sh
uv tool install ghdir
```

Needs Python 3.11+.

### From source

```sh
git clone https://github.com/eko-071/ghdir.git
cd ghdir
uv tool install .
```

or with pip:

```sh
pip install .
```

## Updating

```sh
pip install --upgrade ghdir
```

or:

```sh
uv tool upgrade ghdir
```

If you installed from a local checkout instead, pull and reinstall:

```sh
cd ghdir
git pull
uv tool install . --force
```

## Usage

```sh
ghdir https://github.com/NVlabs/Eagle/tree/main/Embodied
```

This downloads everything under `Embodied/` into a local `Embodied/` folder.

A few flags if you need them:

- `-o, --output DIR` — where to put the files (default: the folder's own name)
- `--branch NAME` — use a different branch than the one in the URL
- `--dry-run` — see the file count and total size without downloading anything
- `--workers N` — number of concurrent downloads (default: 8)
- `--include GLOB` — only download files matching this glob (repeatable)
- `--exclude GLOB` — skip files matching this glob (repeatable)
- `--max-size SIZE` — skip files larger than `SIZE` (e.g. `50M`, `1.5G`)
- `--force` — re-download everything, even files that are already up to date
- `--version` — print the installed version and exit

Some examples:

```sh
# whole repo, default branch
ghdir https://github.com/octo/hello

# a different branch than what's in the URL
ghdir https://github.com/octo/hello/tree/main/src --branch dev

# custom destination
ghdir https://github.com/octo/hello/tree/main/src -o ./vendor/hello-src

# just check what it would download
ghdir https://github.com/octo/hello/tree/main/src --dry-run

# only Python files, nothing over 50M
ghdir https://github.com/octo/hello/tree/main/src --include "*.py" --max-size 50M
```

Running it looks like this:

```
Found 132 files (1482974 bytes) in main/Embodied
Downloaded 132 files to Embodied
```

Already-up-to-date files are skipped on re-runs. Only missing or changed
files are fetched. To force a fresh copy of everything, use `--force`:

```
Downloaded 0 files, skipped 132 already up to date, to Embodied
```

## Authentication

By default ghdir hits the GitHub API anonymously (60 requests/hour) and
cannot download from private repositories. Storing a token unlocks private
repos and raises the limit to 5000 requests/hour:

```sh
ghdir auth login     # prompts for a token, or pass --token TOKEN inline
ghdir auth status    # show who you're logged in as
ghdir auth logout    # remove the stored token
```

Tokens are saved to `~/.config/ghdir/token` (mode 0600). For CI or
scripted use, set the `GHDIR_TOKEN` environment variable instead — it
takes precedence over the stored file and needs no interactive prompt.

## Shell completion

ghdir supports tab completion for bash, zsh, fish, and PowerShell:

```sh
ghdir --install-completion
```

This detects your shell and installs completion for flags (`--branch`,
`--include`, etc.) and local directory paths for `-o/--output`. Restart
your shell, or source your rc file, for it to take effect.

## Developing

```sh
uv sync --extra dev           # install ghdir + dev deps
uv run pytest                 # unit tests, no network calls
uv run pytest -m integration  # live test against real GitHub repos
uv run ruff check src tests   # lint
```

## License

[MIT](LICENSE)