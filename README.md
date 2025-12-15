# Smart Home SDK (Python)

This SDK can be installed locally for development or published to a registry.

Quick setup (development):

```bash
cd sdk/python
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

Dev tools:

```bash
pip install -r dev-requirements.txt
```

How to test the SDK in another project

- Option A — local editable install (recommended for development):

	In your other project folder create `requirements.txt` with:

	```text
	-e ../sdk/python
	```

	Then install:

	```bash
	pip install -r requirements.txt
	```

- Option B — install directly from this repository (CI or simple test):

	```bash
	pip install git+https://github.com/<your-org>/<repo>.git@vX.Y.Z#subdirectory=sdk/python
	```

- Option C — use GitHub Packages / PyPI published package:

	```bash
	pip install home-console-sdk
	```

Notes about dependencies

- `setup.py` contains `install_requires` and is the canonical list for packaging.
- `requirements.txt` is useful for local development and test runners — keep it in sync with `install_requires`.
- `dev-requirements.txt` contains build/test tools (`build`, `twine`, `pytest`).

Versioning and publishing

- Use semantic tags like `v0.0.1`, `v0.0.2` and push tags to trigger CI.
- Registries normally prevent re-uploading the same version. Bump the version in `setup.py` before re-tagging.

Testing examples

Create a small script in another project to import and call the SDK:

```python
from smarthome_sdk import CoreAPIClient
import asyncio

async def main():
		async with CoreAPIClient("http://localhost:8000") as c:
				# use client
				pass

asyncio.run(main())
```

If you want, I can add a tiny `examples/test_project` that demonstrates `-e ../sdk/python` install and a simple test script.
