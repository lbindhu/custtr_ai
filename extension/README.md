# CoursDev AI

A VS Code extension that brings the CoursDev team's Claude Code skills directly into the sidebar — just like the PSAS AI sidebar. Install it once and all shared skills are available immediately.

## Features

- **CoursDev Skills** — team skills bundled in the extension, deployed to every team member's machine
- **User Skills** — skills you created locally (`~/.claude/skills/custtr-*`) not yet contributed to the team
- **⎇ Contribute button** — opens a GitHub pull request page so you can share a skill with the team
- **Auto-update notifications** — the extension checks for new versions on startup

## Installing the Extension

1. Go to the [Releases](../../releases) page of this repository
2. Download the latest `.vsix` file
3. Open VS Code and press `Ctrl+Shift+P`
4. Type `Extensions: Install from VSIX` and select it
5. Browse to the downloaded `.vsix` file
6. **Fully quit and relaunch VS Code** (a window reload is not enough)

The CoursDev AI icon will appear in the left sidebar.

## First-Time Setup

After installing, set your GitHub token so the PR contribution button works:

1. Press `Ctrl+Shift+P`
2. Type `CoursDev AI: Set GitHub Token`
3. Paste your GitHub Enterprise personal access token (needs `repo` and `workflow` scopes)

Generate a token at: https://gitenterprise.xilinx.com/settings/tokens

## Adding a Skill

See [CONTRIBUTING.md](CONTRIBUTING.md) for step-by-step instructions.

Quick summary:
1. Create `extension/skills/custtr-your-skill/` with `SKILL.md` and `version.txt`
2. Test with F5
3. Push to a branch and click the ⎇ button to open a PR

## Configuration

| Setting | Default | Description |
|---|---|---|
| `coursedev-ai.repoUrl` | _(your repo URL)_ | GitHub Enterprise repo URL |
| `coursedev-ai.releasesUrl` | _(your releases URL)_ | URL of `releases/latest.json` for update checks |
| `coursedev-ai.checkUpdatesOnStartup` | `true` | Auto-check for updates when VS Code starts |

## Building from Source

```bash
cd extension
npm install
npm run compile
# Press F5 in VS Code to test
```

## Publishing a Release

```bash
git add .
git commit -m "Release v1.0.1"
git push origin main
git tag v1.0.1
git push origin v1.0.1
```

CI will automatically build the VSIX and attach it to the GitHub Release.
