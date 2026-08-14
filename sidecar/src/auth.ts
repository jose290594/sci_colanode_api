import {
  BridgeSession,
  ensureAccountSlot,
  getApp,
  getSession,
  setSession,
} from './app.js';

function serverDomainFromUrl(url: string): string {
  const parsed = new URL(url);
  return parsed.host;
}

export async function ensureAuth(options: {
  bridgeAccountId: string;
  serverUrl: string;
  email: string;
  password: string;
  workspaceId?: string;
  forceLogin?: boolean;
}): Promise<BridgeSession> {
  await ensureAccountSlot(options.bridgeAccountId);
  const app = getApp(options.bridgeAccountId);
  const domain = serverDomainFromUrl(options.serverUrl);

  const existing = getSession(options.bridgeAccountId);
  if (
    existing &&
    !options.forceLogin &&
    (!options.workspaceId || existing.workspaceId === options.workspaceId)
  ) {
    return existing;
  }

  if (app.getAccounts().length > 0 && !options.forceLogin) {
    const workspaces = await app.mediator.executeQuery({
      type: 'workspace.list',
    });

    if (workspaces.length > 0) {
      const preferred =
        (options.workspaceId
          ? workspaces.find((w) => w.workspaceId === options.workspaceId)
          : undefined) ?? workspaces[0]!;

      const session: BridgeSession = {
        accountId: preferred.accountId,
        userId: preferred.userId,
        workspaceId: preferred.workspaceId,
        serverDomain: domain,
      };
      setSession(options.bridgeAccountId, session);
      return session;
    }
  }

  if (!app.getServer(domain)) {
    const createResult = await app.mediator.executeMutation({
      type: 'server.create',
      url: options.serverUrl,
    });
    if (!createResult.success) {
      throw new Error(
        `server.create failed: ${createResult.error.code} ${createResult.error.message}`
      );
    }
  }

  const loginResult = await app.mediator.executeMutation({
    type: 'email.login',
    server: domain,
    email: options.email,
    password: options.password,
  });

  if (!loginResult.success) {
    throw new Error(
      `email.login failed: ${loginResult.error.code} ${loginResult.error.message}`
    );
  }

  if (loginResult.output.type === 'verify') {
    throw new Error(
      'email.login requires email verification; use a pre-verified service account'
    );
  }

  const workspaces = await app.mediator.executeQuery({
    type: 'workspace.list',
  });

  if (workspaces.length === 0) {
    throw new Error('Login succeeded but no workspaces are available');
  }

  const preferred =
    (options.workspaceId
      ? workspaces.find((w) => w.workspaceId === options.workspaceId)
      : undefined) ?? workspaces[0]!;

  const session: BridgeSession = {
    accountId: preferred.accountId,
    userId: preferred.userId,
    workspaceId: preferred.workspaceId,
    serverDomain: domain,
  };
  setSession(options.bridgeAccountId, session);
  return session;
}
