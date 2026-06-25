---
name: OOXML highlight and tracked-change marking
type: reference
---

# OOXML Highlight and Tracked Changes

Use this reference only for **existing-slide edits**. Do not apply this edit-marking to newly generated slides.

## New Slides

New slides must not have yellow-highlighted body text. Add a badge or callout
only if it fits the deck's authoring style and does not crowd the title,
classification text, or slide number.

## Yellow Highlight Position

In DrawingML, `<a:highlight>` must be placed inside `<a:rPr>` after `<a:effectLst/>` and before `<a:uLnTx/>`.

Correct order:

```xml
<a:rPr ...>
  <a:ln>...</a:ln>
  <a:solidFill>...</a:solidFill>
  <a:effectLst/>
  <a:highlight><a:srgbClr val="FFFF00"/></a:highlight>
  <a:uLnTx/>
  <a:uFillTx/>
  <a:latin .../>
  <a:ea .../>
  <a:cs .../>
</a:rPr>
```

If `<a:rPr>` has no `<a:effectLst/>` or `<a:uLnTx/>`, place `<a:highlight>` immediately after the fill element, such as `</a:solidFill>`.

For self-closing `<a:rPr ... />`, expand it:

```xml
<a:rPr lang="en-US" dirty="0"><a:highlight><a:srgbClr val="FFFF00"/></a:highlight></a:rPr>
```

## Tracked Text Changes

For exact changed spans, split the original `<a:r>` into multiple runs:

- Deleted text: original run properties + `strike="sngStrike"` + yellow highlight + OLD text.
- Inserted text: original run properties + yellow highlight + NEW text.
- Unchanged text: original run properties with no highlight.

Preserve leading/trailing spaces with `xml:space="preserve"` on `<a:t>` when needed.

## Text Color on Highlighted Runs

Highlighted runs must be readable on yellow. **Always force dark text on every highlighted run**, regardless of the original fill:

- Remove any existing `<a:solidFill>` from the highlighted run’s `<a:rPr>`.
- Insert `<a:solidFill><a:schemeClr val="tx1"/></a:solidFill>` as the first child of `<a:rPr>`.

This rule applies unconditionally. Shapes that use white text (`srgbClr=FFFFFF`), light grey, or the `bg1` scheme token will all be invisible on yellow if the original fill is preserved. The correct approach is to always replace — not conditionally check — the fill on highlighted runs.

Do **not** change the fill on non-highlighted runs. Those runs must keep their original fill (white text stays white on unchanged runs of dark-background shapes).

## Validation

After marking changes:

- Ensure every intended changed run contains `<a:highlight><a:srgbClr val="FFFF00"/></a:highlight>`.
- Ensure every highlighted run has `<a:solidFill><a:schemeClr val="tx1"/></a:solidFill>` as the first fill element (no explicit white or `bg1` remains on highlighted runs).
- Ensure non-highlighted runs are untouched — their original fill is preserved.
- Ensure new slides have no highlighted body text; badges are optional and must match the deck style.

