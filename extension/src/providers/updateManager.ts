import * as vscode from 'vscode';
import * as https from 'https';
import * as http from 'http';

interface LatestRelease {
  version: string;
  downloadUrl: string;
  releaseNotes?: string;
}

function fetchJson(url: string): Promise<LatestRelease> {
  return new Promise((resolve, reject) => {
    const client = url.startsWith('https') ? https : http;
    client
      .get(url, res => {
        let data = '';
        res.on('data', chunk => (data += chunk));
        res.on('end', () => {
          try {
            resolve(JSON.parse(data));
          } catch (_e) {
            reject(new Error('Invalid JSON in latest.json'));
          }
        });
      })
      .on('error', reject);
  });
}

export class UpdateManager {
  private currentVersion: string;

  constructor(private context: vscode.ExtensionContext) {
    const ext = vscode.extensions.getExtension('custtr.custtr-ai');
    this.currentVersion = ext?.packageJSON?.version ?? '0.0.0';
  }

  async checkForUpdates(showUpToDate: boolean): Promise<void> {
    const config = vscode.workspace.getConfiguration('custtr-ai');
    const releasesUrl = config.get<string>('releasesUrl', '');

    if (!releasesUrl) {
      if (showUpToDate) {
        vscode.window.showWarningMessage(
          'CUSTTR AI: No releases URL configured (custtr-ai.releasesUrl).'
        );
      }
      return;
    }

    let latest: LatestRelease;
    try {
      latest = await fetchJson(releasesUrl);
    } catch (_e) {
      if (showUpToDate) {
        vscode.window.showErrorMessage('CUSTTR AI: Could not reach releases URL.');
      }
      return;
    }

    if (this.isNewer(latest.version, this.currentVersion)) {
      const action = await vscode.window.showInformationMessage(
        `CUSTTR AI update available: v${latest.version} (you have v${this.currentVersion})`,
        'Download',
        'Later'
      );
      if (action === 'Download') {
        await vscode.env.openExternal(vscode.Uri.parse(latest.downloadUrl));
      }
    } else if (showUpToDate) {
      vscode.window.showInformationMessage(
        `CUSTTR AI is up to date (v${this.currentVersion}).`
      );
    }
  }

  private isNewer(remote: string, local: string): boolean {
    const parse = (v: string) => v.split('.').map(Number);
    const r = parse(remote);
    const l = parse(local);
    for (let i = 0; i < Math.max(r.length, l.length); i++) {
      const rv = r[i] ?? 0;
      const lv = l[i] ?? 0;
      if (rv > lv) { return true; }
      if (rv < lv) { return false; }
    }
    return false;
  }
}
