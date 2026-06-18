// XHR-based because Thunderbird extensions require it for cross-origin requests.
function xhrRequest(
  method: string,
  url: string,
  headers: Record<string, string>,
  body: string | null,
): Promise<{ status: number; text: string; retryAfter: number | null }> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open(method, url);
    for (const [key, val] of Object.entries(headers))
      xhr.setRequestHeader(key, val);
    xhr.onload = () => {
      const raw = xhr.getResponseHeader("retry-after");
      const retryAfter = raw !== null ? parseInt(raw, 10) : null;
      resolve({ status: xhr.status, text: xhr.responseText, retryAfter });
    };
    xhr.onerror = (e) => reject(e);
    xhr.send(body);
  });
}

export class RateLimitError extends Error {
  constructor(public readonly retryAfterSeconds: number) {
    super(`Rate limited; retry after ${retryAfterSeconds}s`);
    this.name = "RateLimitError";
  }
}

export async function addyApiRequest<T = unknown>(
  method: string,
  endpoint: string,
  params?: Record<string, string> | null,
  body?: unknown,
): Promise<T> {
  const storage = await messenger.storage.local.get({ options: {} });
  const options = (storage.options ?? {}) as {
    hostUrl?: string | null;
    apiKey?: string;
  };
  const hostUrl = options.hostUrl || "https://app.addy.io";
  const apiKey = options.apiKey;
  if (!apiKey) throw new Error("No API key configured");

  let url = `${hostUrl}/api/v1/${endpoint}`;
  if (params) url += `?${new URLSearchParams(params)}`;

  const { status, text, retryAfter } = await xhrRequest(
    method,
    url,
    {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
      "X-Requested-With": "XMLHttpRequest",
    },
    body ? JSON.stringify(body) : null,
  );

  if (status === 429) throw new RateLimitError(retryAfter ?? 60);
  if (status < 200 || status >= 300) throw new Error(`HTTP ${status}: ${text}`);

  return JSON.parse(text) as T;
}
