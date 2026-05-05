import * as vscode from 'vscode';
import * as https from 'https';
import * as http from 'http';

function fetchVersion(url: string): Promise<string> {
  return new Promise((resolve, reject) => {
    const client = url.startsWith('https') ? https : http;
    client
      .get(url, res => {
        let data = '';
        res.on('data', chunk => (data += chunk));
        res.on('end', () => {
          try {
            resolve(JSON.parse(data).version ?? 'unknown');
          } catch (_e) {
            reject(new Error('Invalid JSON'));
          }
        });
      })
      .on('error', reject);
  });
}

export class WelcomeViewProvider implements vscode.WebviewViewProvider {
  static readonly viewType = 'custtrAiWelcome';

  private _view?: vscode.WebviewView;
  private _currentVersion: string;
  private _latestVersion = 'checking…';

  constructor(private readonly context: vscode.ExtensionContext) {
    const ext = vscode.extensions.getExtension('custtr.custtr-ai');
    this._currentVersion = ext?.packageJSON?.version ?? '0.0.0';
  }

  resolveWebviewView(webviewView: vscode.WebviewView): void {
    this._view = webviewView;

    webviewView.webview.options = {
      enableScripts: true,
      enableCommandUris: true
    };

    webviewView.webview.html = this._html();

    webviewView.webview.onDidReceiveMessage(msg => {
      if (msg.command === 'openReadme') {
        vscode.commands.executeCommand(
          'workbench.extensions.action.showExtensionsWithIds',
          ['custtr.custtr-ai']
        );
      }
    });

    this._fetchLatest();
  }

  private async _fetchLatest(): Promise<void> {
    const config = vscode.workspace.getConfiguration('custtr-ai');
    const url = config.get<string>('releasesUrl', '');

    if (!url) {
      this._latestVersion = 'not configured';
      this._update();
      return;
    }

    try {
      this._latestVersion = await fetchVersion(url);
    } catch (_e) {
      this._latestVersion = 'unavailable';
    }
    this._update();
  }

  private _update(): void {
    if (this._view) {
      this._view.webview.html = this._html();
    }
  }

  private _html(): string {
    const cur = this._currentVersion;
    const lat = this._latestVersion;

    const isChecking = lat === 'checking…';
    const isUpToDate = !isChecking && lat === cur;
    const hasUpdate = !isChecking && lat !== cur && lat !== 'unavailable' && lat !== 'not configured';

    const badge = isUpToDate
      ? `<span class="badge ok">&#10003; Up to date</span>`
      : hasUpdate
      ? `<span class="badge warn">&#8593; Update available</span>`
      : '';

    return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline';">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: var(--vscode-font-family);
    font-size: var(--vscode-font-size);
    color: var(--vscode-foreground);
    padding: 10px 12px 12px;
    background: transparent;
  }
  .title {
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.3px;
    margin-bottom: 4px;
  }
  .title a {
    color: var(--vscode-foreground);
    text-decoration: none;
  }
  .title a:hover {
    color: var(--vscode-textLink-activeForeground);
    text-decoration: underline;
    cursor: pointer;
  }
  .readme-link {
    font-size: 11px;
    color: var(--vscode-textLink-foreground);
    text-decoration: none;
    cursor: pointer;
    display: inline-block;
    margin-bottom: 8px;
  }
  .readme-link:hover { text-decoration: underline; }
  .versions {
    font-size: 11px;
    color: var(--vscode-descriptionForeground);
    display: flex;
    flex-direction: column;
    gap: 3px;
  }
  .versions span { display: flex; align-items: center; gap: 6px; }
  .badge {
    font-size: 10px;
    padding: 1px 5px;
    border-radius: 3px;
  }
  .ok   { background: #388e3c; color: #fff; }
  .warn { background: #f57c00; color: #fff; }
</style>
</head>
<body>
  <div class="title">
    <a href="#" onclick="send('openReadme')">CUSTTR AI</a>
  </div>
  <a class="readme-link" href="#" onclick="send('openReadme')">&#128196; Open README</a>
  <div class="versions">
    <span>Installed: <strong>v${cur}</strong></span>
    <span>Latest:&nbsp;&nbsp;&nbsp; <strong>${isChecking ? lat : 'v' + lat}</strong> ${badge}</span>
  </div>
  <script>
    const api = acquireVsCodeApi();
    function send(command) { api.postMessage({ command }); return false; }
  </script>
</body>
</html>`;
  }
}
