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
    return this.loadSkillsFromDir(this.userSkillsPath, 'user');
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
