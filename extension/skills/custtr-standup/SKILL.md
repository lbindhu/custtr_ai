# custtr-standup

Formats a daily standup update from rough bullet points into a clean, concise message ready to paste into Slack or Teams.

## When to Use

Invoke `/custtr-standup` when you want to quickly write your daily standup without agonizing over wording.

## Instructions

Ask the user three questions (can be answered together or separately):

1. **Yesterday** — What did you work on?
2. **Today** — What are you planning to work on?
3. **Blockers** — Anything blocking you? (say "none" if not)

Once you have the answers, format the standup as:

```
*Yesterday:* <concise summary>
*Today:* <concise summary>
*Blockers:* <blockers or "None">
```

Rules:
- Keep each line to 1–2 sentences max
- Use plain language — no jargon unless the user used it
- Do not add commentary or explanation, just output the formatted standup
- If the user gives very brief input, flesh it out slightly but stay accurate

## Example

**User says:** yesterday finished the login bug fix and reviewed two PRs, today working on the dashboard chart component, no blockers

**Claude outputs:**
```
*Yesterday:* Fixed the login bug and reviewed 2 PRs.
*Today:* Working on the dashboard chart component.
*Blockers:* None
```
