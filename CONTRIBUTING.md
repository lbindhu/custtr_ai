# Contributing to CoursDev AI

Anyone on the team can contribute a new skill. No coding required.

## How to Add a Skill

### 1 — Create a branch

Open Git Bash in your `custtr_ai` folder and run:

```bash
git checkout -b add-my-skill
```

### 2 — Create the skill folder

Inside `extension/skills/`, create a folder whose name starts with `custtr-`:

```
extension/skills/custtr-my-skill/
```

### 3 — Add the two required files

**SKILL.md** — the prompt Claude Code will follow when the skill is invoked. Include:
- A one-line summary
- When to use the skill
- The instructions Claude should follow

**version.txt** — a single line with the version number, e.g. `1.0`

### 4 — Test locally

Press **F5** in VS Code to open the Extension Development Host. Your skill should appear under **CoursDev Skills** in the sidebar.

### 5 — Push and open a PR

```bash
git add .
git commit -m "Add custtr-my-skill"
git push origin add-my-skill
```

Then click the **⎇** button on your skill in the CoursDev AI sidebar — it opens a pull request page in the browser. Fill in the description and submit.

### 6 — After merge

The maintainer will bump the version in `extension/package.json`, tag the release, and CI will automatically build and publish the new VSIX. Team members will see an **Update available** notification in VS Code.

## Skill Naming Rules

- Folder name must start with `custtr-`
- Use lowercase letters and hyphens only (e.g. `custtr-course-review`)
- Keep names short and descriptive

## Questions?

Open an issue on the repo or ask in the team channel.
