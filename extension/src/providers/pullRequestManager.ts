import * as vscode from 'vscode';

export class PullRequestManager {
  async openPullRequestPage(skillName: string): Promise<void> {
    const config = vscode.workspace.getConfiguration('custtr-ai');
    const repoUrl = config.get<string>('repoUrl', '');

    if (!repoUrl) {
      vscode.window.showErrorMessage(
        'CUSTTR AI: No repository URL configured. Set custtr-ai.repoUrl in settings.'
      );
      return;
    }

    const prUrl = this.buildPrUrl(repoUrl, skillName);

    const action = await vscode.window.showInformationMessage(
      `Contribute "${skillName}" to the team — GitHub will open a web editor where you can fill in the skill and submit a PR.`,
      'Open in GitHub',
      'Cancel'
    );

    if (action === 'Open in GitHub') {
      await vscode.env.openExternal(vscode.Uri.parse(prUrl));
    }
  }

  private buildPrUrl(repoUrl: string, skillName: string): string {
    const base = repoUrl.replace(/\/$/, '');
    const filename = encodeURIComponent(`extension/skills/${skillName}/SKILL.md`);
    return `${base}/new/main?filename=${filename}`;
  }
}
