# ghdir

Download a subdirectory of a GitHub repository.

## Install

```sh
pip install -e .
```

## Usage

```sh
ghdir https://github.com/NVlabs/Eagle/tree/main/Embodied
```

Downloads the files under `Embodied/` into a local `Embodied/` folder.

## Roadmap status

- [x] Phase 1 — MVP: URL parse, resolve, download
- [ ] Phase 2 — CLI polish (`-o`/`--branch`, progress, dry-run)
- [ ] Phase 3 — async, retries, resumability
- [ ] Phase 4 — include/exclude/max-size filters
- [ ] Phase 5 — git sparse-checkout backend
- [ ] Phase 6 — auth / private repos