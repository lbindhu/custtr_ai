# Snagit & Graphics Capture Best Practices
**Source:** `U:\BestPractices\Graphics\Best Practices - Graphics Capture.docx` (v2.0a – 07 JULY 2023, Bill Kafig)
**Source:** `U:\BestPractices\Graphics\Tips on Using Snagit and Best Practices in AuthorIT.pptx` (Omkar Vivek Bhat)

---

## File Format Standards

- **PNG is the required format** for all graphics imported into lab documents. Images not in PNG format must be converted.
- **Source files must be saved as .snagx** (updated from legacy .snag). If an existing .snag file is updated, save it as .snagx.
- All PNG and .snagx source files must be stored in the Graphics Repository (`T:\Graphics_Repository\`).

---

## File Naming Convention

- File names must be **meaningful and match the caption** used in the lab instructions exactly.
- The PNG filename, the .snagx source filename, and the caption in the lab document must all be identical.
- Example: if a graphic shows creating a new Vivado project, the name is `Creating a New Vivado Project.png` — and the lab caption reads "Creating a New Vivado Project".
- Counter-example of a BAD name: `zynq.bit` — gives no indication of purpose, board, or course.

---

## Screenshot Capture Rules

- **Show only the relevant portion** of the screen. Do not capture the full desktop or entire tool window if only a small part is relevant.
- **Use cut-outs** to show the continuation of a workspace when the full window cannot be shown.
- **Resize dialog boxes** to show only the relevant portion — this is preferred over using cut-outs where possible.
- **Blur version numbers** in all screenshots (e.g., blur "2023.1" in Vivado splash screens). This extends the life of the screenshot and reduces rework for the next tool version update. Blur setting: **Smooth, 25% intensity** — sufficient to make the text unreadable but still visible as a placeholder.
- **Use the light motif** in terminal windows to avoid having to invert or replace colors for screenshots.

---

## Annotation Standards (Snagit Shapes)

All shapes below are available as Snagit templates under `U:\BestPractices\Graphics\`.

### Pointing Arrow
- **Purpose:** Point to a specific UI element.
- **Color:** Primary Red — HEX `#ED1C24`
- **Width:** 8 pixels
- **Start cap:** Round
- **End cap:** Barbed arrow
- **Shadow:** None
- **Exception:** Size and color may vary if the arrow is not clearly visible over the background, or appears disproportionate.

### Flow Arrow
- **Purpose:** Indicate a flow from one location to another.
- **Color:** Primary Red — HEX `#ED1C24`
- **Width:** 5 pixels
- **Style:** Dot
- **Type:** Bezier Curve (appears straight initially; drag white circles to curve)
- **Start cap:** Round anchor
- **End cap:** Barbed arrow
- **Shadow:** None
- **Note:** Where there are back-and-forth flows, the round anchor can be changed to a barbed arrow. Width can be adjusted for very large graphics.

### Highlight / Callout Shape
- **Purpose:** Highlight a particular entry or region.
- **Outline color:** Primary Red — HEX `#ED1C24`
- **Fill:** Transparent
- **Line width:** 4 pixels
- **Shadow:** None
- **Rule:** Center the text or object within the highlight.

### Text Rectangle
- **Purpose:** Cover existing text in a field and provide a white background for replacement text.
- **Outline color:** AMD Teal — HEX `#007C97`
- **Fill:** White
- **Line width:** 4 pixels
- **Shadow:** None
- **Font:** Arial, black (use Primary Red `#ED1C24` only if black is not distinguishable from background)

### Numbered Circle Stamp
- **Purpose:** Illustrate numbered steps in a sequence.
- **Fill:** White
- **Outline:** Primary Red — same as preceding shapes
- **Font:** Arial; size varies depending on the graphic
- **Shadow:** None on center text
- **Pre-built stamps available at:** `U:\BestPractices\Graphics\Stamps\` (one.png through nine.png)
- **Rule:** Numbered stamps must overlay the text box, callout, or highlight to associate the number with the correct object.
- **Rule:** Use either number stamps OR arrows — NOT both. Both indicate order; only one is needed.

---

## Graphics in Combination

- Numbered stamps partially overlap the highlight oval. Stamps may be at any corner of the oval to best fit the graphic.
- Flow arrows: the "dot" on the tail sits on top of one edge of the source highlight oval. Select curve and placement for aesthetic and practical appeal.
- Numbering is not required where the sequence is obviously "first, then next".

---

## Directory Structure (Repository)

Two categories of graphics are stored separately:

| Type | Contents | Location |
|---|---|---|
| Tool/Technology Specific | Icons, menus, tool layouts, protocol headers — not specific to any lab | `T:\Graphics_Repository\Tool-Specific Graphics\` |
| Lab/Class Specific | Screenshots containing lab-specific information, code snippets | `T:\Graphics_Repository\F1\` through `F4\` and topic cluster folders |

---

## Snagit Template Location

```
U:\BestPractices\Graphics\SnagIT_Template.snagtheme
U:\BestPractices\Graphics\Stamps\  (one.png through nine.png)
```

Import the .snagtheme file into Snagit to access all pre-configured shapes.
