import * as vscode from 'vscode';
import { CredentialManager } from './credentialManager';

export class PullRequestManager {
  constructor(private credentialManager: CredentialManager) {}

  async openPullRequestPage(skillName: string): Promise<void> {
    const config = vscode.workspace.getConfiguration('custtr-ai');
    const repoUrl = config.get<string>('repoUrl', '');

    if (!repoUrl) {
      vscode.window.showErrorMessage(
        'CUSTTR AI: No repository URL configured. Set custtr-ai.repoUrl in settings.'
      );
      return;
    }

    const token = await this.credentialManager.getOrPromptToken();
    if (!token) {
      return;
    }

    const branchName = `add-${skillName}`;
    const prUrl = this.buildPrUrl(repoUrl, branchName, skillName);

    const action = await vscode.window.showInformationMessage(
      `Ready to open a pull request for skill "${skillName}".\n\nMake sure you have pushed your branch: git push origin ${branchName}`,
      'Open PR Page',
      'Cancel'
    );

    if (action === 'Open PR Page') {
      await vscode.env.openExternal(vscode.Uri.parse(prUrl));
    }
  }

  private buildPrUrl(repoUrl: string, branchName: string, skillName: string): string {
    const base = repoUrl.replace(/\/$/, '');
    const title = encodeURIComponent(`Add skill: ${skillName}`);
    const body = encodeURIComponent(
      `## New Skill: ${skillName}\n\n` +
      `This PR adds the \`${skillName}\` skill to the CUSTTR AI extension.\n\n` +
      `### Checklist\n` +
      `- [ ] SKILL.md describes what the skill does\n` +
      `- [ ] version.txt is set to 1.0\n` +
      `- [ ] Folder name starts with \`custtr-\``
    );
    return `${base}/compare/main...${branchName}?expand=1&title=${title}&body=${body}`;
  }
}
