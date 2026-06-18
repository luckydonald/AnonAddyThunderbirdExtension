import { describe, expect, it } from "vitest";
import { createMenuIconUrls } from "../experiment/menuIcons.js";

function flattenUrls(value: unknown): string[] {
  if (typeof value === "string") return [value];
  if (!value || typeof value !== "object") return [];
  return Object.values(value).flatMap((entry) => flattenUrls(entry));
}

describe("createMenuIconUrls", () => {
  it("uses packaged extension assets instead of CSP-blocked data URLs", () => {
    const urls = flattenUrls(createMenuIconUrls("moz-extension://addon-id/"));

    expect(urls).toContain("moz-extension://addon-id/icon.svg");
    expect(urls).toContain(
      "moz-extension://addon-id/experiment/icons/existing.svg",
    );
    expect(urls).toContain(
      "moz-extension://addon-id/experiment/icons/format-custom.svg",
    );
    expect(urls).toContain(
      "moz-extension://addon-id/experiment/icons/server.svg",
    );
    expect(
      urls.every((url) => url.startsWith("moz-extension://addon-id/")),
    ).toBe(true);
    expect(urls.some((url) => url.startsWith("data:"))).toBe(false);
  });
});
