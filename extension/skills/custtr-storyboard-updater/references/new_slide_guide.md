# New Slide Guide

## Authoring New Slides

New slide creation is LLM-led. The skill no longer routes additions through fixed layout factories or a hard-coded set of slide layouts. The agent is responsible for studying the actual deck, choosing the best construction method for the teaching goal, creating the slide, and verifying the result without opening the final merged deck.

The goal is not to produce a generic slide that happens to contain the right words. The goal is to extend the storyboard so the new slide feels like it belongs in the same training deck.

## Non-Negotiable Principles

1. **Study before designing.** Inspect the neighboring slides, section structure, authoring labels, color palette, typography, diagrams, speaker notes, and summary flow before deciding what the new slide should look like.
2. **Match the deck, not a template.** Reuse existing deck visual patterns where practical: title treatment, body grid, diagram style, callout style, source/footer placement, authoring markers, and slide-number conventions.
3. **Let the concept choose the layout.** The LLM may create an architecture diagram, comparison table, annotated screenshot, visual sequence, cards, duplicated-and-edited existing slide, or any other suitable PowerPoint construction. Do not force content into a predeclared layout enum.
4. **Keep slides editable when practical.** Prefer native PowerPoint text, shapes, connectors, and tables for technical diagrams and training content. Use images only when they are source figures or when an image is clearly the right teaching surface.
5. **Speaker notes are required.** New technical slides need full narration that orients the learner, walks the visual, connects it to adjacent slides, and transitions forward.
6. **Visible content and notes must agree.** Speaker notes may elaborate, but the new concept must also appear on the slide itself through text, labels, a diagram, or a table.
7. **Final merged-output validation is XML/package-only.** Do not open the final merged deck for rendered QA. Validate the output package by inspecting ZIP/OOXML structure, slide XML, notes XML, relationships, content types, text presence, shape geometry, and merge sidecars.

## Planning Contract

An `add_new_slide` action describes intent, not implementation schema. It must include:

```json
{
  "type": "add_new_slide",
  "insert_after_slide": 17,
  "title": "CPM6 PCIe 6.1 and CXL 3.1 Architecture",
  "source_basis": [{"source_id": "SRC-VDOC-01"}],
  "finding_ids": ["NS-01"],
  "learning_goal": "Explain the CPM6 host-interface path and how it differs from CPM5.",
  "why_this_slide_exists": "The existing CPM5 slide cannot teach CPM6 at comparable depth.",
  "what_customer_should_understand": "CPM6 adds the Gen 2 PCIe/CXL path and changes the design conversation.",
  "visible_content_summary": "Architecture visual showing host lanes, GTM2, CPM6 controllers, CXL/DMA/Bridge, and NoC connection.",
    "visual_approach": "Reuse the nearest CPM architecture-slide visual language, matching title, diagram density, colors, and source/footer treatment; verify final output through XML/package inspection.",
  "qa_expectations": [
    "No text cutoffs or overlaps after rendering.",
    "Slide visually matches the surrounding CPM sequence.",
    "Source/scope note is visible but does not collide with content."
  ],
  "speaker_notes": "Full instructor narration..."
}
```

Do not add rigid renderer fields unless they are natural notes for the LLM's chosen implementation. Validators do not require them, and the skill must not route behavior based on them.

## Visual Flow Checklist

Before creating the slide, answer these briefly in the plan or working notes:

- Which existing slide or slide family should this new slide visually follow?
- What should the learner see that makes the concept easier to understand?
- What on-screen text must exist so the notes are not the only teaching surface?
- Where should source/scope information appear without crowding the content?
- Which knowledge check, summary, or objective changes are required because this slide exists?

## Construction Options

The LLM may use any suitable PowerPoint construction method available in the environment, including duplicating a nearby slide and editing it, manipulating OOXML, using `python-pptx`, using an approved PPTX MCP tool, or combining these methods. The method is chosen per deck and per concept.

If an external presentation tool is considered, the agent must justify why it best preserves the deck's visual flow and still deliver a PowerPoint deck that passes XML/package validation.

## Quality Bar

A new technical slide is acceptable only when:

- It teaches a concept at a depth comparable to peer slides in the deck.
- It uses the deck's own palette, fonts, and visual density.
- It contains visible teaching content, not just speaker notes.
- It includes full speaker notes in the deck's narration style.
- It carries source/scope attribution in a way consistent with the deck.
- Its final merged output survives XML/package validation, including expected text, notes, shape geometry, slide order, relationships, authoring markers, and package structure.
- It does not break downstream deck structure: authoring labels, slide order, knowledge checks, summaries, disclaimer, and final logo slide.

## Narrative Notes

Speaker notes are the instructor's script. For new technical slides, write 150-300 words unless the deck's local style clearly uses a different length.

Good narration:

1. Opens with the substantive concept, not with meta phrases such as "This slide...".
2. Walks the visual in the order a learner sees it.
3. Explains why the concept matters and how it relates to previous content.
4. Calls out caveats, scope, or generation boundaries.
5. Transitions to the next slide.

Title slides, objective slides, summary slides, disclaimer slides, and final logo slides usually do not need generated notes unless the existing deck pattern requires them.

## XML Package QA Loop

After producing additions and after merging into the final deck:

1. Extract text to confirm expected title, visible content, and notes are present.
2. Inspect `ppt/slides/*.xml` and `ppt/notesSlides/*.xml` for expected text runs, notes, authoring markers, highlight placement, shape coordinates, and relationship references.
3. Inspect `[Content_Types].xml`, presentation relationships, slide order, and merge sidecars to confirm the package is internally coherent.
4. Fix any XML/package issue and re-check the affected slide or package part.
5. Do not claim completion until the final merged deck has passed XML/package validation. Do not open the final merged deck in PowerPoint, LibreOffice, COM automation, browser UI, or any presentation viewer for validation because the output may require PowerPoint repair.
