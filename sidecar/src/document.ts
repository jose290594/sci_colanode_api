import { richTextContentSchema, RichTextContent } from '@colanode/core';
import { encodeState, YDoc } from '@colanode/crdt';
import { generateId, IdType } from '@colanode/core';

import { getApp } from './app.js';

function plainTextToRichText(documentId: string, text: string): RichTextContent {
  const blockId = generateId(IdType.Block);
  return {
    type: 'rich_text',
    blocks: {
      [blockId]: {
        id: blockId,
        type: 'paragraph',
        parentId: documentId,
        content: [{ type: 'text', text }],
        index: 'a0',
      },
    },
  };
}

export async function setDocumentContent(options: {
  bridgeAccountId: string;
  userId: string;
  documentId: string;
  content: RichTextContent | string | Record<string, unknown>;
}): Promise<{ success: boolean }> {
  const app = getApp(options.bridgeAccountId);

  const current = await app.mediator.executeQuery({
    type: 'document.get',
    userId: options.userId,
    documentId: options.documentId,
  });

  const state = await app.mediator.executeQuery({
    type: 'document.state.get',
    userId: options.userId,
    documentId: options.documentId,
  });

  const updates = await app.mediator.executeQuery({
    type: 'document.updates.list',
    userId: options.userId,
    documentId: options.documentId,
  });

  const ydoc = new YDoc(state?.state);
  for (const update of updates ?? []) {
    ydoc.applyUpdate(update.data);
  }

  const nextContent: RichTextContent =
    typeof options.content === 'string'
      ? plainTextToRichText(options.documentId, options.content)
      : (options.content as RichTextContent);

  const parsed = richTextContentSchema.safeParse(nextContent);
  if (!parsed.success) {
    throw new Error(`Invalid rich text content: ${parsed.error.message}`);
  }

  if (!current && !state) {
    const fresh = new YDoc();
    const update = fresh.update(richTextContentSchema, parsed.data);
    if (!update) {
      return { success: true };
    }

    const result = await app.mediator.executeMutation({
      type: 'document.update',
      userId: options.userId,
      documentId: options.documentId,
      update: encodeState(update),
    });

    if (!result.success) {
      throw new Error(
        `document.update failed: ${result.error.code} ${result.error.message}`
      );
    }
    return { success: true };
  }

  const update = ydoc.update(richTextContentSchema, parsed.data);
  if (!update) {
    return { success: true };
  }

  const result = await app.mediator.executeMutation({
    type: 'document.update',
    userId: options.userId,
    documentId: options.documentId,
    update: encodeState(update),
  });

  if (!result.success) {
    throw new Error(
      `document.update failed: ${result.error.code} ${result.error.message}`
    );
  }

  return { success: true };
}
