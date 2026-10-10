import * as DocumentPicker from 'expo-document-picker';
import { ApiError } from '../api/errors';
import type { SelectedImportFile } from '../contracts/connectedImport';

export async function pickImportFile(): Promise<SelectedImportFile | null> {
  const result = await DocumentPicker.getDocumentAsync({
    type: '*/*',
    multiple: false,
    copyToCacheDirectory: true,
    base64: false,
  });
  if (result.canceled) return null;
  const asset = result.assets[0];
  if (!asset?.file) throw new ApiError('file_unreadable');
  const file = asset.file;
  return {
    name: asset.name,
    size: file.size,
    mimeType: asset.mimeType ?? file.type ?? 'application/octet-stream',
    binary: async () => file,
    release: () => {
      /* Web File is released with the controller reference. */
    },
  };
}
