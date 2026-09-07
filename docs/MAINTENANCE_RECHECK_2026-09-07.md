# Maintenance recheck — 2026-09-07

Source reviewed: `6d4ebd24a6de73c77188c1c3e9349cbe205def07` (public main). The downloaded source's Git tree matched the public commit tree.

## Reproduced checks

- Python 3.12 engine suite: 19 tests passed using synthetic fixtures.
- Node 24 interface suite: 11 tests passed.
- Version consistency and the existing tracked-data privacy check passed.
- Frozen-lockfile installation, production Vite build, and standalone preview build passed.
- Setup instructions now recommend Node 24, matching CI. The previous blanket Node 20+ requirement included versions below Vite's supported range.

The latest main [CI run](https://github.com/rui8001/tolly/actions/runs/33604443483) passed. The previously completed [Windows MSI smoke](https://github.com/rui8001/tolly/actions/runs/33603786413) passed. This recheck ran on macOS; it does not claim a new Windows run or an interactive Windows user test. The smoke covers MSI, not NSIS.

## Public evidence

- Latest release: v1.2.0; three public releases total.
- Stars: 0; forks: 0.
- [Trial invitation #9](https://github.com/rui8001/tolly/issues/9): no comments; no verified external trials recorded.
- v1.2.0 asset download counters: checksum 3, MSI 3, NSIS 0. Automated and maintainer activity may be included; these are not user counts.

## Remaining improvements

- Obtain voluntary Windows 10/11 feedback and add NSIS installation coverage.
- Expand synthetic collector coverage and exercise subprocess failures directly.
- Expand the privacy scanner beyond selected data extensions to documentation and source text.
- Review five pending dependency upgrades against current main, especially the Vite major upgrade and standalone packaging.

The application can enter final maintainer review while disclosing early adoption. The official program does not state a minimum of three trial users. Identity fields stay outside this repository; form submission requires the applicant's explicit confirmation.
