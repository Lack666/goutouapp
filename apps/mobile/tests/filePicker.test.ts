import { pickImportFile as nativePicker } from '../src/data/filePicker.native';
import * as DocumentPicker from 'expo-document-picker';
import { Platform } from 'react-native';
import { file } from './importSupport';
const { pickImportFile } = jest.requireActual(
  '../src/data/filePicker.ts',
) as typeof import('../src/data/filePicker');
jest.mock('expo-document-picker', () => ({ getDocumentAsync: jest.fn() }));
const mockDelete = jest.fn();
const mockCopy = jest.fn<Promise<void>, [string, string]>(async () => undefined);
jest.mock('expo-crypto', () => ({ randomUUID: () => 'synthetic-cache-id' }));
let mockExists = true;
jest.mock('expo-file-system', () => ({
  Paths: { cache: { uri: 'file:///app/cache/' } },
  File: class extends Blob {
    readonly uri: string;
    constructor(...paths: (string | { uri: string })[]) {
      super(['native synthetic']);
      this.uri = paths.map((p) => (typeof p === 'string' ? p : p.uri)).join('/');
    }
    get exists() {
      return mockExists;
    }
    delete() {
      mockDelete(this.uri);
    }
    copy(destination: { uri: string }) {
      return mockCopy(this.uri, destination.uri);
    }
  },
}));
const pick = jest.mocked(DocumentPicker.getDocumentAsync);
beforeEach(() => {
  Object.defineProperty(Platform, 'OS', { value: 'ios', configurable: true });
  pick.mockReset();
  mockDelete.mockReset();
  mockCopy.mockClear();
  mockExists = true;
});
it('Web requests no base64, keeps actual File bytes/name/type/size, and needs explicit upload', async () => {
  const binary = await file().binary();
  const webFile = new File([binary], 'anonymous.md', { type: 'text/markdown' });
  pick.mockResolvedValue({
    canceled: false,
    assets: [
      {
        uri: 'blob:synthetic',
        lastModified: 0,
        name: webFile.name,
        file: webFile,
        size: webFile.size,
        mimeType: webFile.type,
      },
    ],
  });
  const selected = await pickImportFile();
  expect(await selected?.binary()).toBe(webFile);
  expect(selected?.name).toBe('anonymous.md');
  expect(pick).toHaveBeenCalledWith({
    type: '*/*',
    multiple: false,
    copyToCacheDirectory: true,
    base64: false,
  });
});
it('native cancellation returns no file', async () => {
  pick.mockResolvedValue({ canceled: true, assets: null });
  expect(await nativePicker()).toBeNull();
});
it('native uses the granted provider cache copy as binary and deletes only that copy', async () => {
  pick.mockResolvedValue({
    canceled: false,
    assets: [
      {
        uri: 'file:///app/cache/DocumentPicker/anonymous.md',
        lastModified: 0,
        name: 'anonymous.md',
        mimeType: 'text/markdown',
      },
    ],
  });
  const selected = await nativePicker();
  expect(await (await selected!.binary()).text()).toBe('native synthetic');
  expect(selected?.size).toBe(16);
  selected?.release();
  expect(mockDelete).toHaveBeenCalledTimes(1);
});
it('unconverted content URI fails closed instead of uploading its string or deleting the original', async () => {
  pick.mockResolvedValue({
    canceled: false,
    assets: [{ uri: 'content://provider/anonymous.md', lastModified: 0, name: 'anonymous.md' }],
  });
  await expect(nativePicker()).rejects.toThrow('无法读取');
  expect(mockDelete).not.toHaveBeenCalled();
});
it('Android copies the user-granted content URI into owned cache and uploads only the copied binary', async () => {
  Object.defineProperty(Platform, 'OS', { value: 'android', configurable: true });
  const uri = 'content://provider/document/anonymous.md';
  pick.mockResolvedValue({
    canceled: false,
    assets: [{ uri, name: 'anonymous.md', lastModified: 0 }],
  });
  const selected = await nativePicker();
  expect(pick).toHaveBeenCalledWith(expect.objectContaining({ copyToCacheDirectory: false }));
  expect(mockCopy).toHaveBeenCalledWith(uri, expect.stringContaining('/app/cache/'));
  expect(await (await selected!.binary()).text()).toBe('native synthetic');
  selected!.release();
  expect(mockDelete).toHaveBeenCalledWith(expect.stringContaining('/app/cache/'));
  expect(mockDelete).not.toHaveBeenCalledWith(uri);
});
it('Android grant/read failure does not copy, upload or delete the provider source', async () => {
  Object.defineProperty(Platform, 'OS', { value: 'android', configurable: true });
  pick.mockResolvedValue({
    canceled: false,
    assets: [
      { uri: 'content://provider/document/anonymous.md', name: 'anonymous.md', lastModified: 0 },
    ],
  });
  mockExists = false;
  await expect(nativePicker()).rejects.toThrow('无法读取');
  expect(mockCopy).not.toHaveBeenCalled();
  expect(mockDelete).not.toHaveBeenCalled();
});
it('Expo Go host DocumentPicker cache is copied into owned Paths.cache; release never deletes the host copy', async () => {
  const uri = 'file:///host/cache/DocumentPicker/copied.md';
  pick.mockResolvedValue({
    canceled: false,
    assets: [{ uri, name: 'anonymous.md', lastModified: 0 }],
  });
  const selected = await nativePicker();
  expect(mockCopy).toHaveBeenCalledWith(uri, expect.stringContaining('/app/cache/'));
  expect(await (await selected!.binary()).text()).toBe('native synthetic');
  selected!.release();
  expect(mockDelete).toHaveBeenCalledWith(expect.stringContaining('/app/cache/'));
  expect(mockDelete).not.toHaveBeenCalledWith(uri);
});
it('an outside provider file path is not trusted as a picker cache copy', async () => {
  pick.mockResolvedValue({
    canceled: false,
    assets: [
      { uri: 'file:///storage/Download/anonymous.md', name: 'anonymous.md', lastModified: 0 },
    ],
  });
  await expect(nativePicker()).rejects.toThrow('无法读取');
  expect(mockCopy).not.toHaveBeenCalled();
  expect(mockDelete).not.toHaveBeenCalled();
});
it('a failed host-cache copy releases only its partial owned file', async () => {
  const uri = 'file:///host/cache/DocumentPicker/copied.md';
  pick.mockResolvedValue({
    canceled: false,
    assets: [{ uri, name: 'anonymous.md', lastModified: 0 }],
  });
  mockCopy.mockRejectedValueOnce(new Error('synthetic permission failure'));
  await expect(nativePicker()).rejects.toThrow('无法读取');
  expect(mockDelete).toHaveBeenCalledWith(expect.stringContaining('/app/cache/'));
  expect(mockDelete).not.toHaveBeenCalledWith(uri);
});
it('native cache permission/eviction failure after selecting is visible before upload', async () => {
  pick.mockResolvedValue({
    canceled: false,
    assets: [
      {
        uri: 'file:///app/cache/DocumentPicker/anonymous.md',
        lastModified: 0,
        name: 'anonymous.md',
      },
    ],
  });
  const selected = await nativePicker();
  mockExists = false;
  await expect(selected!.binary()).rejects.toThrow('无法读取');
});
it('Web asset missing actual File is rejected instead of converting a URI into source text', async () => {
  pick.mockResolvedValue({
    canceled: false,
    assets: [{ uri: 'blob:synthetic', lastModified: 0, name: 'anonymous.md' }],
  });
  await expect(pickImportFile()).rejects.toThrow('无法读取');
});
