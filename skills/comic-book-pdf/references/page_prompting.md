# Comic Book Page Prompting

Use this structure for each generated image.

```text
Use case: full comic book page
Asset type: <cover | story page n of total>, 4:5 portrait aspect ratio
Primary request: Create a complete anime comic book page, not a single panel.
Story role: <what this page must accomplish in the narrative>
Character bible for continuity: <stable details for every recurring character>
Page layout: <cover composition or panel grid, panel sizes, reading order>
Caption boxes: <short narration and rare short speech to generate directly inside rectangular caption boxes in the page art>
Visual beats: <panel-by-panel actions and emotions>
Setting and props: <recurring locations, objects, symbols>
Style: colorful high-saturation anime comic art, bright glow, high detail saturation, crisp linework, cinematic lighting, expressive faces, polished manga-comic page design.
Constraints: 4:5 portrait full page, caption boxes only, no speech bubbles, no thought bubbles, no floating dialogue, no subtitles, no watermark, no logo, no extra unreadable text. All readable story text must be generated directly inside the page art; do not leave blank caption boxes or art-only panels for later typesetting. Keep all recurring characters visually consistent with the character bible.
```

## Page Count Guidance

- 4 pages: cover, setup, crisis, resolution.
- 6 pages: cover, setup, first obstacle, reversal, choice, resolution.
- 8 pages: cover, setup, inciting incident, escalation, complication, low point, active choice, resolution.

Prefer 8 pages when the user asks for a complete comic and time allows. Use fewer pages for quick tests or compact premises.

## Caption Style

Use caption boxes as the only text vehicle. Narration can be poetic, but it must remain clear. The caption text is part of the generated image prompt, never a separate overlay step.

Good caption-box directions:

```text
Top caption box: "Mira reached the city at sunrise, carrying the last lantern."
Small lower caption box: "The gate opened only for someone willing to leave fear behind."
```

Avoid:

```text
Speech bubble saying...
Thought bubble saying...
Large paragraphs of tiny text...
```

## Continuity Checklist

Before each prompt, copy forward:

- Names and roles.
- Hair, eye, skin tone, face shape, outfit, and color accents.
- Signature item or visual motif.
- Current emotional state.
- Any story changes that should persist, such as a torn sleeve, glowing mark, or recovered object.

## Story Checklist

Each story page should have a clear job:

- Page 2 establishes protagonist, want, and world.
- Early pages show the obstacle and stakes.
- Middle pages escalate through consequence, not random spectacle.
- Penultimate page shows the protagonist making the decisive choice.
- Final page shows the result of that choice and gives emotional closure.
