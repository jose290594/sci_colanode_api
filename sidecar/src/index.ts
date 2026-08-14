import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';

import { serve } from '@hono/node-server';
import { Hono } from 'hono';
import { generateFractionalIndex, generateId, IdType } from '@colanode/core';

import {
  configurePool,
  ensureAccountSlot,
  getApp,
  getSession,
  listSlots,
} from './app.js';
import { ensureAuth } from './auth.js';
import { setDocumentContent } from './document.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, '../..');
dotenv.config({ path: path.join(repoRoot, '.env') });
dotenv.config();

const PORT = Number(process.env.SIDECAR_PORT ?? 3921);
const HOST = process.env.SIDECAR_HOST ?? '127.0.0.1';
const DATA_DIR =
  process.env.COLANODE_DATA_DIR ?? path.join(repoRoot, 'data');
const ASSETS_DIR =
  process.env.COLANODE_ASSETS_DIR ??
  path.join(repoRoot, 'vendor', 'colanode', 'assets');

type RpcBody = {
  accountId?: string;
  op:
    | 'mutation'
    | 'query'
    | 'document.set_content'
    | 'generate_id'
    | 'generate_index'
    | 'session.get'
    | 'file.retry_pending';
  input?: Record<string, unknown>;
};

const app = new Hono();

app.get('/health', (c) => {
  return c.json({
    ok: true,
    accounts: listSlots(),
  });
});

function normalizeServerUrl(raw: string): string {
  const trimmed = raw.trim().replace(/\/+$/, '');
  try {
    new URL(trimmed);
    return trimmed;
  } catch {
    return trimmed;
  }
}

function requireAccountId(raw: unknown): string {
  const id = typeof raw === 'string' ? raw.trim() : '';
  if (!id) {
    throw Object.assign(new Error('accountId is required'), { code: 'account_required' });
  }
  return id;
}

app.post('/auth/ensure', async (c) => {
  try {
    const body = (await c.req.json().catch(() => ({}))) as {
      accountId?: string;
      forceLogin?: boolean;
      serverUrl?: string;
      email?: string;
      password?: string;
      workspaceId?: string;
    };

    const bridgeAccountId = requireAccountId(body.accountId);
    const serverUrlRaw = body.serverUrl || '';
    const email = body.email || '';
    const password = body.password || '';
    const workspaceId = body.workspaceId || undefined;

    if (!serverUrlRaw || !email || !password) {
      return c.json(
        {
          ok: false,
          error: {
            code: 'config_missing',
            message: 'serverUrl, email and password are required',
          },
        },
        400
      );
    }

    const session = await ensureAuth({
      bridgeAccountId,
      serverUrl: normalizeServerUrl(serverUrlRaw),
      email,
      password,
      workspaceId,
      forceLogin: body.forceLogin === true,
    });

    return c.json({ ok: true, session });
  } catch (error) {
    const code =
      error && typeof error === 'object' && 'code' in error
        ? String((error as { code: string }).code)
        : 'auth_failed';
    return c.json(
      {
        ok: false,
        error: {
          code,
          message: error instanceof Error ? error.message : String(error),
        },
      },
      code === 'account_required' || code === 'config_missing' ? 400 : 500
    );
  }
});

app.post('/rpc', async (c) => {
  try {
    const body = (await c.req.json()) as RpcBody;
    const bridgeAccountId = requireAccountId(
      body.accountId || c.req.header('x-account-id')
    );
    await ensureAccountSlot(bridgeAccountId);
    const colanode = getApp(bridgeAccountId);

    if (body.op === 'session.get') {
      return c.json({ ok: true, result: getSession(bridgeAccountId) });
    }

    if (body.op === 'file.retry_pending') {
      const session = getSession(bridgeAccountId);
      if (!session) {
        return c.json(
          {
            ok: false,
            error: { code: 'no_session', message: 'Not authenticated' },
          },
          401
        );
      }
      const workspace = colanode.getWorkspace(session.userId);
      if (!workspace) {
        return c.json(
          {
            ok: false,
            error: { code: 'no_workspace', message: 'Workspace not loaded' },
          },
          400
        );
      }
      const uploads = await workspace.database
        .selectFrom('uploads')
        .selectAll()
        .execute();
      const queued: Array<Record<string, unknown>> = [];
      for (const upload of uploads) {
        if (upload.status === 2) {
          continue;
        }
        await colanode.jobs.addJob({
          type: 'file.upload',
          userId: session.userId,
          fileId: upload.file_id,
        });
        queued.push({
          fileId: upload.file_id,
          status: upload.status,
          error: upload.error_message,
          retries: upload.retries,
        });
      }
      return c.json({ ok: true, result: queued });
    }

    if (body.op === 'generate_id') {
      const typeName = String(body.input?.type ?? 'Node');
      const idType =
        (IdType as Record<string, IdType>)[typeName] ?? IdType.Node;
      return c.json({ ok: true, result: generateId(idType) });
    }

    if (body.op === 'generate_index') {
      const previous =
        body.input?.previous === undefined || body.input?.previous === null
          ? null
          : String(body.input.previous);
      const next =
        body.input?.next === undefined || body.input?.next === null
          ? null
          : String(body.input.next);
      return c.json({
        ok: true,
        result: generateFractionalIndex(previous, next),
      });
    }

    if (body.op === 'document.set_content') {
      const userId = String(body.input?.userId ?? '');
      const documentId = String(body.input?.documentId ?? '');
      const content = body.input?.content;
      if (!userId || !documentId || content === undefined) {
        return c.json(
          {
            ok: false,
            error: {
              code: 'invalid_input',
              message: 'userId, documentId and content are required',
            },
          },
          400
        );
      }
      const result = await setDocumentContent({
        bridgeAccountId,
        userId,
        documentId,
        content: content as string | Record<string, unknown>,
      });
      return c.json({ ok: true, result });
    }

    if (body.op === 'mutation') {
      if (!body.input || typeof body.input.type !== 'string') {
        return c.json(
          {
            ok: false,
            error: {
              code: 'invalid_input',
              message: 'mutation input with type is required',
            },
          },
          400
        );
      }
      const result = await colanode.mediator.executeMutation(body.input as never);
      return c.json({ ok: true, result });
    }

    if (body.op === 'query') {
      if (!body.input || typeof body.input.type !== 'string') {
        return c.json(
          {
            ok: false,
            error: {
              code: 'invalid_input',
              message: 'query input with type is required',
            },
          },
          400
        );
      }
      const result = await colanode.mediator.executeQuery(body.input as never);
      return c.json({ ok: true, result });
    }

    return c.json(
      {
        ok: false,
        error: { code: 'unknown_op', message: `Unknown op: ${String(body.op)}` },
      },
      400
    );
  } catch (error) {
    const code =
      error && typeof error === 'object' && 'code' in error
        ? String((error as { code: string }).code)
        : 'rpc_error';
    return c.json(
      {
        ok: false,
        error: {
          code,
          message: error instanceof Error ? error.message : String(error),
        },
      },
      code === 'account_required' ? 400 : 500
    );
  }
});

async function main() {
  configurePool({
    rootDataDir: DATA_DIR,
    assetsDir: ASSETS_DIR,
  });

  serve({ fetch: app.fetch, port: PORT, hostname: HOST }, (info) => {
    console.log(
      JSON.stringify({
        event: 'sidecar_listening',
        host: HOST,
        port: info.port,
        dataDir: DATA_DIR,
        multiAccount: true,
      })
    );
  });
}

main().catch((error) => {
  console.error('Sidecar failed to start', error);
  process.exit(1);
});
