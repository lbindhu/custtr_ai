import * as vscode from 'vscode';
import * as https from 'https';
import * as http from 'http';
import * as fs from 'fs';
import * as path from 'path';
import * as cp from 'child_process';
import * as os from 'os';

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
          try { resolve(JSON.parse(data)); }
          catch (_e) { reject(new Error('Invalid JSON in latest.json')); }
        });
      })
      .on('error', reject);
  });
}

function downloadFile(url: string, destPath: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const file = fs.createWriteStream(destPath);
    const client = url.startsWith('https') ? https : http;
    client
      .get(url, res => {
        if (res.statusCode === 301 || res.statusCode === 302) {
          file.close();
          fs.unlink(destPath, () => {});
          return downloadFile(res.headers.location!, destPath).then(resolve).catch(reject);
        }
        res.pipe(file);
        file.on('finish', () => file.close(() => resolve()));
      })
      .on('error', err => { fs.unlink(destPath, () => {}); reject(err); });
  });
}

function resolveCodeBin(): string | null {
  // Derive the code CLI path from the running VS Code executable
  const exeDir = path.dirname(process.execPath);
  const candidates = [
    path.join(exeDir, 'bin', 'code.cmd'),   // Windows bundled install
    path.join(exeDir, 'bin', 'code'),        // Linux/macOS
    path.join(exeDir, '..', 'bin', 'code.cmd'),
    path.join(exeDir, '..', 'bin', 'code'),
  ];
  return candidates.find(c => fs.existsSync(c)) ?? null;
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
        `CUSTTR AI v${latest.version} is available (you have v${this.currentVersion}). Install now?`,
        'Install',
        'Later'
      );
      if (action === 'Install') {
        await this.installUpdate(latest);
      }
    } else if (showUpToDate) {
      vscode.window.showInformationMessage(
        `CUSTTR AI is up to date (v${this.currentVersion}).`
      );
    }
  }

  private async installUpdate(latest: LatestRelease): Promise<void> {
    const codeBin = resolveCodeBin();
    if (!codeBin) {
      // Fallback: open download page if we can't find the code binary
      await vscode.env.openExternal(vscode.Uri.parse(latest.downloadUrl));
      return;
    }

    const vsixPath = path.join(os.tmpdir(), `custtr-ai-${latest.version}.vsix`);

    await vscode.window.withProgress(
      { location: vscode.ProgressLocation.Notification, title: `Downloading CUSTTR AI v${latest.version}…`, cancellable: false },
      async () => { await downloadFile(latest.downloadUrl, vsixPath); }
    );

    await new Promise<void>((resolve, reject) => {
      cp.exec(`"${codeBin}" --install-extension "${vsixPath}" --force`, err => {
        fs.unlink(vsixPath, () => {});
        if (err) { reject(err); } else { resolve(); }
      });
    }).catch(async err => {
      vscode.window.showErrorMessage(`CUSTTR AI: Install failed — ${err.message}`);
      return;
    });

    const reload = await vscode.window.showInformationMessage(
      `CUSTTR AI v${latest.version} installed. Reload VS Code to apply.`,
      'Reload Now'
    );
    if (reload === 'Reload Now') {
      vscode.commands.executeCommand('workbench.action.reloadWindow');
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
