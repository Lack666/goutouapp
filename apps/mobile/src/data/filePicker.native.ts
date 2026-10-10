import * as DocumentPicker from 'expo-document-picker';
import { File, Paths } from 'expo-file-system';
import { randomUUID } from 'expo-crypto';
import { Platform } from 'react-native';
import { ApiError } from '../api/errors';
import { LOCAL_IMPORT_BYTE_LIMIT, type SelectedImportFile } from '../contracts/connectedImport';

export async function pickImportFile(): Promise<SelectedImportFile | null> {
  const result = await DocumentPicker.getDocumentAsync({
    type: '*/*',
    multiple: false,
    // SDK57's Android picker cache is outside Expo Go's FileSystem scope.
    // Keep the user-granted content URI and immediately copy it ourselves.
    copyToCacheDirectory: Platform.OS !== 'android',
    base64: false,
  });
  if (result.canceled) return null;
  const asset = result.assets[0];
  if (!asset) throw new ApiError('file_unreadable');
  // Read only the picker result under its grant. Upload/release use an owned
  // cache copy, never the Android content provider's original.
  const cachePrefix = Paths.cache.uri.replace(/\/$/, '') + '/';
  let file: File;
  let ownedCopy: File | null = null;
  let size: number;
  try {
    const source = new File(asset.uri);
    if (asset.uri.startsWith(cachePrefix)) ownedCopy = source;
    if (!source.exists) throw new Error();
    size = source.size;
    if (size > LOCAL_IMPORT_BYTE_LIMIT) throw new ApiError('file_too_large');
    if (asset.uri.startsWith(cachePrefix)) file = source;
    else {
      // Copy an Android picker-granted content URI, or a verified native
      // picker cache file, into our own scope. The original is never deleted.
      const uri = new URL(asset.uri);
      if (
        !(Platform.OS === 'android' && uri.protocol === 'content:' && uri.hostname !== '') &&
        !(
          uri.protocol === 'file:' &&
          uri.hostname === '' &&
          /\/(?:cache|Caches)\/DocumentPicker\/[^/]+$/.test(decodeURIComponent(uri.pathname))
        )
      )
        throw new Error();
      file = new File(Paths.cache, `chat-import-${randomUUID()}.md`);
      ownedCopy = file;
      await source.copy(file);
      if (!file.exists || file.size !== size) throw new Error();
    }
  } catch (error) {
    try {
      if (ownedCopy?.exists) ownedCopy.delete();
    } catch {
      /* OS cache cleanup can be unavailable. */
    }
    if (error instanceof ApiError) throw error;
    throw new ApiError('file_unreadable');
  }
  return {
    name: asset.name,
    size,
    mimeType: asset.mimeType ?? 'application/octet-stream',
    binary: async () => {
      try {
        if (!file.exists || file.size !== size) throw new Error();
        return file;
      } catch {
        throw new ApiError('file_unreadable');
      }
    },
    release: () => {
      try {
        if (file.exists) file.delete();
      } catch {
        /* OS cache eviction may already have occurred. */
      }
    },
  };
}
