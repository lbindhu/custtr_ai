import * as vscode from 'vscode';

const SECRET_KEY = 'custtr-ai.githubToken';

export class CredentialManager {
  constructor(private context: vscode.ExtensionContext) {}

  async getToken(): Promise<string | undefined> {
    return this.context.secrets.get(SECRET_KEY);
  }

  async setToken(token: string): Promise<void> {
    await this.context.secrets.store(SECRET_KEY, token);
  }

  async deleteToken(): Promise<void> {
    await this.context.secrets.delete(SECRET_KEY);
  }

  async promptForToken(): Promise<string | undefined> {
    const token = await vscode.window.showInputBox({
      title: 'CUSTTR AI — GitHub Token',
      prompt: 'Paste your GitHub Enterprise personal access token (needs repo + workflow scopes)',
      password: true,
      ignoreFocusOut: true,
      placeHolder: 'ghp_...'
    });

    if (token) {
      await this.setToken(token);
      vscode.window.showInformationMessage('CUSTTR AI: GitHub token saved.');
      return token;
    }

    return undefined;
  }

  async getOrPromptToken(): Promise<string | undefined> {
    const existing = await this.getToken();
    if (existing) {
      return existing;
    }
    return this.promptForToken();
  }
}
