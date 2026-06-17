// XHR-based because Thunderbird extensions require it for cross-origin requests.
function xhrRequest(
  method: string,
  url: string,
  headers: Record<string, string>,
  body: string | null,
): Promise<string> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open(method, url);
    for (const [key, val] of Object.entries(headers))
      xhr.setRequestHeader(key, val);
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(xhr.responseText);
      } else {
        reject(new Error(`HTTP ${xhr.status}: ${xhr.responseText}`));
      }
    };
    xhr.onerror = (e) => reject(e);
    xhr.send(body);
  });
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

  const raw = await xhrRequest(
    method,
    url,
    {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
      "X-Requested-With": "XMLHttpRequest",
    },
    body ? JSON.stringify(body) : null,
  );
  return JSON.parse(raw) as T;
}
