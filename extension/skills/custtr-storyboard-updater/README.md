# custtr-storyboard-updater — Usage Guide

This skill updates AMD customer-training storyboard decks (`.pptx`) in a controlled, source-backed, repair-resistant way. It works across any AMD technology domain — PCIe, memory, processing system, security, clocking, AI Engine, NoC, and more. It does not just swap keywords: it first learns what the deck is teaching, then updates every dependent part of the learning story (objectives, body slides, diagrams, knowledge checks, summary, and speaker notes).

This README is for people invoking the skill. It focuses on writing good prompts. For how the skill works internally, see [`SKILL.md`](SKILL.md) and [`ARCHITECTURE.md`](ARCHITECTURE.md).

## Before you start

- Have the deck path ready (e.g. `C:\WORK\SB_Update\sources\MyModule.pptx`).
- Know your target version or generation (e.g. `2026.1`, or "Gen 2 Versal").
- Environment: `python3` with `python-pptx` installed.
- The skill runs in Cursor **Plan mode** first and asks you to approve an update plan before any deck is modified. Expect a checkpoint — review it.

## Pattern 1 — Basic update

Use this when you want the skill to find its own sources and do the full update. Just point it at the deck and state the target.

```
Use the custtr-storyboard-updater skill to update <deck path> to <target version/generation>.
```

Good examples:

```
Use the custtr-storyboard-updater skill to update
C:\WORK\SB_Update\sources\Versal_PCIe_Module.pptx to 2026.1.
```

```
Use the storyboard updater to refresh the Versal Memory Controller training deck
to the Gen 2 generation. Deck: C:\decks\Versal_DDR_Module.pptx.
```

```
Update the AI Engine intro storyboard at .\AIE_Intro.pptx to the 2026.1 release.
```

Tips for better results:

- Name the deck path and the module/topic explicitly.
- State the target version or generation clearly — this drives the staleness audit and the title/version marker.
- You do not need to list sources. The skill gathers its own from NABU, Confluence, JIRA, web, and Vivado docs based on what each slide claims.

## Pattern 2 — Source-augmented update

Use this when you have sources you want the skill to weigh heavily — a Confluence page, a datasheet PDF, a JIRA epic, release notes, or a local file. This usually improves accuracy and depth.

The important thing is how you frame the sources. Supplied sources are **priority hints and high-confidence references — not the full scope of the update.** The skill must still audit every slide and gather its own additional sources. If you imply "only update what these sources mention," you will get a shallow, incomplete deck.

Recommended template:

```
Use the custtr-storyboard-updater skill to update <deck path> to <target version/generation>.

Here are sources I consider important:
- <link or file 1>
- <link or file 2>

Treat these as priority inputs and high-confidence references, but do NOT limit the
update to only these topics. Still audit every slide, trace changes across the whole
deck, and gather additional sources wherever they are needed.
```

Good examples:

```
Update C:\decks\Versal_Security_Module.pptx to 2026.1.
Important sources (treat as priority, not the only scope):
- https://confluence.../versal-security-2026
- C:\refs\AMS_security_appnote.pdf
Still audit every slide and pull any other sources you need.
```

```
Use the storyboard updater on .\CPM_PCIe_Module.pptx, target Gen 2.
Please give extra weight to this JIRA epic and datasheet, but keep the full-deck audit:
- JIRA: PCIE-1234
- C:\refs\cpm6_datasheet.pdf
These are hints to prioritize, not a checklist that defines the whole update.
```

How your sources are used: they feed the skill's source inventory and quoted-reference set, then flow through the same evidence gates as auto-discovered sources (every finding and every cleared slide must cite a source). Your sources get priority, but they are added to — not substituted for — the skill's own research.

## What to avoid

- Don't say "only change the slides that mention X" — this defeats the full-deck audit and produces gaps.
- Don't expect keyword-only find-and-replace. The skill updates dependent slides, diagrams, knowledge checks, and the summary too.
- Don't omit the target version/generation — it anchors the staleness and version checks.
- Don't paste a single source and imply it is the complete scope. Frame it as a priority hint (see Pattern 2).

## What a good result looks like

- Every slide is audited on two axes (topic changes + staleness), with source-cited findings.
- The title/version marker matches your target version exactly.
- Knowledge checks and the summary slide reflect the full updated scope.
- Updated text on existing slides is review-marked; new slides match the deck's visual style.
- Speaker notes are narrator-ready on new and changed content.
- Authoring markers (`Fully Shared Slide`, `Slide-*`, etc.) and the trailing AMD logo slide are preserved.
