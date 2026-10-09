export interface TokenStorage {
  read(): Promise<string | null>;
  write(token: string): Promise<void>;
  clear(): Promise<void>;
}
export function createVolatileTokenStorage(): TokenStorage {
  let value: string | null = null;
  return {
    read: async () => value,
    write: async (token) => {
      value = token;
    },
    clear: async () => {
      value = null;
    },
  };
}
