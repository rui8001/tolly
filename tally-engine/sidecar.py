"""PyInstaller entry point used by the Windows desktop bundle."""

from engine.cli import main_cli


if __name__ == "__main__":
    raise SystemExit(main_cli())
