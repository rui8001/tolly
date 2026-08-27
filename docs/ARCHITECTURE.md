# Architecture

```text
local logs / read-only databases / local provider interfaces
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

Tool keys contain `ranges`, `daily`, `projects`, and optional `quota`. Metadata keys start with `_`: `_pricing`, `_daily`, `_projects`, and optional `_errors`. Range buckets contain `in`, `out`, `cr`, `cw`, `reason`, `cost`, `models`, and `sessions`.

`quota` is an extensible, provider-authored balance block. The UI prefers a verified `weekly` window, falls back to `credits`, and hides the block when neither exists. Collectors may only populate it from explicit provider fields such as `used_percent`, `resets_at`, or `balance`; consumption totals and estimated cost are never converted into an account balance. The Codex collector uses the installed app server's read-only `account/rateLimits/read` method and accepts only the account-wide `codex` bucket.

Collector-specific non-token metrics may be added to range buckets, for example WorkBuddy's `credits_used`. Estimates must be marked at tool level with `estimated: true`. A detector with no trustworthy usage field returns `detected: true` and a user-facing note instead of a fabricated total.

The UI treats this as a versioned internal API: it never scrapes collector files directly and never invents service-provider quota values.

## Failure boundaries

Collectors run independently so one malformed database does not blank the dashboard. In the desktop app, an engine failure is shown as an error. Anonymous sample data is restricted to browser preview and is never a silent production fallback.
