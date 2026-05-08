---
name: comic-book-pdf
description: "Create complete comic-book PDFs from a user story, story idea, premise, outline, scene, or character concept. Use when the user wants a proper comic book rather than storybook panels: up to 8 generated full comic pages total, cover plus as many as 7 story pages, 4:5 portrait pages, minimal dialogue, heavy narration, no speech bubbles or thought bubbles, narration and speech inside caption boxes, consistent character designs, coherent visual continuity, satisfying complete story arc, and bright high-saturation detailed anime comic art."
---

# Comic Book PDF

## Overview

Use this skill to turn a story idea into a finished comic-book package: treatment, character bible, page-by-page script, generated full-page comic images, assembled PDF, and previews.

This skill differs from one-panel storybook comic skills: each generated image must be a complete 4:5 portrait comic page, including its own panel layout and caption boxes. All readable story text must be generated inside the page art by the image model. Never generate blank caption boxes, blank pages, or art-only panels and then add narration, speech, labels, or titles afterward with PDF assembly, image editing, canvas drawing, HTML/CSS, or another typesetting step.

## Output Contract

- Generate up to 8 images total: page 1 is the cover, pages 2-8 are story pages.
- Use 4:5 portrait aspect ratio for every generated image.
- Make each image a complete comic-book page with multiple panels or one splash panel as appropriate.
- Use caption boxes only for narration and rare short speech.
- The caption-box text belongs inside the generated image itself. Do not generate art and text as separate assets or layers.
- Do not use speech bubbles, thought bubbles, floating dialogue, subtitles, watermarks, logos, or unreadable decorative text.
- Keep dialogue minimal. Prefer narration that advances the story.
- Keep the story complete and satisfying within the chosen page count.
- Use consistent character designs, outfits, props, color accents, and silhouettes across pages.
- Default art style: colorful, high color saturation, bright glow, high detail saturation, dynamic anime art style, crisp comic linework.

## Workflow

1. Ground the story.
   - Use the story or idea from chat as the source.
   - If the idea is vague, make one reasonable interpretation and state it before generating.
   - Choose 4-8 pages based on scope; default to 8 for a full short comic unless the user asks for quick output.

2. Build the treatment.
   - Write a logline, central conflict, theme, ending, and emotional arc.
   - Define a tight cast. Prefer 1 protagonist, 1 supporting character, and 1 obstacle or antagonist.
   - Make the ending visual: the final page should show the consequence of the protagonist's choice.

3. Create a character bible.
   - Record each recurring character's exact visible identifiers: age range, face shape, hair, eyes, outfit, color palette, signature prop, posture, and expression range.
   - Repeat these identifiers in every image prompt.
   - Do not redesign characters between pages. Change pose, lighting, damage, and expression only when story events require it.

4. Script the comic pages.
   - Read `references/page_prompting.md` when writing prompts.
   - Include cover text guidance only if the user wants visible title text; otherwise keep cover text minimal or omitted to avoid generated text artifacts.
   - For each story page, specify panel layout, visual beats, caption-box text, character continuity notes, lighting, and ending hook.
   - Keep caption text short enough to plausibly fit inside generated caption boxes.
   - Treat the caption-box text as part of the image prompt, not as later overlay copy.

5. Generate full-page images.
   - Use the built-in `image_gen` tool.
   - Generate one page at a time.
   - Prompt for "full comic book page, 4:5 portrait aspect ratio" every time.
   - Repeat "caption boxes only, no speech bubbles, no thought bubbles" every time.
   - Repeat that all caption-box text, title text, and any other readable story text must be generated directly in the page art, with no blank text boxes to fill later.
   - Save generated images into the project, usually `assets/comic-pages/page-01-cover.png`, `page-02.png`, etc.

6. Assemble the PDF.
   - Use `scripts/assemble_comic_book_pdf.py` from this skill unless the project already has a better full-page PDF builder.
   - Do not add external captions, title overlays, dialogue overlays, borders, or page chrome. The generated images are the comic pages.
   - Save the PDF under `output/pdf/` and previews under `tmp/comic-book-pdf/`.

7. Verify the result.
   - Inspect the contact sheet and at least the cover, first story page, middle story page, and final page.
   - Check for correct page count, 4:5 portrait pages, caption boxes instead of bubbles, text not dominating the art, no obvious character redesigns, and a complete narrative.
   - If a page fails core requirements, regenerate that page before assembling the final PDF.

## Suggested Layout

Use this project layout unless the current repo already has conventions:

```text
source/
  story-idea.txt
  treatment.md
  page-script.md
assets/
  comic-pages/
    page-01-cover.png
    page-02.png
output/
  pdf/
    comic-book.pdf
tmp/
  comic-book-pdf/
    preview-page-01.png
    contact-sheet.png
    manifest.json
```

## PDF Assembly

Run from the target project root:

```powershell
python C:/Users/jetbl/.codex/skills/comic-book-pdf/scripts/assemble_comic_book_pdf.py `
  --pages-dir "assets/comic-pages" `
  --out "output/pdf/comic-book.pdf" `
  --preview-dir "tmp/comic-book-pdf"
```

The script requires Pillow. It sorts images by filename, accepts 1-8 pages, normalizes them to 1600x2000 pixels, writes a PDF, preview PNGs, a contact sheet, and a manifest. Its default `blur-fill` mode preserves the full generated page while filling any side margins with a blurred, darkened extension of the art.

## Quality Bar

- The PDF must read as a comic book when opened by itself.
- The cover must clearly signal the story's identity and genre.
- Page turns must have a coherent visual sequence.
- The final page must resolve the central conflict emotionally and visually.
- Generated pages should look intentional as comic pages, not single illustrations with loose captions.
