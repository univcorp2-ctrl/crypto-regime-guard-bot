# CI Status Note

The repository code, tests, devcontainer, docs, research scanner, and sample data were committed successfully.

Creating files under `.github/workflows/` failed twice through the current GitHub automation endpoint with:

```text
GitHub API 404: Not Found
```

Because normal repository files committed successfully and only workflow paths failed, the likely cause is that the GitHub automation token used by the Worker does not currently have permission to create or update workflow files. GitHub requires workflow-file permission/scope for `.github/workflows/*` changes.

The intended workflow definitions are stored in:

- `docs/workflows/ci.yml`
- `docs/workflows/research.yml`

After the automation token is granted workflow-file permission, copy or recommit those files to:

- `.github/workflows/ci.yml`
- `.github/workflows/research.yml`

Then the CI will run tests, linting, sample backtest artifact upload, and the 300+ repository research artifact workflow.
