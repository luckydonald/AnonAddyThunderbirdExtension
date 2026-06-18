import { describe, it, expect } from "vitest";
import { matchingAliasesForEmail } from "../experiment/utils.js";
import aliases from "../../tests/fixtures/aliases.json";

// The experiment function matches aliases whose *email* contains the recipient domain
// as a substring — different from the popup's matchingAliases which uses description.
// Fixtures a6/a7 have email "@relay.example.com" which contains "example.com".
// Fixtures a1-a3 match by description only and should NOT appear here.

describe("matchingAliasesForEmail", () => {
  it("returns aliases whose email contains the recipient domain", () => {
    const result = matchingAliasesForEmail(aliases, "user@example.com");
    const ids = result.map((a) => a.id);
    expect(ids).toContain("a6");
    expect(ids).toContain("a7");
  });

  it("excludes inactive aliases", () => {
    // a8 is inactive and has email containing "example.com" — must be filtered
    const result = matchingAliasesForEmail(aliases, "user@example.com");
    expect(result.find((a) => a.id === "a8")).toBeUndefined();
  });

  it("does NOT match aliases by description", () => {
    // a1/a2/a3 match example.com by description but not by email
    const result = matchingAliasesForEmail(aliases, "user@example.com");
    expect(result.find((a) => a.id === "a1")).toBeUndefined();
    expect(result.find((a) => a.id === "a2")).toBeUndefined();
    expect(result.find((a) => a.id === "a3")).toBeUndefined();
  });

  it("returns empty array for an email with no matching aliases", () => {
    expect(matchingAliasesForEmail(aliases, "user@no-match.io")).toHaveLength(0);
  });

  it("returns empty array for a malformed email (no @)", () => {
    expect(matchingAliasesForEmail(aliases, "notanemail")).toHaveLength(0);
  });

  it("caps results at 20", () => {
    const many = Array.from({ length: 25 }, (_, i) => ({
      id: `x${i}`,
      email: `alias${i}@sub.example.com`,
      active: true,
      description: "",
    }));
    expect(matchingAliasesForEmail(many, "user@example.com")).toHaveLength(20);
  });

  it("handles null/undefined aliases gracefully", () => {
    expect(matchingAliasesForEmail(null, "user@example.com")).toHaveLength(0);
    expect(matchingAliasesForEmail(undefined, "user@example.com")).toHaveLength(
      0,
    );
  });
});
