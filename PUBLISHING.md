# Publishing to PyPI

This repo publishes the **`ezseedfinder`** package to [PyPI](https://pypi.org/project/ezseedfinder/).

## CLI after install

```bash
pip install ezseedfinder
ezsf -f examples/speedrun.ezsf -n 5   # headless search
ezsf -gui                             # graphical interface
```

## One-time PyPI setup

1. Create a [PyPI](https://pypi.org/) account and register the project name `ezseedfinder`.
2. On PyPI → **Your projects** → **ezseedfinder** → **Publishing**, add a **trusted publisher**:
   - Owner: your GitHub org or username
   - Repository: `ezseedfinder` (update when the repo exists)
   - Workflow: `publish.yml`
   - Environment: `pypi` (optional; matches the workflow)
3. In GitHub → **Settings** → **Environments**, create a **`pypi`** environment (used by the workflow).

Alternatively, add a repository secret `PYPI_API_TOKEN` and replace the publish step with:

```yaml
- run: python -m pip install twine
- run: python -m twine upload dist/*
  env:
    TWINE_USERNAME: __token__
    TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
```

## Release process

1. Bump `__version__` in `ezseedfinder/__init__.py`.
2. Commit and push.
3. Create a GitHub **Release** (or push a tag like `v0.2.0`) — the workflow builds and uploads to PyPI.

Linux CI builds a platform wheel via a setuptools `Extension` (`cubiomespi.lib_c`), then repairs it with `auditwheel` for PyPI. Windows installs compile `lib.dll` from the sdist during `pip install`.

To publish manually from a checkout:

```bash
pip install build twine
python -m build
twine upload dist/*
```
