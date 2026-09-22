from __future__ import annotations

import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from catalog import (  # noqa: E402
    FOOTER_PATH,
    HEADER_PATH,
    format_authors,
    load_categories,
    load_papers,
    markdown_code,
    markdown_escape,
    normalize_text,
    render_readme,
    validate_catalog,
)


class CatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.categories = load_categories()
        cls.papers = load_papers()
        cls.header = HEADER_PATH.read_text(encoding="utf-8")

    def test_catalog_is_valid(self) -> None:
        self.assertEqual(validate_catalog(self.papers, self.categories), [])

    def test_readme_shortens_only_exceptionally_long_author_lists(self) -> None:
        fifteen = "; ".join(f"Author {index}" for index in range(1, 16))
        sixteen = "; ".join(f"Author {index}" for index in range(1, 17))
        self.assertEqual(format_authors(fifteen), fifteen)
        self.assertEqual(
            format_authors(sixteen),
            "; ".join([*(f"Author {index}" for index in range(1, 14)), "...", "Author 16"]),
        )

    def test_initial_catalog_is_not_accidentally_shrunk(self) -> None:
        self.assertGreaterEqual(len(self.papers), 84)
        self.assertEqual(
            len({normalize_text(paper["title"]) for paper in self.papers}),
            len(self.papers),
        )

    def test_every_paper_is_rendered_in_each_assigned_category(self) -> None:
        # The CSV is the catalog source of truth; this must cover new rows without
        # duplicating individual titles, categories, or method names in the tests.
        rendered = render_readme(self.papers, self.categories, self.header)
        lines = rendered.splitlines()
        for paper in self.papers:
            title = markdown_escape(paper["title"])
            method_prefix = (
                f"{markdown_code(paper['method_name'])} " if paper["method_name"] else ""
            )
            line_prefix = f"- {method_prefix}**{title}** —"
            matching_lines = [line for line in lines if line.startswith(line_prefix)]
            expected_count = len(paper["categories"].split(";"))
            self.assertEqual(len(matching_lines), expected_count, paper["title"])

    def test_validator_rejects_unknown_categories_and_bad_code_pairing(self) -> None:
        papers = deepcopy(self.papers)
        papers[0]["categories"] = "not-a-category"
        papers[1]["code_url"] = "https://github.com/example/example"
        papers[1]["code_license"] = ""
        errors = validate_catalog(papers, self.categories)
        self.assertTrue(any("unknown categories" in error for error in errors))
        self.assertTrue(any("code_url and code_license" in error for error in errors))

    def test_validator_rejects_abbreviated_author_lists(self) -> None:
        papers = deepcopy(self.papers)
        papers[0]["authors"] = "First Author; Second Author; et al."
        errors = validate_catalog(papers, self.categories)
        self.assertTrue(any("complete author list" in error for error in errors))

    def test_validator_rejects_duplicate_doi(self) -> None:
        papers = deepcopy(self.papers)
        papers[1]["doi"] = papers[0]["doi"]
        errors = validate_catalog(papers, self.categories)
        self.assertTrue(any("duplicate external identifier" in error for error in errors))

    def test_render_is_deterministic(self) -> None:
        first = render_readme(self.papers, self.categories, self.header)
        second = render_readme(load_papers(), load_categories(), self.header)
        self.assertEqual(first, second)
        with tempfile.TemporaryDirectory() as directory:
            first_path = Path(directory) / "first.md"
            second_path = Path(directory) / "second.md"
            first_path.write_text(first, encoding="utf-8")
            second_path.write_text(second, encoding="utf-8")
            self.assertEqual(first_path.read_bytes(), second_path.read_bytes())

    def test_related_repositories_footer_is_rendered_last(self) -> None:
        footer = FOOTER_PATH.read_text(encoding="utf-8")
        rendered = render_readme(self.papers, self.categories, self.header, footer)
        self.assertTrue(rendered.rstrip().endswith(footer.rstrip()))
        for repository in (
            "merlin-ms/awesome-mass-spectral-libraries",
            "josiehong/awesome-smallmol-massspec-ml",
            "enveda/computational-metabolomics-review",
        ):
            self.assertIn(f"https://github.com/{repository}", rendered)

    def test_each_section_is_sorted_newest_first_then_title(self) -> None:
        rendered = render_readme(self.papers, self.categories, self.header)
        for category in self.categories:
            papers = [
                paper for paper in self.papers if category.slug in paper["categories"].split(";")
            ]
            expected = sorted(
                papers,
                key=lambda paper: (-int(paper["year"]), normalize_text(paper["title"])),
            )
            section_start = rendered.index(f"## {category.label}\n")
            next_sections = [
                rendered.find(f"## {later.label}\n", section_start + 1)
                for later in self.categories
            ]
            next_sections = [position for position in next_sections if position > section_start]
            section_end = min(next_sections, default=len(rendered))
            section = rendered[section_start:section_end]
            positions = [section.index(f"**{paper['title']}**") for paper in expected]
            self.assertEqual(positions, sorted(positions))


if __name__ == "__main__":
    unittest.main()
