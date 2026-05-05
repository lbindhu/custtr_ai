import * as vscode from 'vscode';

export class StatusBarManager {
  private item: vscode.StatusBarItem;

  constructor(private context: vscode.ExtensionContext) {
    this.item = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
    this.item.command = 'custtr-ai.checkForUpdates';
    this.item.text = '$(library) CUSTTR AI';
    this.item.tooltip = 'CUSTTR AI — Click to check for updates';
    context.subscriptions.push(this.item);
  }

  show(): void {
    this.item.show();
  }

  hide(): void {
    this.item.hide();
  }

  setUpdating(): void {
    this.item.text = '$(sync~spin) CUSTTR AI';
    this.item.tooltip = 'CUSTTR AI — Checking for updates…';
  }

  setReady(): void {
    this.item.text = '$(library) CUSTTR AI';
    this.item.tooltip = 'CUSTTR AI — Click to check for updates';
  }

  setUpdateAvailable(version: string): void {
    this.item.text = `$(arrow-up) CUSTTR AI v${version} available`;
    this.item.tooltip = 'Click to download the latest CUSTTR AI extension';
  }
}
