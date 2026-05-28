# ASCII Block-Diagram Guideline

> **AMD / PSAS storyboard-updater extensions**
>
> The `ascii_to_diagram.py` parser shipped with this skill is a tolerant
> superset of the strict syntax described below. Concretely:
>
> - **Unicode box-drawing glyphs** (`┌┐└┘├┤┬┴┼ ─ │ ═ ╌ ► ◄ ▼ ▲ → ← ↓ ↑`) are
>   normalized to ASCII (`+`, `-`, `|`, `=`, `.`, `>`, `<`, `v`, `^`) before
>   parsing. You can freely mix Unicode and ASCII box-drawing chars.
> - **Body-row column drift of ±2** is tolerated: arrows like `───►│` shift
>   downstream chars by one column and corner positions may drift between
>   the top and bottom rows of a box. The parser scans exhaustively and
>   accepts a ≥40% vertical-wall match for tolerant edge verification.
> - **AMD palette**: the renderer maps `# color=NAME` hints to AMD-branded
>   fills — `teal` (default), `gold`, `red`, `dark`. Containers default to
>   `dark`.
> - **Soft-fail policy**: malformed input is logged to stderr; the caller
>   falls back to a non-diagram layout instead of crashing.
> - **`[[ID]]` emphasis** is OPTIONAL. Boxes do not need explicit IDs; the
>   parser slugifies the first label line. Use `[[ID]]` only when you want
>   to bold-highlight a specific box.
>
> Everything below documents the strict baseline syntax — examples that
> follow it work everywhere, but you are free to use Unicode glyphs and
> AMD color hints in PSAS storyboard ASCII art.

---

A strict ASCII syntax for block diagrams. Following this guideline guarantees
that `ascii2pptx.py` produces the same shape set, geometry, and connectivity
every time.

## 1. File format

- Encoding: **UTF-8**.
- Line endings: **LF** (`\n`).
- Indentation: **spaces only**. Tabs are an error.
- One diagram per file.
- Trailing whitespace on a line is ignored.
- The grid coordinate of a character is `(col, row)` where `col` is its 0-based
  byte offset and `row` is its 0-based line index.
- A `#` at column 0 begins a comment line and is ignored entirely.

## 2. Boxes

Boxes are closed axis-aligned rectangles drawn with these glyphs:

| Glyph | Role             |
|-------|------------------|
| `+`   | corner           |
| `-`   | horizontal wall  |
| `|`   | vertical wall    |

Rules:

- Minimum size: **5 columns × 3 rows** (the smallest legal box).
- All four corners must be `+`. Top and bottom edges between corners must be
  all `-`. Left and right edges between corners must be all `|`.
- **Two boxes must not share any border cell** (no touching, no adjacency).
  They may be nested with at least one cell of padding inside the parent.

### Box content

Lines inside the walls form the box's content. The **first non-blank interior
line is the box identifier** used by arrow references. Subsequent non-blank
lines are display text rendered below the identifier.

```
+---------+
| db      |   <- identifier: "db", no body
+---------+

+----------------+
| api            |   <- identifier: "api"
| REST + auth    |   <- body line 1
| Python 3.12    |   <- body line 2
+----------------+
```

### Emphasis

Wrap the identifier in double brackets to mark a box as emphasized:

```
+----------+
| [[db]]   |
+----------+
```

Emphasized boxes render with a thicker border and an accent fill.
The stored identifier is `db` (brackets stripped).

## 3. Containers (groups)

A box whose interior fully contains another box's outer rectangle is the
**parent** of that box. Containment is detected geometrically — there is no
syntax for it. Nesting depth is unlimited; sibling boxes inside the same
container must not overlap.

```
+-------------------------+
| cluster                 |
|                         |
|   +-------+   +-------+ |
|   | api   |   | db    | |
|   +-------+   +-------+ |
|                         |
+-------------------------+
```

`cluster` is the parent of `api` and `db`.

Containers render behind their children with a lighter fill.

## 4. Arrows

Arrows connect two box-border cells. They are built from line glyphs and
arrowhead glyphs:

| Glyph    | Role                                |
|----------|-------------------------------------|
| `-`      | horizontal segment, **thin solid**  |
| `|`      | vertical segment, thin solid        |
| `=`      | horizontal segment, **bold solid**  |
| `.`      | horizontal segment, **dashed**      |
| `+`      | bend / junction (2–4 segments)      |
| `>` `<`  | arrowhead, horizontal               |
| `^` `v`  | arrowhead, vertical                 |

Rules:

- An arrow must terminate at a cell **immediately adjacent to a box border**
  on each end. Floating arrows are an error.
- An arrowhead may appear only at a terminal cell.
- A single arrow uses one style throughout: all `-` (thin), all `=` (bold),
  or all `.` (dashed). Mixing styles in one arrow is an error.
- A `+` bend must connect 2–4 line segments — no more, no less.
- **Bidirectional:** arrowheads on both ends, e.g. `<-->`, `<==>`, `<..>`.
- Vertical arrows always use `|` regardless of the horizontal style.
  Style is determined by the horizontal glyph; pure-vertical arrows are thin solid.

Examples:

```
+---+   +---+
| a |-->| b |       a -> b   thin solid
+---+   +---+

+---+   +---+
| a |==>| b |       a -> b   bold solid
+---+   +---+

+---+   +---+
| a |..>| b |       a -> b   dashed
+---+   +---+

+---+      +---+
| a | <--> | b |      bidirectional
+---+      +---+
```

## 5. Edge labels

Free text near an arrow path (within **2 cells** of any cell on that arrow,
and not part of any other shape) becomes the arrow's label.

```
+---+        +---+
| a |--ack-->| b |
+---+        +---+
```

Rules:

- One label maximum per arrow.
- A text run that is within 2 cells of two different arrows is **ambiguous**
  and is a parse error — move it closer to one arrow.
- Labels cannot contain box/arrow glyphs (`+ - | = . > < ^ v`).

## 6. Errors are loud

The script exits non-zero with a `line:col` location for every violation. No
silent fallbacks. The full error list:

| Condition                                  | Why it is an error |
|--------------------------------------------|--------------------|
| Tab character anywhere                     | Non-deterministic column layout |
| Box smaller than 5×3                       | Cannot hold a 1-char identifier |
| Box not closed (missing corner/edge cell)  | Ambiguous parse |
| Two boxes share any border cell            | Cannot tell them apart |
| Duplicate box identifier                   | Arrow references would be ambiguous |
| Arrow without two box endpoints            | Floating; no connection |
| Mixed-style arrow (`-` and `=` in one arrow) | Style would be ambiguous |
| `+` bend with <2 or >4 connected segments  | Topology unclear |
| Arrowhead not at a terminal cell           | Direction ambiguous |
| Edge label within range of multiple arrows | Owner ambiguous |

## 7. Not supported (intentional)

To keep output predictable, these are deliberately omitted:

- Diagonal lines.
- Curves.
- Per-shape colors beyond the emphasis flag.
- Free-floating text not attached to a box or arrow (such text triggers a
  warning and is ignored).
- Multiple diagrams in one file.

## 8. Minimal complete example

```
+--------+         +-----------+
| client |--req--->| [[server]]|
+--------+         +-----------+
                         |
                         v
                   +-----------+
                   | db        |
                   | Postgres  |
                   +-----------+
```

Three boxes. Two arrows. `server` is emphasized. Arrow `client -> server`
carries the label `req`. Arrow `server -> db` is unlabeled.
