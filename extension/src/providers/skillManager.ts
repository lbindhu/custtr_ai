import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';

export interface Skill {
  name: string;
  displayName: string;
  description: string;
  skillPath: string;
  mdPath: string;
  docPath: string;
  version: string;
  type: 'custtr' | 'user';
}

export class SkillManager {
  private extensionPath: string;
  private userSkillsPath: string;

  constructor(private context: vscode.ExtensionContext) {
    this.extensionPath = context.extensionPath;
    this.userSkillsPath = path.join(
      process.env.USERPROFILE || process.env.HOME || '',
      '.claude',
      'skills'
    );
  }

  getCUSTTRSkills(): Skill[] {
    const skillsDir = path.join(this.extensionPath, 'skills');
    return this.loadSkillsFromDir(skillsDir, 'custtr');
  }

  getUserSkills(): Skill[] {
    if (!fs.existsSync(this.userSkillsPath)) {
      return [];
    }
    const bundledNames = new Set(this.getCUSTTRSkills().map(s => s.name));
    return this.loadSkillsFromDir(this.userSkillsPath, 'user')
      .filter(s => !bundledNames.has(s.name));
  }

  syncBundledSkills(): void {
    const bundledDir = path.join(this.extensionPath, 'skills');
    if (!fs.existsSync(bundledDir)) { return; }

    if (!fs.existsSync(this.userSkillsPath)) {
      fs.mkdirSync(this.userSkillsPath, { recursive: true });
    }

    const entries = fs.readdirSync(bundledDir, { withFileTypes: true });
    for (const entry of entries) {
      if (!entry.isDirectory() || !entry.name.startsWith('custtr-')) { continue; }

      const src = path.join(bundledDir, entry.name);
      const dest = path.join(this.userSkillsPath, entry.name);
      this._copyDir(src, dest);
    }
  }

  watchBundledSkills(onChange: () => void): vscode.Disposable {
    const bundledDir = path.join(this.extensionPath, 'skills');
    const watcher = vscode.workspace.createFileSystemWatcher(
      new vscode.RelativePattern(bundledDir, '**/*')
    );
    const handler = () => {
      this.syncBundledSkills();
      onChange();
    };
    watcher.onDidCreate(handler);
    watcher.onDidChange(handler);
    watcher.onDidDelete(handler);
    return watcher;
  }

  private _parseDescription(md: string): string {
    const fm = md.match(/^---\s*\n([\s\S]*?)\n---/);
    if (!fm) { return ''; }
    const block = fm[1];
    const m = block.match(/^description:\s*(.+)/m);
    if (!m) { return ''; }
    let val = m[1].trim();
    if (val === '>') {
      // multi-line folded scalar — collect indented lines
      const lines: string[] = [];
      let inDesc = false;
      for (const line of block.split('\n')) {
        if (/^description:\s*>/.test(line)) { inDesc = true; continue; }
        if (inDesc) {
          if (/^\s+/.test(line)) { lines.push(line.trim()); }
          else { break; }
        }
      }
      return lines.join(' ');
    }
    return val.replace(/^["']|["']$/g, '');
  }

  private _copyDir(src: string, dest: string): void {
    if (!fs.existsSync(dest)) { fs.mkdirSync(dest, { recursive: true }); }
    for (const entry of fs.readdirSync(src, { withFileTypes: true })) {
      const s = path.join(src, entry.name);
      const d = path.join(dest, entry.name);
      if (entry.isDirectory()) { this._copyDir(s, d); }
      else { fs.copyFileSync(s, d); }
    }
  }

  private loadSkillsFromDir(dir: string, type: 'custtr' | 'user'): Skill[] {
    if (!fs.existsSync(dir)) {
      return [];
    }

    const skills: Skill[] = [];
    const entries = fs.readdirSync(dir, { withFileTypes: true });

    for (const entry of entries) {
      if (!entry.isDirectory() || !entry.name.startsWith('custtr-')) {
        continue;
      }

      const skillPath = path.join(dir, entry.name);
      const mdPath = path.join(skillPath, 'SKILL.md');
      const versionPath = path.join(skillPath, 'version.txt');

      if (!fs.existsSync(mdPath)) {
        continue;
      }

      const version = fs.existsSync(versionPath)
        ? fs.readFileSync(versionPath, 'utf8').trim()
        : '';

      const mdContent = fs.readFileSync(mdPath, 'utf8');
      const description = this._parseDescription(mdContent);

      const readmePath = path.join(skillPath, 'README.md');
      const docPath = fs.existsSync(readmePath) ? readmePath : mdPath;

      skills.push({
        name: entry.name,
        displayName: entry.name,
        description,
        skillPath,
        mdPath,
        docPath,
        version,
        type
      });
    }

    return skills.sort((a, b) => a.displayName.localeCompare(b.displayName));
  }
}
