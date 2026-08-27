# Privacy

Tolly is designed to process usage data locally.

## Data read

Collectors look only in documented per-tool data locations or paths explicitly provided through `TALLY_*` environment variables. JSONL files are streamed, and SQLite databases are opened read-only. The engine derives aggregate Token counts, estimated cost, model names, dates, project display keys, and session counts. When a service exposes explicit quota metadata through its local logs or a documented local read-only interface, Tolly may also display the remaining percentage/credits and reset time; it does not infer balances from usage.

## Data stored

The desktop app stores only display-card choices, refresh frequency, and the opt-in QwenWork quota preference in the operating system's application configuration directory. It does not store manually entered balances and does not persist a copy of raw logs. Browser preview settings use local storage.

## Network

Token collection and display are local. Codex quota display asks the installed Codex app server for the current account limit during refresh; Codex may use its existing login session and network connection to update that value. Other network access occurs only when the user explicitly:

- runs `python -m engine update-prices`; or
- enables the opt-in Grok live quota request with `TALLY_GROK_QUOTA=1` and supplies an API key; or
- enables QwenWork quota lookup. Tolly then calls only the authenticated read-only `qwenwork.usage` resource exposed by QwenWork on `127.0.0.1`. QwenWork itself may use its existing login session to refresh the quota from its service. Tolly does not read QwenWork authentication files or browser cookies.

Tolly does not read Codex authentication files, and it ignores model-specific limit buckets.

No analytics or crash-reporting service is included.

## Reporting bugs

Use synthetic examples. Before attaching files, remove prompts, paths, usernames, account IDs, repository names, session IDs, and timestamps that could identify you or your work.
