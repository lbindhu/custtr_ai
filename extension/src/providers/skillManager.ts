import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';

export interface Skill {
  name: string;
  displayName: string;
  skillPath: string;
  mdPath: string;
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
        : '1.0';

      const displayName = entry.name
        .replace(/^custtr-/, '')
        .replace(/^psas-/, '')
        .replace(/^m365-/, 'M365 ');

      skills.push({
        name: entry.name,
        displayName,
        skillPath,
        mdPath,
        version,
        type
      });
    }

    return skills.sort((a, b) => a.displayName.localeCompare(b.displayName));
  }
}
