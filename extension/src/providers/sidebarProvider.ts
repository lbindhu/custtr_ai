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

  private _skillIcon(name: string): string {
    if (name.includes('pptx') || name.includes('storyboard') || name.includes('sb-'))
      return `<path d="M13 2H3a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1V3a1 1 0 0 0-1-1zM3 1h10a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V3a2 2 0 0 1 2-2zm2 4h6v1H5V5zm0 3h6v1H5V8zm0 3h4v1H5v-1z"/>`;
    if (name.includes('mp4') || name.includes('scorm') || name.includes('vo-'))
      return `<path d="M6 3l7 5-7 5V3z"/>`;
    if (name.includes('training') || name.includes('advisor'))
      return `<path d="M8 1a7 7 0 1 1 0 14A7 7 0 0 1 8 1zm0 1a6 6 0 1 0 0 12A6 6 0 0 0 8 2zm0 2a1 1 0 1 1 0 2 1 1 0 0 1 0-2zm-1 3h2v5H7V7z"/>`;
    if (name.includes('copyright'))
      return `<path d="M8 1a7 7 0 1 1 0 14A7 7 0 0 1 8 1zm0 1a6 6 0 1 0 0 12A6 6 0 0 0 8 2zM6.5 5.5C7 5 7.5 4.8 8 4.8c1.2 0 2.2 1 2.2 2.2 0 .8-.4 1.5-1 1.9v.1c.8.4 1.3 1.2 1.3 2.1 0 1.4-1.1 2.4-2.5 2.4-.7 0-1.3-.2-1.8-.7l.7-.7c.3.3.7.5 1.1.5.8 0 1.4-.6 1.4-1.5 0-.9-.6-1.4-1.5-1.4H7.5V9h.3c.7 0 1.2-.5 1.2-1.2 0-.6-.5-1.1-1.1-1.1-.4 0-.7.1-1 .4l-.4-.6z"/>`;
    if (name.includes('workbook') || name.includes('participant'))
      return `<path d="M3 1h10a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1zm0 1v12h10V2H3zm2 2h6v1H5V4zm0 2h6v1H5V6zm0 2h4v1H5V8z"/>`;
    return `<path d="M2 4h12v1H2V4zm0 3h12v1H2V7zm0 3h8v1H2v-1z"/>`;
  }

  private _skillLabel(name: string): string {
    if (name.includes('pptx') || name.includes('storyboard')) return 'Slides';
    if (name.includes('mp4') || name.includes('scorm'))        return 'Video';
    if (name.includes('vo-'))                                  return 'Audio';
    if (name.includes('training') || name.includes('advisor')) return 'Learning';
    if (name.includes('copyright'))                            return 'Compliance';
    if (name.includes('workbook') || name.includes('participant')) return 'Docs';
    if (name.includes('sb-'))                                  return 'Slides';
    return 'Skill';
  }

  private _skillRow(s: Skill, showContribute: boolean): string {
    const pathJson = esc(JSON.stringify(s.mdPath));
    const nameJson = esc(JSON.stringify(s.name));
    const trigger = s.description
      ? s.description.split('.')[0].trim()
      : s.displayName;
    const triggerJson = esc(JSON.stringify(trigger));
    const shortName = esc(s.displayName.replace(/^custtr-/, '').replace(/-/g, ' '));
    const desc = s.description ? esc(s.description.slice(0, 90)) + (s.description.length > 90 ? '…' : '') : '';
    const label = this._skillLabel(s.name);
    const icon = this._skillIcon(s.name);

    return `
      <div class="skill-card" onclick="send('openSkill',{path:${pathJson}})">
        <div class="skill-card-left">
          <div class="skill-avatar">
            <svg viewBox="0 0 16 16" fill="currentColor" width="16" height="16">${icon}</svg>
          </div>
        </div>
        <div class="skill-card-body">
          <div class="skill-card-header">
            <span class="skill-card-name">${shortName}</span>
            <span class="skill-tag">${label}</span>
            ${s.version ? `<span class="skill-ver">v${esc(s.version)}</span>` : ''}
          </div>
          ${desc ? `<div class="skill-card-desc">${desc}</div>` : ''}
        </div>
        <div class="skill-card-actions">
          <button class="run-btn" title="Run in Claude chat"
            onclick="event.stopPropagation();send('runSkill',{trigger:${triggerJson}})">
            <svg viewBox="0 0 16 16" fill="currentColor" width="12" height="12"><path d="M4 3l9 5-9 5V3z"/></svg>
          </button>
          ${showContribute
            ? `<button class="pr-btn" title="Contribute via PR"
                 onclick="event.stopPropagation();send('contributeSkill',{skillName:${nameJson}})">⎇</button>`
            : ''}
        </div>
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
    animation: slideDown 0.4s cubic-bezier(0.16,1,0.3,1);
  }
  @keyframes slideDown {
    from { max-height: 0; opacity: 0; transform: translateY(-10px); }
    to   { max-height: 120px; opacity: 1; transform: translateY(0); }
  }
  .update-banner-inner {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 9px 12px;
    background: linear-gradient(135deg, #b84700 0%, #e07000 100%);
    color: #fff;
    border-bottom: 1px solid rgba(0,0,0,0.15);
  }
  .update-pulse {
    width: 8px; height: 8px;
    border-radius: 50%;
    background: #fff;
    flex-shrink: 0;
    animation: pulse 1.6s ease-in-out infinite;
  }
  @keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); box-shadow: 0 0 0 0 rgba(255,255,255,0.4); }
    50%       { opacity: 0.6; transform: scale(1.3); box-shadow: 0 0 0 4px rgba(255,255,255,0); }
  }
  .update-text { flex: 1; display: flex; flex-direction: column; gap: 2px; min-width: 0; }
  .update-title { font-size: 11px; font-weight: 700; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .update-notes { font-size: 10px; opacity: 0.8; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .update-btn {
    background: rgba(255,255,255,0.2);
    border: 1px solid rgba(255,255,255,0.5);
    color: #fff; font-size: 11px; font-weight: 600;
    padding: 3px 9px; border-radius: 4px; cursor: pointer;
    white-space: nowrap; transition: background 0.15s; flex-shrink: 0;
  }
  .update-btn:hover { background: rgba(255,255,255,0.35); }
  .update-dismiss {
    background: none; border: none; color: rgba(255,255,255,0.65);
    font-size: 12px; cursor: pointer; padding: 0 2px; flex-shrink: 0; line-height: 1;
  }
  .update-dismiss:hover { color: #fff; }

  /* ── Header ── */
  .header {
    padding: 12px 14px 11px;
    border-bottom: 1px solid var(--vscode-sideBarSectionHeader-border, rgba(128,128,128,0.15));
    background: var(--vscode-sideBar-background, transparent);
  }
  .header-top {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 8px;
  }
  .header-logo {
    width: 28px; height: 28px;
    background: linear-gradient(135deg, #e84d0e 0%, #f07030 100%);
    border-radius: 6px;
    display: flex; align-items: center; justify-content: center;
    flex-shrink: 0;
    box-shadow: 0 1px 4px rgba(0,0,0,0.25);
  }
  .header-logo svg { display: block; }
  .header-brand { flex: 1; }
  .header-brand-name {
    font-size: 13px; font-weight: 700; letter-spacing: 0.3px;
    color: var(--vscode-foreground);
    line-height: 1.2;
  }
  .header-brand-sub {
    font-size: 10px;
    color: var(--vscode-descriptionForeground);
    letter-spacing: 0.2px;
  }
  .readme-btn {
    background: none; border: 1px solid var(--vscode-button-border, rgba(128,128,128,0.3));
    color: var(--vscode-descriptionForeground); font-size: 10px;
    padding: 2px 7px; border-radius: 3px; cursor: pointer;
    transition: border-color 0.15s, color 0.15s; white-space: nowrap;
  }
  .readme-btn:hover {
    border-color: var(--vscode-textLink-foreground);
    color: var(--vscode-textLink-foreground);
  }
  .version-row {
    display: flex; align-items: center; gap: 6px;
    font-size: 10px; color: var(--vscode-descriptionForeground);
  }
  .version-pill {
    background: var(--vscode-badge-background, rgba(128,128,128,0.2));
    color: var(--vscode-badge-foreground, var(--vscode-foreground));
    padding: 1px 6px; border-radius: 10px; font-size: 10px; font-weight: 600;
  }
  .version-sep { opacity: 0.4; }

  /* ── Section headings ── */
  .section-header {
    display: flex; align-items: center; gap: 6px;
    padding: 10px 14px 5px;
    border-bottom: 1px solid var(--vscode-sideBarSectionHeader-border, rgba(128,128,128,0.1));
  }
  .section-title {
    font-size: 10px; font-weight: 700; letter-spacing: 0.8px;
    text-transform: uppercase;
    color: var(--vscode-sideBarSectionHeader-foreground, var(--vscode-foreground));
    opacity: 0.65; flex: 1;
  }
  .section-count {
    font-size: 10px; font-weight: 600;
    background: var(--vscode-badge-background, rgba(128,128,128,0.2));
    color: var(--vscode-badge-foreground, var(--vscode-foreground));
    padding: 1px 6px; border-radius: 8px; opacity: 0.85;
  }

  /* ── Skill cards ── */
  .skills-list { padding: 4px 0; }

  .skill-card {
    display: flex; align-items: flex-start; gap: 0;
    padding: 6px 10px 6px 12px;
    cursor: pointer;
    border-radius: 4px;
    margin: 1px 6px;
    transition: background 0.12s;
    position: relative;
  }
  .skill-card:hover { background: var(--vscode-list-hoverBackground); }
  .skill-card:active { background: var(--vscode-list-activeSelectionBackground); }

  .skill-card-left { margin-right: 9px; padding-top: 1px; }
  .skill-avatar {
    width: 28px; height: 28px;
    border-radius: 6px;
    background: var(--vscode-badge-background, rgba(128,128,128,0.15));
    display: flex; align-items: center; justify-content: center;
    flex-shrink: 0;
    color: var(--vscode-textLink-foreground);
    transition: background 0.12s;
  }
  .skill-card:hover .skill-avatar {
    background: var(--vscode-textLink-foreground);
    color: #fff;
  }

  .skill-card-body { flex: 1; min-width: 0; }
  .skill-card-header {
    display: flex; align-items: center; gap: 5px;
    margin-bottom: 2px;
  }
  .skill-card-name {
    font-size: 12px; font-weight: 600;
    color: var(--vscode-foreground);
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    text-transform: capitalize; flex: 1; min-width: 0;
  }
  .skill-tag {
    font-size: 9px; font-weight: 700; letter-spacing: 0.3px;
    padding: 1px 5px; border-radius: 3px; flex-shrink: 0;
    background: rgba(var(--vscode-textLink-activeForeground, 0,122,204), 0.12);
    color: var(--vscode-textLink-foreground);
    text-transform: uppercase;
  }
  .skill-ver {
    font-size: 9px; color: var(--vscode-descriptionForeground);
    flex-shrink: 0; opacity: 0.7;
  }
  .skill-card-desc {
    font-size: 11px; color: var(--vscode-descriptionForeground);
    line-height: 1.4; opacity: 0.85;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }

  /* ── Card action buttons ── */
  .skill-card-actions {
    display: flex; flex-direction: column; gap: 3px;
    margin-left: 6px; opacity: 0;
    transition: opacity 0.12s;
    flex-shrink: 0;
  }
  .skill-card:hover .skill-card-actions { opacity: 1; }

  .run-btn {
    display: flex; align-items: center; justify-content: center;
    width: 22px; height: 22px; border-radius: 4px;
    background: var(--vscode-textLink-foreground);
    color: #fff; border: none; cursor: pointer;
    transition: background 0.12s, transform 0.1s;
    flex-shrink: 0;
  }
  .run-btn:hover { filter: brightness(1.15); transform: scale(1.08); }

  .pr-btn {
    display: flex; align-items: center; justify-content: center;
    width: 22px; height: 22px; border-radius: 4px;
    background: none;
    border: 1px solid var(--vscode-button-border, rgba(128,128,128,0.3));
    color: var(--vscode-descriptionForeground); font-size: 12px;
    cursor: pointer; transition: border-color 0.12s, color 0.12s;
    flex-shrink: 0;
  }
  .pr-btn:hover { border-color: var(--vscode-textLink-foreground); color: var(--vscode-textLink-foreground); }

  /* ── Empty state ── */
  .empty {
    display: flex; flex-direction: column; align-items: center;
    padding: 16px 14px; gap: 6px;
    color: var(--vscode-descriptionForeground);
  }
  .empty-icon { font-size: 22px; opacity: 0.4; }
  .empty-text { font-size: 11px; font-style: italic; opacity: 0.7; text-align: center; }
</style>
</head>
<body>

  ${updateBanner}

  <div class="header">
    <div class="header-top">
      <div class="header-logo">
        <svg viewBox="0 0 20 20" fill="white" width="16" height="16">
          <path d="M10 2L3 7v9h5v-5h4v5h5V7l-7-5z"/>
        </svg>
      </div>
      <div class="header-brand">
        <div class="header-brand-name">CUSTTR AI</div>
        <div class="header-brand-sub">AMD Customer Training</div>
      </div>
      <button class="readme-btn" onclick="send('openReadme')">README</button>
    </div>
    <div class="version-row">
      <span>Installed</span>
      <span class="version-pill">v${cur}</span>
      <span class="version-sep">·</span>
      <span>Latest</span>
      <span class="version-pill">${checking || ['unavailable', 'not configured'].includes(lat) ? lat : 'v' + lat}</span>
    </div>
  </div>

  <div class="section-header">
    <span class="section-title">CUSTTR Skills</span>
    <span class="section-count">${custtrSkills.length}</span>
  </div>
  <div class="skills-list">${custtrRows}</div>

  <div class="section-header">
    <span class="section-title">User Skills</span>
    <span class="section-count">${userSkills.length}</span>
  </div>
  <div class="skills-list">${userRows}</div>

<script>
  const api = acquireVsCodeApi();
  function send(command, data) { api.postMessage({ command, ...(data || {}) }); }
  function dismissBanner() {
    const b = document.getElementById('updateBanner');
    if (b) {
      b.style.transition = 'max-height 0.25s ease, opacity 0.2s ease';
      b.style.maxHeight = '0'; b.style.opacity = '0';
      setTimeout(() => b.remove(), 260);
    }
  }
</script>
</body>
</html>`;
  }
}
