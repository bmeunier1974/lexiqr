"""The `lexiqr` command line — the no-Python interface for lexicon authors.

This module may only call lexiqr's public API, never private modules (ADR 0002).
"""

import argparse


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="lexiqr",
        description="Inspect and check lexicon files without writing Python.",
    )
    parser.parse_args(argv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
