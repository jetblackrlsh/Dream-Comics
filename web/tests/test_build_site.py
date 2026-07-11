from __future__ import annotations

import importlib.util
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path


BUILD_SCRIPT = Path(__file__).parents[1] / "scripts" / "build_site.py"
SPEC = importlib.util.spec_from_file_location("dream_comics_build_site", BUILD_SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Could not load {BUILD_SCRIPT}")
build_site = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = build_site
SPEC.loader.exec_module(build_site)


class MetadataInjectionTests(unittest.TestCase):
    def test_generated_metadata_is_inserted_as_literal_text(self) -> None:
        description = (
            "Unicode survives—along with emoji 🌟 and regex-like text "
            r"such as \u2014, \1, and \g<1>."
        )
        template = """<!doctype html>
<html>
  <head>
    <!-- SEO_META_START -->
    <title>Placeholder</title>
    <!-- SEO_META_END -->
    <link rel="stylesheet" href="styles.css">
    <script defer src="app.js"></script>
  </head>
  <body><main></main></body>
</html>
"""
        meta = {
            "title": "Future Comic | Dream Comics",
            "description": description,
            "url": "https://example.com/comics/future-comic/",
            "image": "https://example.com/future-comic.jpg",
            "type": "article",
        }
        structured_data = {
            "@context": "https://schema.org",
            "@type": "ComicIssue",
            "description": description,
        }

        rendered = build_site.with_meta(
            template,
            meta,
            structured_data,
            "",
            "/Dream-Comics/",
            "https://example.com",
        )

        self.assertIn(build_site.escape(description), rendered)
        json_ld_match = re.search(
            r'<script type="application/ld\+json" id="structured-data">(.*?)</script>',
            rendered,
        )
        self.assertIsNotNone(json_ld_match)
        payload = json.loads(json_ld_match.group(1))
        self.assertEqual(description, payload["description"])


class ArtifactSizeTests(unittest.TestCase):
    def test_artifact_size_guard_rejects_oversized_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory)
            (output / "asset.bin").write_bytes(b"12345")

            self.assertEqual(5, build_site.validate_artifact_size(output, max_bytes=5))
            with self.assertRaisesRegex(SystemExit, "exceeding the 0 MB safety limit"):
                build_site.validate_artifact_size(output, max_bytes=4)


if __name__ == "__main__":
    unittest.main()
