// Doctor 1.20.4 still reads the legacy host. Both URLs are official Expo APIs.
// This preload is used only by Doctor, never by the Mobile application.
const originalFetch = globalThis.fetch;
globalThis.fetch = async (input, init) => {
  try {
    return await originalFetch(input, init);
  } catch (error) {
    const url = new URL(typeof input === 'string' || input instanceof URL ? input : input.url);
    const method = init?.method ?? (input instanceof Request ? input.method : 'GET');
    const headers = new Headers(init?.headers ?? (input instanceof Request ? input.headers : {}));
    const originalHeaders = new Headers(input instanceof Request ? input.headers : {});
    const networkCodes = new Set([
      'ENOTFOUND', 'EAI_AGAIN', 'ECONNRESET', 'ECONNREFUSED', 'ETIMEDOUT',
      'UND_ERR_CONNECT_TIMEOUT', 'UND_ERR_SOCKET',
    ]);
    if (
      !(error instanceof TypeError) || !networkCodes.has(error.cause?.code) || method !== 'GET' ||
      url.origin !== 'https://exp.host' || url.search || url.hash ||
      url.username || url.password || init?.dispatcher || init?.agent ||
      init?.credentials === 'include' ||
      !/^\/--\/api\/v2\/project\/configuration\/schema\/\d+\.\d+\.\d+$/.test(url.pathname) ||
      headers.has('authorization') || headers.has('cookie') ||
      originalHeaders.has('authorization') || originalHeaders.has('cookie')
    ) throw error;
    const alternate = new URL(url.pathname.replace('/--/api/', '/'), 'https://api.expo.dev');
    process.stderr.write('Expo Doctor: legacy schema network failed; reading the same SDK schema from official api.expo.dev.\n');
    // Return the real Response. Doctor still validates its schema; errors propagate.
    return originalFetch(alternate, init);
  }
};
