import path from 'path';
import { fileURLToPath } from 'url';

import { PathService } from '@colanode/client/services';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export class NodePathService implements PathService {
  private readonly nativePath = path;
  private readonly appPath: string;
  private readonly assetsPath: string;

  constructor(dataDir: string, assetsDir?: string) {
    this.appPath = path.resolve(dataDir);
    this.assetsPath = assetsDir
      ? path.resolve(assetsDir)
      : path.resolve(
          __dirname,
          '../../../../vendor/colanode/assets'
        );
  }

  public get app(): string {
    return this.appPath;
  }

  public get appDatabase(): string {
    return this.nativePath.join(this.appPath, 'app.db');
  }

  public get temp(): string {
    return this.nativePath.join(this.appPath, 'temp');
  }

  public get avatars(): string {
    return this.nativePath.join(this.appPath, 'avatars');
  }

  public tempFile(name: string): string {
    return this.nativePath.join(this.appPath, 'temp', name);
  }

  public avatar(avatarId: string): string {
    return this.nativePath.join(this.avatars, `${avatarId}.jpeg`);
  }

  public workspace(userId: string): string {
    return this.nativePath.join(this.appPath, 'workspaces', userId);
  }

  public workspaceDatabase(userId: string): string {
    return this.nativePath.join(this.workspace(userId), 'workspace.db');
  }

  public workspaceFiles(userId: string): string {
    return this.nativePath.join(this.workspace(userId), 'files');
  }

  public workspaceFile(
    userId: string,
    fileId: string,
    extension: string
  ): string {
    return this.nativePath.join(
      this.workspaceFiles(userId),
      `${fileId}${extension}`
    );
  }

  public dirname(dir: string): string {
    return this.nativePath.dirname(dir);
  }

  public filename(file: string): string {
    return this.nativePath.basename(file, this.nativePath.extname(file));
  }

  public extension(name: string): string {
    return this.nativePath.extname(name);
  }

  public get assets(): string {
    return this.assetsPath;
  }

  public get fonts(): string {
    return this.nativePath.join(this.assetsPath, 'fonts');
  }

  public get emojisDatabase(): string {
    return this.nativePath.join(this.assetsPath, 'emojis', 'emojis.db');
  }

  public get iconsDatabase(): string {
    return this.nativePath.join(this.assetsPath, 'icons', 'icons.db');
  }

  public font(name: string): string {
    return this.nativePath.join(this.fonts, name);
  }
}
