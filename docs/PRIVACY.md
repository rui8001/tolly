# Privacy

Tolly is designed to process usage data locally.

## Data read

Collectors look only in documented per-tool data locations or paths explicitly provided through `TALLY_*` environment variables. JSONL files are streamed, and SQLite databases are opened read-only. The engine derives aggregate Token counts, estimated cost, model names, dates, project display keys, and session counts.

## Data stored

The desktop app stores only user settings such as custom weekly budgets, selected tools, reset day, and optional plan labels in the operating system's application configuration directory. Tolly does not persist a copy of raw logs. Browser preview settings use local storage.

## Network

Normal collection and display do not require a network connection. Network access occurs only when the user explicitly:

- runs `python -m engine update-prices`; or
- enables the opt-in Grok live quota request with `TALLY_GROK_QUOTA=1` and supplies an API key.

No analytics or crash-reporting service is included.

## Reporting bugs

Use synthetic examples. Before attaching files, remove prompts, paths, usernames, account IDs, repository names, session IDs, and timestamps that could identify you or your work.
