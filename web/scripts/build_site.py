#!/usr/bin/env python3
"""Build the static Dream Comics site from dated comic folders."""

from __future__ import annotations

import argparse
import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path


DATE_DIR_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-.+")
README_HEADING_RE = re.compile(r"^#\s+(\d{2})/(\d{2})/(\d{4})\s+-\s+(.+?)\s*$", re.MULTILINE)


@dataclass(frozen=True)
class Comic:
    slug: str
    date: str
    title: str
    source_dir: Path
    pages: list[Path]
    pdf: Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Dream Comics static site.")
    parser.add_argument("--root", default=".", help="Repository root.")
    parser.add_argument("--out", default="web/dist", help="Output directory.")
    parser.add_argument("--site-url", default="https://jetblackrlsh.github.io/Dream-Comics", help="Public site URL without trailing slash.")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    out = (root / args.out).resolve()
    site_url = args.site_url.rstrip("/")
    source_web = root / "web"

    comics = discover_comics(root)
    if not comics:
        raise SystemExit("No dated comic folders with pages and PDFs were found.")

    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    copy_app_shell(source_web, out)
    manifest = copy_comics(comics, out)
    write_json(out / "data" / "comics.json", {"comics": manifest})
    write_pages(out, manifest, site_url)

    print(f"Built {len(manifest)} comics into {out}")


def discover_comics(root: Path) -> list[Comic]:
    comics: list[Comic] = []
    for directory in sorted(path for path in root.iterdir() if path.is_dir() and DATE_DIR_RE.match(path.name)):
        page_dir = directory / "assets" / "comic-pages"
        pdf_dir = directory / "output" / "pdf"
        pages = sorted(page_dir.glob("page-*.png"))
        pdfs = sorted(pdf_dir.glob("*.pdf"))
        if not pages or not pdfs:
            continue

        readme = directory / "README.md"
        heading = README_HEADING_RE.search(readme.read_text(encoding="utf-8")) if readme.exists() else None
        if heading:
            month, day, year, title = heading.groups()
            date = f"{year}-{month}-{day}"
        else:
            date = directory.name[:10]
            title = title_from_slug(directory.name[11:])

        comics.append(Comic(
            slug=directory.name,
            date=date,
            title=title,
            source_dir=directory,
            pages=pages,
            pdf=pdfs[0],
        ))

    return sorted(comics, key=lambda comic: (comic.date, comic.slug))


def copy_app_shell(source_web: Path, out: Path) -> None:
    for filename in ("index.html", "styles.css", "app.js"):
        shutil.copy2(source_web / filename, out / filename)

    generated_out = out / "assets" / "generated"
    generated_out.mkdir(parents=True)
    for image in (source_web / "assets" / "generated").glob("*.png"):
        if image.name == "site-concept.png":
            continue
        shutil.copy2(image, generated_out / image.name)


def copy_comics(comics: list[Comic], out: Path) -> list[dict[str, object]]:
    manifest: list[dict[str, object]] = []
    assets_root = out / "comics-assets"
    assets_root.mkdir()

    for comic in comics:
        comic_out = assets_root / comic.slug
        pages_out = comic_out / "pages"
        pages_out.mkdir(parents=True)

        page_paths: list[str] = []
        for page in comic.pages:
            target = pages_out / page.name
            shutil.copy2(page, target)
            page_paths.append(target.relative_to(out).as_posix())

        pdf_target = comic_out / comic.pdf.name
        shutil.copy2(comic.pdf, pdf_target)

        manifest.append({
            "slug": comic.slug,
            "date": comic.date,
            "title": comic.title,
            "cover": page_paths[0],
            "pages": page_paths,
            "pdf": pdf_target.relative_to(out).as_posix(),
            "pdfName": comic.pdf.name,
        })

    return manifest


def write_pages(out: Path, comics: list[dict[str, object]], site_url: str) -> None:
    index_html = (out / "index.html").read_text(encoding="utf-8")
    first = comics[0]
    (out / "index.html").write_text(with_meta(index_html, {
        "title": "Dream Comics",
        "description": "Browse Dream Comics by date, read each comic in a vertical webtoon-style reader, download PDFs, and support future issues.",
        "url": f"{site_url}/",
        "image": f"{site_url}/{first['cover']}",
    }), encoding="utf-8")

    about_dir = out / "about"
    about_dir.mkdir()
    (about_dir / "index.html").write_text(with_meta(index_html, {
        "title": "About Dream Comics",
        "description": "Dream Comics adapts actual dream journal entries and lucid dream adventures in the Storyverse into bright anime comics.",
        "url": f"{site_url}/about/",
        "image": f"{site_url}/assets/generated/dream-comics-logo.png",
    }), encoding="utf-8")

    comics_dir = out / "comics"
    comics_dir.mkdir()
    for comic in comics:
        page_dir = comics_dir / str(comic["slug"])
        page_dir.mkdir()
        title = f"{comic['title']} | Dream Comics"
        description = f"Read {comic['title']}, a Dream Comic dated {comic['date']}, in a vertical browser reader."
        (page_dir / "index.html").write_text(with_meta(index_html, {
            "title": title,
            "description": description,
            "url": f"{site_url}/comics/{comic['slug']}/",
            "image": f"{site_url}/{comic['cover']}",
        }), encoding="utf-8")


def with_meta(html: str, meta: dict[str, str]) -> str:
    replacements = {
        r"<title>.*?</title>": f"<title>{escape(meta['title'])}</title>",
        r'<meta name="description" content=".*?">': f'<meta name="description" content="{escape(meta["description"])}">',
        r'<meta property="og:title" content=".*?">': f'<meta property="og:title" content="{escape(meta["title"])}">',
        r'<meta property="og:description" content=".*?">': f'<meta property="og:description" content="{escape(meta["description"])}">',
        r'<meta property="og:image" content=".*?">': f'<meta property="og:image" content="{escape(meta["image"])}">',
    }
    for pattern, value in replacements.items():
        html = re.sub(pattern, value, html, count=1, flags=re.DOTALL)

    extra = f'    <meta property="og:url" content="{escape(meta["url"])}">\n    <meta name="twitter:card" content="summary_large_image">\n'
    html = html.replace("    <link rel=\"stylesheet\" href=\"styles.css\">", extra + "    <link rel=\"stylesheet\" href=\"/Dream-Comics/styles.css\">")
    html = html.replace("    <script defer src=\"app.js\"></script>", "    <script defer src=\"/Dream-Comics/app.js\"></script>")
    html = html.replace("src=\"assets/generated/dream-comics-logo.png\"", "src=\"/Dream-Comics/assets/generated/dream-comics-logo.png\"")
    return html


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def title_from_slug(slug: str) -> str:
    return " ".join(part.capitalize() for part in slug.split("-"))


def escape(value: object) -> str:
    return str(value).replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")


if __name__ == "__main__":
    main()
