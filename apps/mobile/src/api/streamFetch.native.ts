import { fetch as expoFetch } from 'expo/fetch';
import { nativeSseObserver } from '../diagnostics/nativeSseObserver';

// Use the installed SDK's native incremental body. No extra native library.
export const streamFetch: typeof fetch = async (input, init) => {
  const request = new Request(input, init);
  const ticket = nativeSseObserver.begin();
  const response = await expoFetch(request.url, {
    method: request.method,
    headers: Object.fromEntries(request.headers.entries()),
    body: request.method === 'GET' ? undefined : await request.text(),
    signal: request.signal,
    credentials: 'omit',
    redirect: 'error',
  });
  nativeSseObserver.bind(response as Response, ticket);
  return response as Response;
};
