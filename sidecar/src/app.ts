import path from 'path';

import { AppMeta, AppService } from '@colanode/client/services';

import { NodeFileSystem } from './platform/file-system.js';
import { NodeKyselyService } from './platform/kysely-service.js';
import { NodePathService } from './platform/path-service.js';

export type BridgeSession = {
  accountId: string;
  userId: string;
  workspaceId: string;
  serverDomain: string;
};

export type AccountSlot = {
  bridgeAccountId: string;
  app: AppService;
  session: BridgeSession | null;
};

const slots = new Map<string, AccountSlot>();
let assetsDirGlobal: string | undefined;
let rootDataDirGlobal = '';

export function configurePool(options: { rootDataDir: string; assetsDir?: string }): void {
  rootDataDirGlobal = options.rootDataDir;
  assetsDirGlobal = options.assetsDir;
}

export function getSlot(bridgeAccountId: string): AccountSlot {
  const slot = slots.get(bridgeAccountId);
  if (!slot) {
    throw new Error(`Account slot not initialized: ${bridgeAccountId}`);
  }
  return slot;
}

export function getApp(bridgeAccountId: string): AppService {
  return getSlot(bridgeAccountId).app;
}

export function getSession(bridgeAccountId: string): BridgeSession | null {
  return getSlot(bridgeAccountId).session;
}

export function setSession(
  bridgeAccountId: string,
  next: BridgeSession | null
): void {
  const slot = getSlot(bridgeAccountId);
  slot.session = next;
}

export function listSlots(): Array<{ bridgeAccountId: string; session: BridgeSession | null }> {
  return [...slots.entries()].map(([bridgeAccountId, slot]) => ({
    bridgeAccountId,
    session: slot.session,
  }));
}

export async function ensureAccountSlot(bridgeAccountId: string): Promise<AccountSlot> {
  const existing = slots.get(bridgeAccountId);
  if (existing) {
    return existing;
  }
  if (!rootDataDirGlobal) {
    throw new Error('Account pool not configured');
  }

  const dataDir = path.join(rootDataDirGlobal, 'accounts', bridgeAccountId);
  const meta: AppMeta = {
    type: 'desktop',
    platform: process.platform,
  };

  const fs = new NodeFileSystem();
  const pathService = new NodePathService(dataDir, assetsDirGlobal);
  const kysely = new NodeKyselyService();

  await fs.makeDirectory(dataDir);
  await fs.makeDirectory(pathService.avatars);
  await fs.makeDirectory(pathService.temp);

  const app = new AppService(meta, fs, kysely, pathService);
  await app.init();

  const slot: AccountSlot = {
    bridgeAccountId,
    app,
    session: null,
  };
  slots.set(bridgeAccountId, slot);
  return slot;
}
