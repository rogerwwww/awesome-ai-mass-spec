# Contributing

Thank you for helping maintain Awesome AI for Mass Spectrometry.

## Add or update a paper

1. Edit `data/papers.csv`; do not edit the generated catalog in `README.md`.
2. Keep the exact column order shown in the existing file.
3. Separate multiple category slugs with semicolons, putting the primary category first. Available categories and their definitions are in `data/categories.toml`.
4. Enter the complete author list in publication order, separated by semicolons. The generated README displays lists of up to 15 authors in full; longer lists appear as the first three authors, `...`, and the final author. The CSV always retains the complete list.
5. Use one of `journal`, `conference`, `workshop`, or `preprint` for `publication_type`.
6. Prefer the version-of-record metadata. Use a stable public paper page where possible, and store a DOI as a bare value such as `10.1234/example`.
7. Link source code only when the repository is controlled by the authors or official project. Record its SPDX license identifier. Use `NOASSERTION` when the repository is public but has no declared license; leave both source fields empty when there is no verified official repository.
8. Run the local checks:

   ```bash
   python scripts/validate_catalog.py
   python -m unittest discover -s tests -v
   python scripts/generate_readme.py --output /tmp/awesome-ai-mass-spec-README.md
   ```

Pull requests run the same read-only checks. After a catalog change is merged into `main`, GitHub Actions regenerates and commits `README.md` automatically.

For automatic publishing, repository maintainers must allow GitHub Actions to use a read/write workflow token, and branch rules must permit `github-actions[bot]` to update `README.md`. The validation workflow never receives write access.

## Scope and review

The editorial focus is AI for small-molecule mass spectrometry and metabolomics. Work from broader mass-spectrometry domains is welcome when its AI relevance is explicit. Both peer-reviewed papers and public preprints are eligible; announced-only or unverifiable work is not.

Categories are scientific claims, not merely keywords. A multi-label entry should use only categories that represent a material contribution of the paper. Maintainers may adjust category assignments during review.

## Change the taxonomy

Taxonomy changes require editing `data/categories.toml` and should explain why an existing category is insufficient. Slugs are stable public identifiers in the CSV, so renaming or removing one requires updating every affected row.
