# ghdir

Download a single folder from a GitHub repo, without cloning the whole thing.

Point it at a GitHub tree URL and it grabs just that folder, keeping the
directory structure intact. You should probably use `git clone` if you're downloading an entire repo, but this tool works for that as well.

## Install

Not on PyPI yet, so clone the repo and install from your local checkout:
 
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
 
Since it's installed from a local checkout, pull the latest changes and
reinstall:
 
```sh
cd ghdir
git pull
uv tool install . --force
```
 
or with pip:
 
```sh
pip install . --force-reinstall
```

Needs Python 3.11+.

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
Downloaded 132 files (1482974 bytes) to Embodied
```

If something's wrong like a bad URL, missing folder, private repo, or a branch that
doesn't exist, you'll get one clear error line and a non-zero exit code,
not a stack trace.

## Developing

```sh
uv sync --extra dev           # install ghdir + dev deps
uv run pytest                 # unit tests, no network calls
uv run pytest -m integration  # live test against real GitHub repos
uv run ruff check src tests   # lint
```

## License

[MIT](LICENSE)