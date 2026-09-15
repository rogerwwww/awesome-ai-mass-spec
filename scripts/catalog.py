"""Catalog loading, validation, and README rendering utilities."""

from __future__ import annotations

import csv
import html
import re
import tomllib
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
PAPERS_PATH = ROOT / "data" / "papers.csv"
CATEGORIES_PATH = ROOT / "data" / "categories.toml"
HEADER_PATH = ROOT / "data" / "header.md"

CSV_FIELDS = (
    "categories",
    "title",
    "method_name",
    "authors",
    "venue",
    "year",
    "publication_type",
    "paper_url",
    "doi",
    "code_url",
    "code_license",
)
PUBLICATION_TYPES = {"journal", "conference", "workshop", "preprint"}
DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$", re.IGNORECASE)
AUTHOR_DISPLAY_LIMIT = 15
AUTHOR_DISPLAY_PREFIX = 13


@dataclass(frozen=True)
class Category:
    slug: str
    label: str
    description: str


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).casefold()
    return "".join(character for character in value if character.isalnum())


def load_categories(path: Path = CATEGORIES_PATH) -> list[Category]:
    with path.open("rb") as handle:
        raw = tomllib.load(handle)
    return [Category(**item) for item in raw.get("categories", [])]


def load_papers(path: Path = PAPERS_PATH) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != CSV_FIELDS:
            raise ValueError(
                f"unexpected CSV header: {reader.fieldnames!r}; expected {list(CSV_FIELDS)!r}"
            )
        return [{key: (value or "").strip() for key, value in row.items()} for row in reader]


def assigned_categories(paper: dict[str, str]) -> list[str]:
    return [slug.strip() for slug in paper["categories"].split(";") if slug.strip()]


def _is_https_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc) and not any(char.isspace() for char in value)


def _external_identifier(paper: dict[str, str]) -> str | None:
    if paper["doi"]:
        return f"doi:{paper['doi'].casefold()}"
    url = paper["paper_url"].casefold().rstrip("/")
    for pattern in (
        r"arxiv\.org/abs/([^/?#]+)",
        r"openreview\.net/forum\?id=([^&#]+)",
    ):
        match = re.search(pattern, url)
        if match:
            return f"external:{match.group(1)}"
    return None


def validate_catalog(
    papers: list[dict[str, str]], categories: list[Category]
) -> list[str]:
    errors: list[str] = []
    slugs = [category.slug for category in categories]
    labels = [category.label for category in categories]
    if not categories:
        errors.append("category configuration is empty")
    if len(slugs) != len(set(slugs)):
        errors.append("category slugs must be unique")
    if len(labels) != len(set(labels)):
        errors.append("category labels must be unique")

    known_slugs = set(slugs)
    seen_titles: dict[str, int] = {}
    seen_identifiers: dict[str, int] = {}
    for index, paper in enumerate(papers, start=2):
        prefix = f"CSV row {index}"
        for field in ("categories", "title", "authors", "venue", "year", "publication_type", "paper_url"):
            if not paper[field]:
                errors.append(f"{prefix}: {field} is required")
        if "et al." in paper["authors"].casefold():
            errors.append(f"{prefix}: authors must contain the complete author list, not et al.")

        assigned = assigned_categories(paper)
        if ";".join(assigned) != paper["categories"]:
            errors.append(f"{prefix}: categories must use semicolons without surrounding spaces")
        if len(assigned) != len(set(assigned)):
            errors.append(f"{prefix}: category assignments must not repeat")
        unknown = [slug for slug in assigned if slug not in known_slugs]
        if unknown:
            errors.append(f"{prefix}: unknown categories: {', '.join(unknown)}")

        try:
            year = int(paper["year"])
            if not 1900 <= year <= 2100:
                raise ValueError
        except ValueError:
            errors.append(f"{prefix}: year must be an integer from 1900 through 2100")
        if paper["publication_type"] not in PUBLICATION_TYPES:
            errors.append(
                f"{prefix}: publication_type must be one of {sorted(PUBLICATION_TYPES)}"
            )
        if paper["paper_url"] and not _is_https_url(paper["paper_url"]):
            errors.append(f"{prefix}: paper_url must be an HTTPS URL")
        if paper["doi"]:
            if paper["doi"].lower().startswith(("http://", "https://", "doi:")):
                errors.append(f"{prefix}: doi must be bare, without a URL or doi: prefix")
            elif not DOI_RE.match(paper["doi"]):
                errors.append(f"{prefix}: doi has an invalid format")
        if paper["code_url"] and not _is_https_url(paper["code_url"]):
            errors.append(f"{prefix}: code_url must be an HTTPS URL")
        if bool(paper["code_url"]) != bool(paper["code_license"]):
            errors.append(f"{prefix}: code_url and code_license must either both be set or both be blank")

        title_key = normalize_text(paper["title"])
        if title_key in seen_titles:
            errors.append(f"{prefix}: duplicate title (first seen at CSV row {seen_titles[title_key]})")
        else:
            seen_titles[title_key] = index
        identifier = _external_identifier(paper)
        if identifier:
            if identifier in seen_identifiers:
                errors.append(
                    f"{prefix}: duplicate external identifier (first seen at CSV row {seen_identifiers[identifier]})"
                )
            else:
                seen_identifiers[identifier] = index
    return errors


def markdown_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")


def markdown_code(value: str) -> str:
    """Wrap arbitrary text in a valid Markdown inline-code span."""
    longest_run = max((len(run) for run in re.findall(r"`+", value)), default=0)
    fence = "`" * (longest_run + 1)
    padding = " " if value.startswith(("`", " ")) or value.endswith(("`", " ")) else ""
    return f"{fence}{padding}{value}{padding}{fence}"


def format_authors(value: str) -> str:
    """Shorten exceptionally long lists while retaining the final author."""
    authors = [author.strip() for author in value.split(";") if author.strip()]
    if len(authors) <= AUTHOR_DISPLAY_LIMIT:
        return "; ".join(authors)
    return "; ".join(authors[:AUTHOR_DISPLAY_PREFIX] + ["...", authors[-1]])


def anchor(label: str) -> str:
    value = unicodedata.normalize("NFKD", label).casefold()
    value = re.sub(r"[^a-z0-9 -]", "", value)
    return re.sub(r"[- ]+", "-", value).strip("-")


def render_readme(
    papers: list[dict[str, str]], categories: list[Category], header: str
) -> str:
    errors = validate_catalog(papers, categories)
    if errors:
        raise ValueError("catalog validation failed:\n- " + "\n- ".join(errors))

    lines = [header.rstrip(), "", "<!-- BEGIN GENERATED CATALOG -->", "", "## Contents", ""]
    for category in categories:
        count = sum(category.slug in assigned_categories(paper) for paper in papers)
        lines.append(f"- [{category.label}](#{anchor(category.label)}) ({count})")

    for category in categories:
        lines.extend(["", f"## {category.label}", "", category.description, ""])
        category_papers = [
            paper for paper in papers if category.slug in assigned_categories(paper)
        ]
        category_papers.sort(key=lambda paper: (-int(paper["year"]), normalize_text(paper["title"])))
        for paper in category_papers:
            title = markdown_escape(paper["title"])
            authors = markdown_escape(format_authors(paper["authors"]))
            venue = markdown_escape(paper["venue"])
            links = [f"[paper]({paper['paper_url']})"]
            if paper["doi"]:
                links.append(f"[DOI](https://doi.org/{paper['doi']})")
            if paper["code_url"]:
                source_label = (
                    "source"
                    if paper["code_license"] == "NOASSERTION"
                    or "-NC" in paper["code_license"]
                    or "-ND" in paper["code_license"]
                    else "code"
                )
                links.append(
                    f"[{source_label}]({paper['code_url']}) <kbd>{html.escape(paper['code_license'])}</kbd>"
                )
            author_punctuation = "" if authors.endswith((".", "!", "?")) else "."
            method_prefix = f"{markdown_code(paper['method_name'])} " if paper["method_name"] else ""
            lines.append(
                f"- {method_prefix}**{title}** — {authors}{author_punctuation} *{venue}* ({paper['year']}). "
                + " · ".join(links)
            )

    lines.extend(["", "<!-- END GENERATED CATALOG -->", ""])
    return "\n".join(lines)
