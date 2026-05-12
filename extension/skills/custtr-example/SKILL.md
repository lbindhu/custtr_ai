# custtr-example
This is an example Custtr AI skill. Use it as a template when creating new skills.

## What This Skill Does
Demonstrates the structure of a Custtr AI skill. When invoked, it shows how to:
- Structure a skill prompt
- Provide clear instructions to Claude
- Include relevant context and examples

## When to Use
Invoke this skill by typing `/custtr-example` in the Claude Code chat when you want to see an example of a well-structured skill.

## Instructions
You are helping the user understand how to create a Custtr AI skill.
A skill is a markdown file (`SKILL.md`) inside a folder that starts with `custtr-`. The folder lives under:
- `extension/skills/` — for team-wide skills bundled in the extension
- `~/.claude/skills/` — for personal skills on your machine

### Skill folder structure
```
custtr-my-skill/
  SKILL.md      ← the skill prompt (this file)
  version.txt   ← contains the version number, e.g. "1.0"
  dependencies/  ← any additional files needed by the skill
```

### Tips for writing a good skill
1. Start with a one-line summary of what the skill does.
2. List the exact conditions when someone should invoke it.
3. Write the Claude instructions in plain language — no jargon.
4. Include an example input and expected output if helpful.
5. Keep it short — Claude reads the whole file every time.

## Example
**User invokes:** `/custtr-example`
**Claude responds:** Explains skill structure, shows folder layout, and offers to scaffold a new skill for the user.
