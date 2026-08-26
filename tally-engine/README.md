# Tolly usage engine

This directory is the single source of truth for Tolly's cross-platform data collection and aggregation.

```bash
python -m unittest discover -s tests -v
python -m engine --json
python -m engine projects
python -m engine daily-costs
python -m engine wrapped
```

Collectors are isolated modules under `engine/collectors`. JSONL files are streamed, SQLite sources are opened read-only, and paths can be overridden with documented `TALLY_*` environment variables. Optional zstd support is installed with `pip install -e ".[zstd]"`.

The JSON contract contains per-tool `ranges`, `daily`, and `projects`, plus `_pricing`, `_daily`, `_projects`, and optional `_errors` metadata. See [`../docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md) and the unit tests for the contract.
