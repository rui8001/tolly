# Security policy

Please do not open a public issue for vulnerabilities that could expose local prompts, session paths, account identifiers, API keys, or arbitrary file contents.

Until a dedicated security address is published, use GitHub's private vulnerability reporting feature for this repository. Include the affected version, reproduction steps, and the minimum synthetic fixture needed to demonstrate the issue. Never attach real logs.

The latest tagged release is the only supported version. Tolly reads local tool data and launches a bundled helper, so path traversal, unsafe command construction, overly broad file discovery, and accidental telemetry are treated as security issues.
