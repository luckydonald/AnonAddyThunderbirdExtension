import { describe, it, expect } from "vitest";
import { matchingAliasesForEmail } from "../experiment/utils.js";
import aliases from "../../tests/fixtures/aliases.json";

// matchingAliasesForEmail now matches by *description* (same as the popup's
// matchingAliases) so both UI surfaces — the toolbar popup and the right-click
// chip menu — show identical alias candidates.
//
// Fixture breakdown for "user@example.com":
//   a1 shop@anonaddy.me        active, description "Shopping alias for example.com"     → match
//   a2 news@anonaddy.me        active, description "Newsletter alias for example.com"   → match
//   a3 work@anon.email         active, description "Work alias for example.com"         → match
//   a4 old@anonaddy.me         INACTIVE, description "Old inactive alias for example.com" → filtered
//   a5 other@anonaddy.me       active, description "Unrelated alias for other-site.org" → no match
//   a6 relay1@relay.example.com active, description ""                                 → no match
//   a7 relay2@relay.example.com active, description ""                                 → no match
//   a8 old-relay@relay.example.com INACTIVE, description ""                            → filtered

describe("matchingAliasesForEmail", () => {
  it("returns aliases whose description contains the recipient domain", () => {
    const result = matchingAliasesForEmail(aliases, "user@example.com");
    const ids = result.map((a) => a.id);
    expect(ids).toContain("a1");
    expect(ids).toContain("a2");
    expect(ids).toContain("a3");
  });

  it("excludes inactive aliases", () => {
    // a4 is inactive but has a description matching example.com
    const result = matchingAliasesForEmail(aliases, "user@example.com");
    expect(result.find((a) => a.id === "a4")).toBeUndefined();
  });

  it("does NOT match aliases whose email happens to contain the domain", () => {
    // a6/a7 have '@relay.example.com' but empty descriptions — must not appear
    const result = matchingAliasesForEmail(aliases, "user@example.com");
    expect(result.find((a) => a.id === "a6")).toBeUndefined();
    expect(result.find((a) => a.id === "a7")).toBeUndefined();
  });

  it("excludes aliases with non-matching descriptions", () => {
    // a5 is active but describes other-site.org, not example.com
    const result = matchingAliasesForEmail(aliases, "user@example.com");
    expect(result.find((a) => a.id === "a5")).toBeUndefined();
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
      email: `alias${i}@anon.email`,
      active: true,
      description: `alias for example.com #${i}`,
    }));
    expect(matchingAliasesForEmail(many, "user@example.com")).toHaveLength(20);
  });

  it("handles null/undefined aliases gracefully", () => {
    expect(matchingAliasesForEmail(null, "user@example.com")).toHaveLength(0);
    expect(matchingAliasesForEmail(undefined, "user@example.com")).toHaveLength(0);
  });
});
