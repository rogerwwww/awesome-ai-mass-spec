from __future__ import annotations

import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from catalog import (  # noqa: E402
    HEADER_PATH,
    format_authors,
    load_categories,
    load_papers,
    normalize_text,
    render_readme,
    validate_catalog,
)


class CatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.categories = load_categories()
        cls.papers = load_papers()
        cls.by_title = {paper["title"]: paper for paper in cls.papers}
        cls.header = HEADER_PATH.read_text(encoding="utf-8")

    def test_catalog_is_valid(self) -> None:
        self.assertEqual(validate_catalog(self.papers, self.categories), [])

    def test_readme_shortens_only_exceptionally_long_author_lists(self) -> None:
        fifteen = "; ".join(f"Author {index}" for index in range(1, 16))
        sixteen = "; ".join(f"Author {index}" for index in range(1, 17))
        self.assertEqual(format_authors(fifteen), fifteen)
        self.assertEqual(
            format_authors(sixteen),
            "Author 1; Author 2; Author 3; ...; Author 16",
        )

        rendered = render_readme(self.papers, self.categories, self.header)
        title = "MassSpecGym: A Benchmark for the Discovery and Identification of Molecules"
        self.assertIn(
            "Roman Bushuiev; Anton Bushuiev; Niek F. de Jonge; ...; Tomáš Pluskal",
            rendered,
        )
        self.assertNotIn(self.by_title[title]["authors"], rendered)

    def test_initial_catalog_is_not_accidentally_shrunk(self) -> None:
        self.assertGreaterEqual(len(self.papers), 70)
        self.assertEqual(
            len({normalize_text(paper["title"]) for paper in self.papers}),
            len(self.papers),
        )

    def test_known_reclassifications(self) -> None:
        self.assertEqual(
            self.by_title[
                "DENDRAL: A Case Study of the First Expert System for Scientific Hypothesis Formation"
            ]["categories"],
            "surveys",
        )

        self.assertEqual(
            self.by_title[
                "Agentic AI for Structural Elucidation and Discovery of Drug Metabolites from Mass Spectrometry Data"
            ]["categories"],
            "systems-agents",
        )

        for title in (
            "Substructure-Based Annotation of High-Resolution Multistage MSn Spectral Trees",
            "Automatic Compound Annotation from Mass Spectrometry Data Using MAGMa",
            "MetFrag Relaunched: Incorporating Strategies beyond In Silico Fragmentation",
        ):
            primary = self.by_title[title]["categories"].split(";")[0]
            self.assertEqual(primary, "structure-to-spectrum", title)

        self.assertNotIn(
            "candidate-retrieval",
            {category.slug for category in self.categories},
        )
        for paper in self.papers:
            self.assertNotIn("candidate-retrieval", paper["categories"].split(";"))

        self.assertEqual(
            self.by_title["MSNovelist: De Novo Structure Generation from Mass Spectra"]["categories"],
            "de-novo-elucidation",
        )
        self.assertEqual(
            self.by_title[
                "MS-GPT: Rethinking MS/MS De Novo Structure Elucidation as Spectrum-Induced Posterior Querying of a Molecule-Language Model"
            ]["categories"],
            "de-novo-elucidation",
        )
        for title in (
            "JESTR: Joint Embedding Space Technique for Ranking Candidate Molecules for the Annotation of Untargeted Metabolomics Data",
            "Learning from All Views: A Multiview Contrastive Framework for Metabolite Annotation",
            "FLARE: Fine-Grained Learning for Alignment of Spectra-Molecule REpresentation Enhances Metabolite Annotation",
        ):
            self.assertEqual(self.by_title[title]["categories"], "spectrum-to-fingerprint")
        self.assertEqual(
            self.by_title[
                "Rapid Prediction of Electron–Ionization Mass Spectrometry Using Neural Networks"
            ]["categories"],
            "structure-to-spectrum",
        )
        self.assertEqual(
            self.by_title[
                "Deep Learning Prediction of Electrospray Ionization Tandem Mass Spectra of Chemically Derived Molecules"
            ]["categories"],
            "structure-to-spectrum",
        )
        self.assertEqual(
            self.by_title[
                "An End-to-End Deep Learning Framework for Translating Mass Spectra to De-Novo Molecules"
            ]["categories"],
            "de-novo-elucidation",
        )
        self.assertEqual(
            self.by_title[
                "MADGEN: Mass-Spec Attends to De Novo Molecular Generation"
            ]["categories"],
            "de-novo-elucidation",
        )
        self.assertEqual(
            self.by_title[
                "GEMS: Molecular Structure Identification via Geodesic Navigation of the Isomer Manifold"
            ]["categories"].split(";")[0],
            "de-novo-elucidation",
        )
        self.assertEqual(
            self.by_title[
                "An Evaluation Methodology for Machine Learning-Based Tandem Mass Spectra Similarity Prediction"
            ]["categories"].split(";")[0],
            "datasets-benchmarks",
        )

    def test_multilabel_paper_renders_in_each_section(self) -> None:
        rendered = render_readme(self.papers, self.categories, self.header)
        title = "MolSpecFlow: Mass-Constrained Hybrid Flow Matching for Joint Molecular-Spectral Analysis"
        self.assertEqual(rendered.count(f"**{title}**"), 2)

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
