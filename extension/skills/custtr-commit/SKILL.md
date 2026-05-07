# custtr-commit

Writes a clean git commit message from a short description of your changes.

## When to Use

Invoke `/custtr-commit` when you're not sure how to word a commit message or want it to follow conventional commit format.

## Instructions

Ask the user: "What did you change?" — one sentence is enough.

Then output a commit message in this format:

```
<type>: <short summary in present tense, max 72 chars>
```

Where `<type>` is one of:
- `feat` — new feature
- `fix` — bug fix
- `chore` — maintenance, deps, config
- `refactor` — code change with no behavior change
- `docs` — documentation only
- `test` — adding or updating tests
- `style` — formatting, whitespace

Rules:
- Summary must be lowercase, no period at the end
- Use imperative mood ("add", "fix", "remove" — not "added" or "fixes")
- Output only the commit message, nothing else

## Example

**User says:** I fixed the button that wasn't opening the PR page

**Claude outputs:**
```
fix: open PR page when contribute button is clicked
```
