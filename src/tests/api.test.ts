import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { addyApiRequest, RateLimitError } from "../api/index.js";

interface XhrState {
  status: number;
  text: string;
  retryAfter: string | null;
}

let xhrState: XhrState;
let lastXhr: {
  open: ReturnType<typeof vi.fn>;
  setRequestHeader: ReturnType<typeof vi.fn>;
};

function setupXHRMock() {
  class MockXHR {
    open = vi.fn();
    setRequestHeader = vi.fn();
    status = 0;
    responseText = "";
    onload: (() => void) | null = null;
    onerror: ((e: Event) => void) | null = null;

    getResponseHeader = vi.fn((name: string) =>
      name === "retry-after" ? xhrState.retryAfter : null,
    );

    send = vi.fn().mockImplementation(() => {
      this.status = xhrState.status;
      this.responseText = xhrState.text;
      queueMicrotask(() => this.onload?.());
    });

    constructor() {
      // eslint-disable-next-line @typescript-eslint/no-this-alias
      lastXhr = this;
    }
  }
  vi.stubGlobal("XMLHttpRequest", MockXHR);
}

beforeEach(() => {
  xhrState = { status: 200, text: '{"ok":true}', retryAfter: null };
  setupXHRMock();
  vi.mocked(messenger.storage.local.get).mockResolvedValue({
    options: { apiKey: "test-key", hostUrl: "http://mock.test" },
  });
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.clearAllMocks();
});

describe("addyApiRequest", () => {
  it("builds the correct URL with query params", async () => {
    await addyApiRequest("GET", "aliases", { "filter[active]": "true" });
    const [, url] = lastXhr.open.mock.calls[0] as [string, string];
    expect(url).toBe("http://mock.test/api/v1/aliases?filter%5Bactive%5D=true");
  });

  it("sends Authorization: Bearer header", async () => {
    await addyApiRequest("GET", "aliases");
    const headers = Object.fromEntries(
      lastXhr.setRequestHeader.mock.calls as [string, string][],
    );
    expect(headers["Authorization"]).toBe("Bearer test-key");
    expect(headers["X-Requested-With"]).toBe("XMLHttpRequest");
  });

  it("uses default host when hostUrl is not set", async () => {
    vi.mocked(messenger.storage.local.get).mockResolvedValue({
      options: { apiKey: "test-key" },
    });
    await addyApiRequest("GET", "domain-options");
    const [, url] = lastXhr.open.mock.calls[0] as [string, string];
    expect(url).toContain("https://app.addy.io");
  });

  it("returns parsed JSON on 2xx", async () => {
    xhrState = { status: 200, text: '{"data":[1,2,3]}', retryAfter: null };
    const result = await addyApiRequest<{ data: number[] }>("GET", "aliases");
    expect(result.data).toEqual([1, 2, 3]);
  });

  it("throws RateLimitError on 429", async () => {
    xhrState = { status: 429, text: "", retryAfter: "30" };
    await expect(addyApiRequest("GET", "aliases")).rejects.toBeInstanceOf(
      RateLimitError,
    );
  });

  it("RateLimitError carries retryAfterSeconds", async () => {
    xhrState = { status: 429, text: "", retryAfter: "42" };
    await expect(addyApiRequest("GET", "aliases")).rejects.toMatchObject({
      retryAfterSeconds: 42,
    });
  });

  it("uses 60 as default retry-after when header is absent", async () => {
    xhrState = { status: 429, text: "", retryAfter: null };
    await expect(addyApiRequest("GET", "aliases")).rejects.toMatchObject({
      retryAfterSeconds: 60,
    });
  });

  it("throws Error on 4xx non-429", async () => {
    xhrState = { status: 404, text: "Not found", retryAfter: null };
    await expect(addyApiRequest("GET", "aliases")).rejects.toThrow("HTTP 404");
  });

  it("throws Error on 5xx", async () => {
    xhrState = { status: 500, text: "Server error", retryAfter: null };
    await expect(addyApiRequest("GET", "aliases")).rejects.toThrow("HTTP 500");
  });

  it("throws when no API key is configured", async () => {
    vi.mocked(messenger.storage.local.get).mockResolvedValue({
      options: { hostUrl: "http://mock.test" },
    });
    await expect(addyApiRequest("GET", "aliases")).rejects.toThrow(
      "No API key configured",
    );
  });
});
