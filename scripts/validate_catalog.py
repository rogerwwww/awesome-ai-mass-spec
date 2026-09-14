#!/usr/bin/env python3
"""Validate the structured paper catalog."""

from catalog import load_categories, load_papers, validate_catalog


def main() -> int:
    papers = load_papers()
    errors = validate_catalog(papers, load_categories())
    if errors:
        print("Catalog validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Catalog is valid: {len(papers)} unique papers")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
