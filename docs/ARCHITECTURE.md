# Architecture

```text
local tool logs / read-only databases
                 |
                 v
        tally-engine collectors
                 |
       stable JSON contract
                 |
                 v
 Tauri command <-> Vite UI <-> tray window
```

## Single engine source

All collectors, pricing resolution, date bucketing, replay deduplication, project aggregation, and Wrapped calculations live under `tally-engine/engine`. Development runs `python -m engine` from that directory. Release builds freeze `tally-engine/sidecar.py` into a target-triple-named PyInstaller executable consumed by Tauri's sidecar API.

## Contract

Tool keys contain `ranges`, `daily`, and `projects`. Metadata keys start with `_`: `_pricing`, `_daily`, `_projects`, and optional `_errors`. Range buckets contain `in`, `out`, `cr`, `cw`, `reason`, `cost`, `models`, and `sessions`.

The UI treats this as a versioned internal API: it never scrapes collector files directly and never invents service-provider quota values.

## Failure boundaries

Collectors run independently so one malformed database does not blank the dashboard. In the desktop app, an engine failure is shown as an error. Anonymous sample data is restricted to browser preview and is never a silent production fallback.
