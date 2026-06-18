import { describe, it, expect } from "vitest";
import { matchingAliasesForEmail } from "../experiment/utils.js";
import aliases from "../../tests/fixtures/aliases.json";

// Core alias-filtering behaviour is tested in alias-search.test.ts.
// These tests verify the wrapper: email → domain extraction and the 20-item cap.

describe("matchingAliasesForEmail", () => {
  it("extracts the domain from the email and returns matching aliases", () => {
    const result = matchingAliasesForEmail(aliases, "user@example.com");
    const ids = result.map((a) => a.id);
    expect(ids).toContain("a1");
    expect(ids).toContain("a2");
    expect(ids).toContain("a3");
  });

  it("excludes inactive aliases", () => {
    const result = matchingAliasesForEmail(aliases, "user@example.com");
    expect(result.find((a) => a.id === "a4")).toBeUndefined();
  });

  it("applies a cap of 20", () => {
    const many = Array.from({ length: 25 }, (_, i) => ({
      id: `x${i}`,
      email: `alias${i}@anon.email`,
      active: true,
      description: `alias for example.com #${i}`,
    }));
    expect(matchingAliasesForEmail(many, "user@example.com")).toHaveLength(20);
  });

  it("returns empty for a malformed email (no @)", () => {
    expect(matchingAliasesForEmail(aliases, "notanemail")).toHaveLength(0);
  });

  it("handles null/undefined aliases gracefully", () => {
    expect(matchingAliasesForEmail(null, "user@example.com")).toHaveLength(0);
    expect(matchingAliasesForEmail(undefined, "user@example.com")).toHaveLength(0);
  });
});
