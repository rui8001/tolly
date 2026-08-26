"""Allow ``python -m engine --json``."""
from .cli import main_cli

if __name__ == "__main__":
    raise SystemExit(main_cli())
