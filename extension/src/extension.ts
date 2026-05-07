import * as vscode from 'vscode';
import { SkillManager } from './providers/skillManager';
import { CredentialManager } from './providers/credentialManager';
import { PullRequestManager } from './providers/pullRequestManager';
import { UpdateManager } from './providers/updateManager';
import { StatusBarManager } from './providers/statusBarManager';
import { SidebarProvider } from './providers/sidebarProvider';

export function activate(context: vscode.ExtensionContext) {
  const credentialManager = new CredentialManager(context);
  const skillManager = new SkillManager(context);
  const pullRequestManager = new PullRequestManager();
  const updateManager = new UpdateManager(context);
  const statusBarManager = new StatusBarManager(context);
  const sidebarProvider = new SidebarProvider(context, skillManager);

  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider(SidebarProvider.viewType, sidebarProvider, {
      webviewOptions: { retainContextWhenHidden: true }
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand('custtr-ai.refreshSkills', () => {
      sidebarProvider.refresh();
    }),

    vscode.commands.registerCommand('custtr-ai.openSkill', (skillPath: string) => {
      vscode.workspace.openTextDocument(skillPath).then(doc =>
        vscode.window.showTextDocument(doc)
      );
    }),

    vscode.commands.registerCommand('custtr-ai.contributeSkill', (skillName: string) => {
      pullRequestManager.openPullRequestPage(skillName);
    }),

    vscode.commands.registerCommand('custtr-ai.checkForUpdates', async () => {
      await updateManager.checkForUpdates(true);
    }),

    vscode.commands.registerCommand('custtr-ai.setGitHubToken', async () => {
      await credentialManager.promptForToken();
    }),

    vscode.commands.registerCommand('custtr-ai.openReadme', () => {
      vscode.commands.executeCommand(
        'workbench.extensions.action.showExtensionsWithIds',
        ['custtr.custtr-ai']
      );
    })
  );

  statusBarManager.show();

  const config = vscode.workspace.getConfiguration('custtr-ai');
  if (config.get<boolean>('checkUpdatesOnStartup', true)) {
    updateManager.checkForUpdates(false);
  }
}

export function deactivate() {}
