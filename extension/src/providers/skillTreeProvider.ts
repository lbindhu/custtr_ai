import * as vscode from 'vscode';
import { SkillManager, Skill } from './skillManager';

export class SkillTreeItem extends vscode.TreeItem {
  constructor(
    public readonly skill: Skill,
    public readonly collapsibleState: vscode.TreeItemCollapsibleState
  ) {
    super(skill.displayName, collapsibleState);

    this.tooltip = `${skill.name} v${skill.version}`;
    this.description = `v${skill.version}`;
    this.contextValue = 'skill';

    this.command = {
      command: 'custtr-ai.openSkill',
      title: 'Open Skill',
      arguments: [skill.docPath]
    };

    this.iconPath = new vscode.ThemeIcon(
      skill.type === 'custtr' ? 'library' : 'file-code'
    );
  }
}

export class SkillTreeProvider implements vscode.TreeDataProvider<SkillTreeItem> {
  private _onDidChangeTreeData = new vscode.EventEmitter<SkillTreeItem | undefined | null | void>();
  readonly onDidChangeTreeData = this._onDidChangeTreeData.event;

  constructor(
    private skillManager: SkillManager,
    private viewType: 'custtr' | 'user'
  ) {}

  refresh(): void {
    this._onDidChangeTreeData.fire();
  }

  getTreeItem(element: SkillTreeItem): vscode.TreeItem {
    return element;
  }

  getChildren(): Thenable<SkillTreeItem[]> {
    const skills =
      this.viewType === 'custtr'
        ? this.skillManager.getCUSTTRSkills()
        : this.skillManager.getUserSkills();

    if (skills.length === 0) {
      return Promise.resolve([]);
    }

    return Promise.resolve(
      skills.map(skill => new SkillTreeItem(skill, vscode.TreeItemCollapsibleState.None))
    );
  }
}
