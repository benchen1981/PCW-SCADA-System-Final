const isBackendServed =
  typeof window !== 'undefined' &&
  window.location.port !== '5173' &&
  !window.location.hostname.includes('vercel.app');

export const API_CONFIG = {
  REST_URL:
    import.meta.env.VITE_API_REST_URL ||
    (typeof window !== 'undefined' ? `${window.location.origin}/api` : 'http://127.0.0.1:8000/api'),
  WS_URL:
    import.meta.env.VITE_API_WS_URL ||
    (typeof window !== 'undefined'
      ? `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/stream`
      : 'ws://127.0.0.1:8000/ws/stream'),
  USE_MOCK:
    import.meta.env.VITE_USE_MOCK === 'true'
      ? true
      : import.meta.env.VITE_USE_MOCK === 'false'
        ? false
        : !isBackendServed,
};
