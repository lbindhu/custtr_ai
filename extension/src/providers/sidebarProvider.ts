import * as vscode from 'vscode';
import * as https from 'https';
import * as http from 'http';
import { SkillManager, Skill } from './skillManager';

function fetchVersion(url: string): Promise<string> {
  return new Promise((resolve, reject) => {
    const client = url.startsWith('https') ? https : http;
    client
      .get(url, res => {
        let data = '';
        res.on('data', chunk => (data += chunk));
        res.on('end', () => {
          try { resolve(JSON.parse(data).version ?? 'unknown'); }
          catch (_e) { reject(new Error('Invalid JSON')); }
        });
      })
      .on('error', reject);
  });
}

function esc(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

export class SidebarProvider implements vscode.WebviewViewProvider {
  static readonly viewType = 'custtrAiSidebar';

  private _view?: vscode.WebviewView;
  private _currentVersion: string;
  private _latestVersion = 'checking…';

  constructor(
    private readonly context: vscode.ExtensionContext,
    private readonly skillManager: SkillManager
  ) {
    const ext = vscode.extensions.getExtension('custtr.custtr-ai');
    this._currentVersion = ext?.packageJSON?.version ?? '0.0.0';
  }

  resolveWebviewView(webviewView: vscode.WebviewView): void {
    this._view = webviewView;
    webviewView.webview.options = { enableScripts: true };
    webviewView.webview.html = this._html();

    webviewView.webview.onDidReceiveMessage(msg => {
      switch (msg.command) {
        case 'openReadme':
          vscode.env.openExternal(vscode.Uri.parse('vscode:extension/custtr.custtr-ai'));
          break;
        case 'openSkill':
          vscode.workspace.openTextDocument(msg.path).then(doc =>
            vscode.window.showTextDocument(doc)
          );
          break;
        case 'contributeSkill':
          vscode.commands.executeCommand('custtr-ai.contributeSkill', msg.skillName);
          break;
        case 'refresh':
          this.refresh();
          break;
      }
    });

    this._fetchLatest();
  }

  refresh(): void {
    if (this._view) {
      this._view.webview.html = this._html();
    }
  }

  private async _fetchLatest(): Promise<void> {
    const config = vscode.workspace.getConfiguration('custtr-ai');
    const url = config.get<string>('releasesUrl', '');
    if (!url) {
      this._latestVersion = 'not configured';
      this._redraw();
      return;
    }
    try {
      this._latestVersion = await fetchVersion(url);
    } catch (_e) {
      this._latestVersion = 'unavailable';
    }
    this._redraw();
  }

  private _redraw(): void {
    if (this._view) {
      this._view.webview.html = this._html();
    }
  }

  private _skillRow(s: Skill, showContribute: boolean): string {
    const pathJson = esc(JSON.stringify(s.mdPath));
    const nameJson = esc(JSON.stringify(s.name));
    return `
      <div class="skill-row" onclick="send('openSkill',{path:${pathJson}})">
        <svg class="skill-icon" viewBox="0 0 16 16" fill="currentColor">
          <path d="M2 4h12v1H2V4zm0 3h12v1H2V7zm0 3h8v1H2v-1z"/>
        </svg>
        <span class="skill-name">${esc(s.displayName)}</span>
        ${s.version ? `<span class="skill-ver">v${esc(s.version)}</span>` : ''}
        ${showContribute
          ? `<button class="pr-btn" title="Contribute via PR"
               onclick="event.stopPropagation();send('contributeSkill',{skillName:${nameJson}})">⎇</button>`
          : ''}
      </div>`;
  }

  private _html(): string {
    const cur = this._currentVersion;
    const lat = this._latestVersion;
    const checking = lat === 'checking…';
    const upToDate = !checking && lat === cur;
    const hasUpdate = !checking && !upToDate && !['unavailable', 'not configured'].includes(lat);

    const badge = hasUpdate
      ? `<span class="badge warn">↑ Update available</span>`
      : '';

    const custtrSkills = this.skillManager.getCUSTTRSkills();
    const userSkills = this.skillManager.getUserSkills();

    const custtrRows = custtrSkills.length
      ? custtrSkills.map(s => this._skillRow(s, false)).join('')
      : `<div class="empty">No skills bundled yet</div>`;

    const userRows = userSkills.length
      ? userSkills.map(s => this._skillRow(s, true)).join('')
      : `<div class="empty">No local skills in ~/.claude/skills</div>`;

    return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta http-equiv="Content-Security-Policy"
  content="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline';">
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    font-family: var(--vscode-font-family);
    font-size: var(--vscode-font-size);
    color: var(--vscode-foreground);
    background: transparent;
    overflow-x: hidden;
  }

  /* ── Header ── */
  .header {
    padding: 10px 14px 10px;
    border-bottom: 1px solid var(--vscode-sideBarSectionHeader-border,
      rgba(128,128,128,0.2));
  }
  .ext-title {
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.2px;
    margin-bottom: 3px;
  }
  .readme-link {
    font-size: 11px;
    color: var(--vscode-textLink-foreground);
    cursor: pointer;
    text-decoration: none;
    display: inline-block;
    margin-bottom: 7px;
  }
  .readme-link:hover { text-decoration: underline; }
  .versions {
    font-size: 11px;
    color: var(--vscode-descriptionForeground);
    display: flex;
    flex-direction: column;
    gap: 2px;
  }
  .badge {
    display: inline-block;
    font-size: 10px;
    padding: 1px 5px;
    border-radius: 3px;
    margin-left: 5px;
    vertical-align: middle;
  }
  .ok   { background: #388e3c; color: #fff; }
  .warn { background: #f57c00; color: #fff; }

  /* ── Section headings ── */
  .section-title {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
    text-transform: uppercase;
    color: var(--vscode-sideBarSectionHeader-foreground, var(--vscode-foreground));
    padding: 10px 14px 4px;
    opacity: 0.7;
  }

  /* ── Skill rows ── */
  .skill-row {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 4px 14px;
    cursor: pointer;
    border-radius: 3px;
  }
  .skill-row:hover { background: var(--vscode-list-hoverBackground); }
  .skill-icon {
    width: 14px;
    height: 14px;
    flex-shrink: 0;
    color: var(--vscode-descriptionForeground);
  }
  .skill-name { flex: 1; font-size: 12px; text-transform: none; }
  .skill-ver  { font-size: 10px; color: var(--vscode-descriptionForeground); }

  .pr-btn {
    background: none;
    border: none;
    color: var(--vscode-descriptionForeground);
    cursor: pointer;
    font-size: 13px;
    padding: 0 2px;
    opacity: 0;
    line-height: 1;
  }
  .skill-row:hover .pr-btn { opacity: 1; }
  .pr-btn:hover { color: var(--vscode-foreground); }

  .empty {
    font-size: 11px;
    color: var(--vscode-descriptionForeground);
    padding: 3px 14px;
    font-style: italic;
  }
</style>
</head>
<body>

  <div class="header">
    <a class="readme-link" href="#" onclick="send('openReadme');return false;">#README</a>
    <div class="versions">
      <span>Installed: <strong>v${cur}</strong>${badge}</span>
      <span>Latest:&nbsp;&nbsp;&nbsp; <strong>${checking || ['unavailable', 'not configured'].includes(lat) ? lat : 'v' + lat}</strong></span>
    </div>
  </div>

  <div class="section-title">CUSTTR Skills</div>
  ${custtrRows}

  <div class="section-title">User Skills</div>
  ${userRows}

<script>
  const api = acquireVsCodeApi();
  function send(command, data) { api.postMessage({ command, ...(data || {}) }); }
</script>
</body>
</html>`;
  }
}
