# CUSTTR AI

CUSTTR AI is a Visual Studio Code extension that distributes shared Claude Code skills to the CourseDev team. It adds a sidebar panel where you can browse, open, and contribute skills.

---

## Features

- A curated set of team skills bundled in the extension
- A **Contribute via PR** button to share your personal skills with the team
- Automatic update notifications

---

## Installing the Extension

1. Go to the [Releases](https://github.com/lbindhu/custtr_ai/releases) page
2. Download the latest `.vsix` file
3. Open VS Code and press `Ctrl+Shift+P`
4. Type `Extensions: Install from VSIX` and select it
5. Browse to the downloaded `.vsix` file and click **Install**
6. Reload VS Code by selecting **Developer: Reload Window** from the Command Palette

After reloading, the **CUSTTR AI** icon will appear in the Activity Bar on the left. Click it to open the sidebar.

The sidebar has two sections:

| Section | Description |
|---|---|
| **CUSTTR SKILLS** | Approved team skills bundled with the extension |
| **USER SKILLS** | Personal skills in your `.claude/skills/` folder prefixed with `custtr-` |

Click any skill name to open its `SKILL.md` file and read what it does.

---

## Using Skills

In any Claude Code chat, type the skill name with a forward slash:

```
/custtr-standup
```

Claude loads the skill instructions and guides you interactively through the task.

---

## Contributing a Skill

If you have a personal skill that the whole team would benefit from, you can contribute it via a Pull Request.

### Fork the Repository

1. Go to [github.com/dashboard](https://github.com/dashboard)
2. Search for `lbindhu/custtr-ai` in the search bar at the top right
3. Select the **custtr-ai** repository
4. Click **Fork** in the top right
5. Leave the default settings on the **Create a new fork** page and click **Create fork** — it will take a few seconds

### Submit Your Skill

6. In the **USER SKILLS** section, hover over the skill you want to contribute — a branch icon (**Contribute via PR**) appears on the right
7. Click the branch icon — a confirmation popup asks whether you want to open GitHub to contribute the skill
8. Click **Open in GitHub** — your browser opens a new file editor in the repository
9. Paste or type your `SKILL.md` content into the editor

> **Note:** It is recommended to also create a `version.txt` file in the same skill folder to track the skill version.

10. Add any dependency files if needed in the correct path
11. Click **Commit changes** in the top right
12. Write a commit message and an optional extended description, then select **Propose changes**
13. On the **Comparing changes** page, click **Create pull request**
14. Add a suitable title and description, then click **Create pull request** — your PR will be reviewed and merged by the team

---

## Automatic Updates

The extension checks for updates every time VS Code starts. You can also trigger a manual check using either of these methods:

- **Method 1:** Click the CUSTTR AI icon in the bottom-right corner of VS Code
- **Method 2:** Press `Ctrl+Shift+P`, type `Extensions: Check for Extension Updates`, and press Enter

When an update is available:

1. A notification appears in the bottom-right corner
2. Click **Install** to download and install the new version
3. Click **Reload Now** — VS Code reloads with the updated version active

### Checking Your Version

Your installed version and the latest available version are always visible in the sidebar.
