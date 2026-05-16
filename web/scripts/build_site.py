#!/usr/bin/env python3
"""Build the static Dream Comics site from dated comic folders."""

from __future__ import annotations

import argparse
from datetime import date, datetime, time, timezone
from email.utils import format_datetime
import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


DATE_DIR_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-.+")
README_HEADING_RE = re.compile(r"^#\s+(\d{2})/(\d{2})/(\d{4})\s*(?:-|:)\s+(.+?)\s*$", re.MULTILINE)
LOG_LINE_RE = re.compile(r"^##\s+Logline\s+(.+?)(?=^##\s+|\Z)", re.MULTILINE | re.DOTALL)


@dataclass(frozen=True)
class Comic:
    slug: str
    date: str
    title: str
    description: str
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
    base_path = public_base_path(site_url)
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
    write_pages(out, manifest, site_url, base_path)
    write_support_files(out, manifest, site_url)

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
        description = comic_description(directory, title, date)

        comics.append(Comic(
            slug=directory.name,
            date=date,
            title=title,
            description=description,
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

    characters_out = out / "assets" / "characters"
    characters_out.mkdir(parents=True)
    for image in (source_web / "assets" / "characters").glob("*.png"):
        shutil.copy2(image, characters_out / image.name)


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
            "description": comic.description,
            "cover": page_paths[0],
            "pages": page_paths,
            "pdf": pdf_target.relative_to(out).as_posix(),
            "pdfName": comic.pdf.name,
        })

    return manifest


def write_pages(out: Path, comics: list[dict[str, object]], site_url: str, base_path: str) -> None:
    index_html = (out / "index.html").read_text(encoding="utf-8")
    latest = comics[-1]
    home_description = "Read Dream Comics, a Storyverse lucid dream comic series adapted from actual dream journal entries, with browser-readable issues, PDFs, and a cast guide."
    (out / "index.html").write_text(with_meta(index_html, {
        "title": "Dream Comics",
        "description": home_description,
        "url": canonical_url(site_url, "/"),
        "image": canonical_url(site_url, str(latest["cover"])),
        "type": "website",
    }, home_structured_data(comics, site_url), home_fallback(comics, site_url, base_path), base_path, site_url), encoding="utf-8")

    about_dir = out / "about"
    about_dir.mkdir()
    about_description = "Learn how Dream Comics adapts actual dream journal entries, lucid dreams, and Storyverse adventures into a growing comic series."
    (about_dir / "index.html").write_text(with_meta(index_html, {
        "title": "About Dream Comics",
        "description": about_description,
        "url": canonical_url(site_url, "about/"),
        "image": canonical_url(site_url, "assets/generated/dream-comics-logo.png"),
        "type": "website",
    }, {
        "@context": "https://schema.org",
        "@type": "AboutPage",
        "name": "About Dream Comics",
        "description": about_description,
        "url": canonical_url(site_url, "about/"),
        "isPartOf": site_reference(site_url),
    }, simple_fallback("About Dream Comics", about_description, canonical_url(site_url, "/"), "Browse comics"), base_path, site_url), encoding="utf-8")

    whos_dir = out / "whos-who"
    whos_dir.mkdir()
    whos_description = "Meet Jet, Leon, Johnson, Second Brain, Skelebot, Overdrive, Savannah, Tecton, Chipper, and Lucid Light from Dream Comics."
    (whos_dir / "index.html").write_text(with_meta(index_html, {
        "title": "Who's Who | Dream Comics",
        "description": whos_description,
        "url": canonical_url(site_url, "whos-who/"),
        "image": canonical_url(site_url, "assets/characters/jet.png"),
        "type": "website",
    }, whos_structured_data(site_url), simple_fallback("Dream Comics Who's Who", whos_description, canonical_url(site_url, "/"), "Browse comics"), base_path, site_url), encoding="utf-8")

    comics_dir = out / "comics"
    comics_dir.mkdir()
    for comic in comics:
        page_dir = comics_dir / str(comic["slug"])
        page_dir.mkdir()
        title = f"{comic['title']} | Dream Comics"
        description = str(comic.get("description") or f"Read {comic['title']}, a Dream Comics lucid dream comic dated {comic['date']}.")
        (page_dir / "index.html").write_text(with_meta(index_html, {
            "title": title,
            "description": description,
            "url": canonical_url(site_url, f"comics/{comic['slug']}/"),
            "image": canonical_url(site_url, str(comic["cover"])),
            "type": "article",
            "published": str(comic["date"]),
        }, comic_structured_data(comic, site_url), comic_fallback(comic, site_url, base_path), base_path, site_url), encoding="utf-8")


def with_meta(html: str, meta: dict[str, str], structured_data: object, fallback_html: str, base_path: str, site_url: str) -> str:
    meta = {**meta, "feed": canonical_url(site_url, "rss.xml")}
    html = re.sub(
        r"    <!-- SEO_META_START -->.*?    <!-- SEO_META_END -->",
        seo_meta_block(meta, structured_data),
        html,
        count=1,
        flags=re.DOTALL,
    )
    html = html.replace("    <link rel=\"stylesheet\" href=\"styles.css\">", f"    <link rel=\"stylesheet\" href=\"{base_path}styles.css\">")
    html = html.replace("    <script defer src=\"app.js\"></script>", f"    <script defer src=\"{base_path}app.js\"></script>")
    html = html.replace("href=\"./whos-who/\"", f"href=\"{base_path}whos-who/\"")
    html = html.replace("href=\"./about/\"", f"href=\"{base_path}about/\"")
    html = html.replace("href=\"./\"", f"href=\"{base_path}\"")
    html = html.replace("href=\"assets/", f"href=\"{base_path}assets/")
    html = html.replace("src=\"assets/", f"src=\"{base_path}assets/")
    if fallback_html:
        html = html.replace("      <main>", f"      <main>\n        <noscript>\n{indent(fallback_html, 10)}\n        </noscript>", 1)
    return html


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_support_files(out: Path, comics: list[dict[str, object]], site_url: str) -> None:
    sitemap_urls: list[dict[str, str]] = [
        {
            "loc": canonical_url(site_url, "/"),
            "lastmod": str(comics[-1]["date"]),
            "image": canonical_url(site_url, str(comics[-1]["cover"])),
            "image_title": "Dream Comics",
        },
        {
            "loc": canonical_url(site_url, "about/"),
            "lastmod": str(comics[-1]["date"]),
            "image": canonical_url(site_url, "assets/generated/dream-comics-logo.png"),
            "image_title": "Dream Comics",
        },
        {
            "loc": canonical_url(site_url, "whos-who/"),
            "lastmod": str(comics[-1]["date"]),
            "image": canonical_url(site_url, "assets/characters/jet.png"),
            "image_title": "Dream Comics Who's Who",
        },
    ]
    for comic in comics:
        sitemap_urls.append({
            "loc": canonical_url(site_url, f"comics/{comic['slug']}/"),
            "lastmod": str(comic["date"]),
            "image": canonical_url(site_url, str(comic["cover"])),
            "image_title": str(comic["title"]),
        })

    (out / "sitemap.xml").write_text(sitemap_xml(sitemap_urls), encoding="utf-8")
    (out / "rss.xml").write_text(rss_xml(comics, site_url), encoding="utf-8")
    (out / "robots.txt").write_text(
        "User-agent: *\n"
        "Allow: /\n\n"
        f"Sitemap: {canonical_url(site_url, 'sitemap.xml')}\n",
        encoding="utf-8",
    )


def seo_meta_block(meta: dict[str, str], structured_data: object) -> str:
    title = escape(meta["title"])
    description = escape(meta["description"])
    url = escape(meta["url"])
    image = escape(meta["image"])
    page_type = escape(meta.get("type", "website"))
    lines = [
        "    <!-- SEO_META_START -->",
        f"    <title>{title}</title>",
        f"    <meta name=\"description\" content=\"{description}\">",
        "    <meta name=\"robots\" content=\"index, follow\">",
        f"    <link rel=\"canonical\" href=\"{url}\">",
        f"    <meta property=\"og:type\" content=\"{page_type}\">",
        "    <meta property=\"og:site_name\" content=\"Dream Comics\">",
        f"    <meta property=\"og:title\" content=\"{title}\">",
        f"    <meta property=\"og:description\" content=\"{description}\">",
        f"    <meta property=\"og:url\" content=\"{url}\">",
        f"    <meta property=\"og:image\" content=\"{image}\">",
        f"    <link rel=\"alternate\" type=\"application/rss+xml\" title=\"Dream Comics RSS Feed\" href=\"{escape(meta['feed'])}\">",
        "    <meta name=\"twitter:card\" content=\"summary_large_image\">",
        f"    <meta name=\"twitter:title\" content=\"{title}\">",
        f"    <meta name=\"twitter:description\" content=\"{description}\">",
        f"    <meta name=\"twitter:image\" content=\"{image}\">",
    ]
    if meta.get("published"):
        lines.append(f"    <meta property=\"article:published_time\" content=\"{escape(meta['published'])}\">")
    json_ld = json.dumps(structured_data, separators=(",", ":")).replace("</", "<\\/")
    lines.append(f"    <script type=\"application/ld+json\" id=\"structured-data\">{json_ld}</script>")
    lines.append("    <!-- SEO_META_END -->")
    return "\n".join(lines)


def home_structured_data(comics: list[dict[str, object]], site_url: str) -> object:
    return {
        "@context": "https://schema.org",
        "@graph": [
            site_reference(site_url),
            {
                "@type": "ComicSeries",
                "@id": f"{canonical_url(site_url, '/')}#series",
                "name": "Dream Comics",
                "url": canonical_url(site_url, "/"),
                "description": "A lucid dream comic series adapted from actual dream journal entries in the Storyverse.",
                "hasPart": [
                    {
                        "@type": "ComicIssue",
                        "name": str(comic["title"]),
                        "url": canonical_url(site_url, f"comics/{comic['slug']}/"),
                        "datePublished": str(comic["date"]),
                    }
                    for comic in comics
                ],
            },
        ],
    }


def comic_structured_data(comic: dict[str, object], site_url: str) -> object:
    comic_url = canonical_url(site_url, f"comics/{comic['slug']}/")
    return {
        "@context": "https://schema.org",
        "@type": "ComicIssue",
        "@id": f"{comic_url}#comic",
        "name": str(comic["title"]),
        "description": str(comic["description"]),
        "url": comic_url,
        "image": canonical_url(site_url, str(comic["cover"])),
        "datePublished": str(comic["date"]),
        "isPartOf": {
            "@type": "ComicSeries",
            "name": "Dream Comics",
            "url": canonical_url(site_url, "/"),
        },
        "encoding": {
            "@type": "MediaObject",
            "encodingFormat": "application/pdf",
            "contentUrl": canonical_url(site_url, str(comic["pdf"])),
            "name": str(comic["pdfName"]),
        },
        "numberOfPages": len(comic["pages"]),
    }


def whos_structured_data(site_url: str) -> object:
    characters = ["Jet", "Leon", "Johnson", "Second Brain", "Skelebot", "Overdrive", "Savannah", "Tecton", "Chipper", "Lucid Light"]
    return {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": "Dream Comics Who's Who",
        "description": "Recurring Dream Comics cast, allies, vessels, and mythic forces.",
        "url": canonical_url(site_url, "whos-who/"),
        "isPartOf": site_reference(site_url),
        "mainEntity": {
            "@type": "ItemList",
            "itemListElement": [
                {"@type": "ListItem", "position": index + 1, "name": name}
                for index, name in enumerate(characters)
            ],
        },
    }


def site_reference(site_url: str) -> object:
    return {
        "@type": "WebSite",
        "@id": f"{canonical_url(site_url, '/')}#website",
        "name": "Dream Comics",
        "url": canonical_url(site_url, "/"),
    }


def home_fallback(comics: list[dict[str, object]], site_url: str, base_path: str) -> str:
    items = "\n".join(
        f'      <li><a href="{base_path}comics/{escape(comic["slug"])}/">{escape(comic["title"])}</a> - {escape(comic["date"])}</li>'
        for comic in comics
    )
    return (
        "    <section class=\"noscript-seo\" aria-label=\"Dream Comics index\">\n"
        "      <h1>Dream Comics</h1>\n"
        "      <p>Read Dream Comics, a Storyverse lucid dream comic series adapted from actual dream journal entries.</p>\n"
        f"      <p><a href=\"{escape(canonical_url(site_url, 'rss.xml'))}\">RSS feed</a> | <a href=\"{escape(canonical_url(site_url, 'sitemap.xml'))}\">Sitemap</a></p>\n"
        f"      <ul>\n{items}\n      </ul>\n"
        "    </section>"
    )


def comic_fallback(comic: dict[str, object], site_url: str, base_path: str) -> str:
    return (
        "    <section class=\"noscript-seo\" aria-label=\"Comic summary\">\n"
        f"      <h1>{escape(comic['title'])}</h1>\n"
        f"      <p>{escape(comic['description'])}</p>\n"
        f"      <p>Published as a Dream Comic for {escape(comic['date'])}.</p>\n"
        f"      <p><a href=\"{base_path}{escape(comic['pdf'])}\">Download {escape(comic['title'])} as a PDF</a></p>\n"
        f"      <img src=\"{base_path}{escape(comic['cover'])}\" alt=\"{escape(comic['title'])} cover\">\n"
        f"      <p><a href=\"{escape(canonical_url(site_url, '/'))}\">Browse all Dream Comics</a></p>\n"
        "    </section>"
    )


def simple_fallback(title: str, description: str, href: str, label: str) -> str:
    return (
        "    <section class=\"noscript-seo\">\n"
        f"      <h1>{escape(title)}</h1>\n"
        f"      <p>{escape(description)}</p>\n"
        f"      <p><a href=\"{escape(href)}\">{escape(label)}</a></p>\n"
        "    </section>"
    )


def sitemap_xml(urls: list[dict[str, str]]) -> str:
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">',
    ]
    for entry in urls:
        lines.extend([
            "  <url>",
            f"    <loc>{escape(entry['loc'])}</loc>",
            f"    <lastmod>{escape(entry['lastmod'])}</lastmod>",
            "    <image:image>",
            f"      <image:loc>{escape(entry['image'])}</image:loc>",
            f"      <image:title>{escape(entry['image_title'])}</image:title>",
            "    </image:image>",
            "  </url>",
        ])
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def rss_xml(comics: list[dict[str, object]], site_url: str) -> str:
    feed_url = canonical_url(site_url, "rss.xml")
    latest_date = str(comics[-1]["date"])
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">',
        "  <channel>",
        "    <title>Dream Comics</title>",
        f"    <link>{escape(canonical_url(site_url, '/'))}</link>",
        "    <description>New Dream Comics releases adapted from actual dream journal entries.</description>",
        "    <language>en-us</language>",
        f"    <lastBuildDate>{escape(rss_pub_date(latest_date))}</lastBuildDate>",
        f"    <atom:link href=\"{escape(feed_url)}\" rel=\"self\" type=\"application/rss+xml\" />",
    ]
    for comic in reversed(comics):
        comic_url = canonical_url(site_url, f"comics/{comic['slug']}/")
        lines.extend([
            "    <item>",
            f"      <title>{escape(comic['title'])}</title>",
            f"      <link>{escape(comic_url)}</link>",
            f"      <guid isPermaLink=\"true\">{escape(comic_url)}</guid>",
            f"      <pubDate>{escape(rss_pub_date(str(comic['date'])))}</pubDate>",
            f"      <description>{escape(comic['description'])}</description>",
            f"      <category>Dream Comics</category>",
            "    </item>",
        ])
    lines.extend([
        "  </channel>",
        "</rss>",
    ])
    return "\n".join(lines) + "\n"


def rss_pub_date(value: str) -> str:
    published_date = date.fromisoformat(value)
    published = datetime.combine(published_date, time(12, 0), tzinfo=timezone.utc)
    return format_datetime(published, usegmt=True)


def comic_description(directory: Path, title: str, date: str) -> str:
    treatment = directory / "source" / "treatment.md"
    if treatment.exists():
        match = LOG_LINE_RE.search(treatment.read_text(encoding="utf-8"))
        if match:
            return trim_description(normalize_space(match.group(1)))
    return f"Read {title}, a Dream Comics lucid dream comic adapted from the {date} dream journal entry."


def trim_description(value: str, limit: int = 320) -> str:
    if len(value) <= limit:
        return value
    return value[:limit].rsplit(" ", 1)[0].rstrip(".,;:") + "."


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def canonical_url(site_url: str, path: str) -> str:
    if path in {"", "/"}:
        return f"{site_url}/"
    return f"{site_url}/{path.lstrip('/')}"


def public_base_path(site_url: str) -> str:
    path = urlparse(site_url).path.strip("/")
    return f"/{path}/" if path else "/"


def indent(value: str, spaces: int) -> str:
    prefix = " " * spaces
    return "\n".join(f"{prefix}{line}" if line else line for line in value.splitlines())


def title_from_slug(slug: str) -> str:
    return " ".join(part.capitalize() for part in slug.split("-"))


def escape(value: object) -> str:
    return str(value).replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")


if __name__ == "__main__":
    main()
