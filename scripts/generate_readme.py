#!/usr/bin/env python3
"""Generate README.md from the structured paper catalog."""

from __future__ import annotations

import argparse
from pathlib import Path

from catalog import FOOTER_PATH, HEADER_PATH, ROOT, load_categories, load_papers, render_readme


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "README.md",
        help="output path (default: repository README.md)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit nonzero if the output differs instead of writing it",
    )
    args = parser.parse_args()

    rendered = render_readme(
        load_papers(),
        load_categories(),
        HEADER_PATH.read_text(encoding="utf-8"),
        FOOTER_PATH.read_text(encoding="utf-8"),
    )
    if args.check:
        if not args.output.exists() or args.output.read_text(encoding="utf-8") != rendered:
            print(f"{args.output} is out of date; run scripts/generate_readme.py")
            return 1
        print(f"{args.output} is up to date")
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
