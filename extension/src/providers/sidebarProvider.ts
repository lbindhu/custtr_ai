import * as vscode from 'vscode';
import * as https from 'https';
import * as http from 'http';
import { SkillManager, Skill } from './skillManager';

interface LatestInfo { version: string; releaseNotes?: string; }

function fetchLatestInfo(url: string): Promise<LatestInfo> {
  return new Promise((resolve, reject) => {
    const client = url.startsWith('https') ? https : http;
    client
      .get(url, res => {
        let data = '';
        res.on('data', chunk => (data += chunk));
        res.on('end', () => {
          try {
            const j = JSON.parse(data);
            resolve({ version: j.version ?? 'unknown', releaseNotes: j.releaseNotes });
          }
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
  private _releaseNotes = '';

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
        case 'runSkill':
          vscode.commands.executeCommand('workbench.action.chat.open', { query: msg.trigger });
          break;
        case 'contributeSkill':
          vscode.commands.executeCommand('custtr-ai.contributeSkill', msg.skillName);
          break;
        case 'installUpdate':
          vscode.commands.executeCommand('custtr-ai.checkForUpdates');
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
      const info = await fetchLatestInfo(url);
      this._latestVersion = info.version;
      this._releaseNotes = info.releaseNotes ?? '';
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
    const trigger = s.description
      ? s.description.split('.')[0].trim()
      : s.displayName;
    const triggerJson = esc(JSON.stringify(trigger));
    return `
      <div class="skill-row" onclick="send('openSkill',{path:${pathJson}})">
        <svg class="skill-icon" viewBox="0 0 16 16" fill="currentColor">
          <path d="M2 4h12v1H2V4zm0 3h12v1H2V7zm0 3h8v1H2v-1z"/>
        </svg>
        <span class="skill-name">${esc(s.displayName)}</span>
        ${s.version ? `<span class="skill-ver">v${esc(s.version)}</span>` : ''}
        <button class="run-btn" title="Run this skill in Claude chat"
          onclick="event.stopPropagation();send('runSkill',{trigger:${triggerJson}})">▶</button>
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
    const notes = esc(this._releaseNotes);

    const custtrSkills = this.skillManager.getCUSTTRSkills();
    const userSkills = this.skillManager.getUserSkills();

    const custtrRows = custtrSkills.length
      ? custtrSkills.map(s => this._skillRow(s, false)).join('')
      : `<div class="empty">No skills bundled yet</div>`;

    const userRows = userSkills.length
      ? userSkills.map(s => this._skillRow(s, true)).join('')
      : `<div class="empty">No local skills in ~/.claude/skills</div>`;

    const updateBanner = hasUpdate ? `
      <div class="update-banner" id="updateBanner">
        <div class="update-banner-inner">
          <div class="update-pulse"></div>
          <div class="update-text">
            <span class="update-title">⬆ Update Available — v${esc(lat)}</span>
            ${notes ? `<span class="update-notes">${notes}</span>` : ''}
          </div>
          <button class="update-btn" onclick="send('installUpdate')">Update Now</button>
          <button class="update-dismiss" title="Dismiss" onclick="dismissBanner()">✕</button>
        </div>
      </div>` : '';

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

  /* ── Update Banner ── */
  .update-banner {
    overflow: hidden;
    animation: slideDown 0.35s ease-out;
  }
  @keyframes slideDown {
    from { max-height: 0; opacity: 0; transform: translateY(-8px); }
    to   { max-height: 120px; opacity: 1; transform: translateY(0); }
  }
  .update-banner-inner {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 12px;
    background: linear-gradient(135deg, #c65000 0%, #e07000 100%);
    color: #fff;
    position: relative;
  }
  .update-pulse {
    width: 8px; height: 8px;
    border-radius: 50%;
    background: #fff;
    flex-shrink: 0;
    animation: pulse 1.5s ease-in-out infinite;
  }
  @keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50%       { opacity: 0.4; transform: scale(1.4); }
  }
  .update-text {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 2px;
    min-width: 0;
  }
  .update-title {
    font-size: 11px;
    font-weight: 700;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .update-notes {
    font-size: 10px;
    opacity: 0.85;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .update-btn {
    background: rgba(255,255,255,0.2);
    border: 1px solid rgba(255,255,255,0.5);
    color: #fff;
    font-size: 11px;
    font-weight: 600;
    padding: 3px 9px;
    border-radius: 3px;
    cursor: pointer;
    white-space: nowrap;
    transition: background 0.15s;
    flex-shrink: 0;
  }
  .update-btn:hover { background: rgba(255,255,255,0.35); }
  .update-dismiss {
    background: none;
    border: none;
    color: rgba(255,255,255,0.7);
    font-size: 12px;
    cursor: pointer;
    padding: 0 2px;
    flex-shrink: 0;
    line-height: 1;
  }
  .update-dismiss:hover { color: #fff; }

  /* ── Header ── */
  .header {
    padding: 10px 14px 10px;
    border-bottom: 1px solid var(--vscode-sideBarSectionHeader-border,
      rgba(128,128,128,0.2));
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
  .skill-name { flex: 1; font-size: 12px; }
  .skill-ver  { font-size: 10px; color: var(--vscode-descriptionForeground); }

  .run-btn {
    background: none;
    border: none;
    color: var(--vscode-textLink-foreground);
    cursor: pointer;
    font-size: 11px;
    padding: 0 2px;
    opacity: 0;
    line-height: 1;
    transition: opacity 0.1s, transform 0.1s;
  }
  .skill-row:hover .run-btn { opacity: 1; }
  .run-btn:hover { transform: scale(1.2); }

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

  ${updateBanner}

  <div class="header">
    <a class="readme-link" href="#" onclick="send('openReadme');return false;">#README</a>
    <div class="versions">
      <span>Installed: <strong>v${cur}</strong></span>
      <span>Latest:&nbsp;&nbsp;&nbsp; <strong>${checking || ['unavailable', 'not configured'].includes(lat) ? lat : 'v' + lat}</strong></span>
    </div>
  </div>

  <div class="section-title">CUSTTR Skills (${custtrSkills.length})</div>
  ${custtrRows}

  <div class="section-title">User Skills (${userSkills.length})</div>
  ${userRows}

<script>
  const api = acquireVsCodeApi();
  function send(command, data) { api.postMessage({ command, ...(data || {}) }); }
  function dismissBanner() {
    const b = document.getElementById('updateBanner');
    if (b) { b.style.transition = 'max-height 0.25s ease, opacity 0.25s ease'; b.style.maxHeight = '0'; b.style.opacity = '0'; setTimeout(() => b.remove(), 260); }
  }
</script>
</body>
</html>`;
  }
}
