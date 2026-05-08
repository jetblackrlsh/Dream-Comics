import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont


PAGE_W, PAGE_H = 1600, 2000
BG = (8, 8, 14)
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


def get_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    name = "arialbd.ttf" if bold else "arial.ttf"
    path = Path("C:/Windows/Fonts") / name
    if path.exists():
        return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default(size=size)


LABEL_FONT = get_font(32, bold=True)
SMALL_FONT = get_font(22)


def fit_page(img: Image.Image, mode: str) -> Image.Image:
    src = img.convert("RGB")
    if mode == "stretch":
        return src.resize((PAGE_W, PAGE_H), Image.Resampling.LANCZOS)

    if mode == "blur-fill":
        bg = fit_page(src, "crop").filter(ImageFilter.GaussianBlur(24))
        bg = ImageEnhance.Brightness(bg).enhance(0.45)
        ratio = min(PAGE_W / src.width, PAGE_H / src.height)
        fg = src.resize((round(src.width * ratio), round(src.height * ratio)), Image.Resampling.LANCZOS)
        left = (PAGE_W - fg.width) // 2
        top = (PAGE_H - fg.height) // 2
        bg.paste(fg, (left, top))
        return bg

    ratio_func = max if mode == "crop" else min
    ratio = ratio_func(PAGE_W / src.width, PAGE_H / src.height)
    resized = src.resize((round(src.width * ratio), round(src.height * ratio)), Image.Resampling.LANCZOS)

    if mode == "crop":
        left = max(0, (resized.width - PAGE_W) // 2)
        top = max(0, (resized.height - PAGE_H) // 2)
        return resized.crop((left, top, left + PAGE_W, top + PAGE_H))

    page = Image.new("RGB", (PAGE_W, PAGE_H), BG)
    left = (PAGE_W - resized.width) // 2
    top = (PAGE_H - resized.height) // 2
    page.paste(resized, (left, top))
    return page


def aspect_ratio_delta(path: Path, img: Image.Image) -> dict:
    expected = PAGE_W / PAGE_H
    actual = img.width / img.height
    return {
        "file": str(path),
        "width": img.width,
        "height": img.height,
        "aspect_ratio": round(actual, 5),
        "target_aspect_ratio": round(expected, 5),
        "delta": round(abs(actual - expected), 5),
    }


def make_contact_sheet(pages: list[Image.Image], names: list[str]) -> Image.Image:
    thumb_w, thumb_h = 240, 300
    cols = 4
    rows = (len(pages) + cols - 1) // cols
    pad = 34
    label_h = 62
    sheet = Image.new("RGB", (cols * (thumb_w + pad) + pad, rows * (thumb_h + label_h + pad) + pad), BG)
    draw = ImageDraw.Draw(sheet)

    for idx, (page, name) in enumerate(zip(pages, names), start=1):
        col = (idx - 1) % cols
        row = (idx - 1) // cols
        x = pad + col * (thumb_w + pad)
        y = pad + row * (thumb_h + label_h + pad)
        thumb = page.resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        sheet.paste(thumb, (x, y))
        draw.rectangle((x, y, x + thumb_w, y + thumb_h), outline=(244, 240, 255), width=3)
        draw.text((x, y + thumb_h + 10), f"Page {idx}", font=LABEL_FONT, fill=(255, 255, 255))
        draw.text((x, y + thumb_h + 42), name[:24], font=SMALL_FONT, fill=(198, 198, 215))

    return sheet


def main() -> None:
    parser = argparse.ArgumentParser(description="Assemble full-page comic images into a 4:5 portrait PDF.")
    parser.add_argument("--pages-dir", required=True, help="Directory containing cover and story page images.")
    parser.add_argument("--out", required=True, help="Output PDF path.")
    parser.add_argument("--preview-dir", default="tmp/comic-book-pdf", help="Directory for preview images and manifest.")
    parser.add_argument("--fit", choices=["blur-fill", "contain", "crop", "stretch"], default="blur-fill", help="How to normalize non-4:5 images.")
    parser.add_argument("--max-pages", type=int, default=8)
    args = parser.parse_args()

    pages_dir = Path(args.pages_dir)
    if not pages_dir.exists():
        raise SystemExit(f"Pages directory does not exist: {pages_dir}")

    page_paths = sorted(p for p in pages_dir.iterdir() if p.suffix.lower() in IMAGE_SUFFIXES)
    if not page_paths:
        raise SystemExit(f"No page images found in {pages_dir}")
    if len(page_paths) > args.max_pages:
        raise SystemExit(f"Found {len(page_paths)} images, but max-pages is {args.max_pages}")

    out_path = Path(args.out)
    preview_dir = Path(args.preview_dir)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    preview_dir.mkdir(parents=True, exist_ok=True)

    for old_preview in preview_dir.glob("preview-page-*.png"):
        old_preview.unlink()

    raw_pages = [Image.open(path) for path in page_paths]
    manifest = {
        "page_count": len(page_paths),
        "target_size": [PAGE_W, PAGE_H],
        "fit": args.fit,
        "source_pages": [aspect_ratio_delta(path, img) for path, img in zip(page_paths, raw_pages)],
    }
    normalized_pages = [fit_page(img, args.fit) for img in raw_pages]

    normalized_pages[0].save(out_path, "PDF", resolution=150, save_all=True, append_images=normalized_pages[1:])

    for idx, page in enumerate(normalized_pages, start=1):
        page.save(preview_dir / f"preview-page-{idx:02}.png")
    make_contact_sheet(normalized_pages, [p.name for p in page_paths]).save(preview_dir / "contact-sheet.png")
    (preview_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(out_path.resolve())


if __name__ == "__main__":
    main()
