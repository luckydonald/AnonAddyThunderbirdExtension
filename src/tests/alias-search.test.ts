import { describe, it, expect } from "vitest";
import { aliasesForDomain } from "../shared/aliasSearch.js";
import type { Alias } from "../api/types.js";
import aliases from "../../tests/fixtures/aliases.json";

const fixtureAliases = aliases as Alias[];

describe("aliasesForDomain", () => {
  it("returns active aliases whose description contains the domain", () => {
    const result = aliasesForDomain(fixtureAliases, "example.com");
    const ids = result.map((a) => a.id);
    expect(ids).toContain("a1"); // "Shopping alias for example.com"
    expect(ids).toContain("a2"); // "Newsletter alias for example.com"
    expect(ids).toContain("a3"); // "Work alias for example.com"
  });

  it("excludes inactive aliases", () => {
    const result = aliasesForDomain(fixtureAliases, "example.com");
    expect(result.find((a) => a.id === "a4")).toBeUndefined(); // inactive
  });

  it("excludes aliases with non-matching descriptions", () => {
    const result = aliasesForDomain(fixtureAliases, "example.com");
    expect(result.find((a) => a.id === "a5")).toBeUndefined(); // other-site.org
  });

  it("does NOT match on alias email, only description", () => {
    // a6/a7 live at relay.example.com but have empty descriptions
    const result = aliasesForDomain(fixtureAliases, "example.com");
    expect(result.find((a) => a.id === "a6")).toBeUndefined();
    expect(result.find((a) => a.id === "a7")).toBeUndefined();
  });

  it("is case-insensitive on the domain argument", () => {
    const result = aliasesForDomain(fixtureAliases, "EXAMPLE.COM");
    expect(result.map((a) => a.id)).toContain("a1");
  });

  it("respects the limit parameter (default 10)", () => {
    const many: Alias[] = Array.from({ length: 15 }, (_, i) => ({
      id: `m${i}`,
      local_part: `a${i}`,
      domain: "anon.email",
      email: `a${i}@anon.email`,
      active: true,
      description: `alias for example.com #${i}`,
    }));
    expect(aliasesForDomain(many, "example.com")).toHaveLength(10);
  });

  it("respects an explicit limit", () => {
    const many: Alias[] = Array.from({ length: 25 }, (_, i) => ({
      id: `m${i}`,
      local_part: `a${i}`,
      domain: "anon.email",
      email: `a${i}@anon.email`,
      active: true,
      description: `alias for example.com #${i}`,
    }));
    expect(aliasesForDomain(many, "example.com", 20)).toHaveLength(20);
  });

  it("returns empty for no match", () => {
    expect(aliasesForDomain(fixtureAliases, "no-match.io")).toHaveLength(0);
  });

  it("handles null aliases gracefully", () => {
    expect(aliasesForDomain(null, "example.com")).toHaveLength(0);
  });

  it("handles undefined aliases gracefully", () => {
    expect(aliasesForDomain(undefined, "example.com")).toHaveLength(0);
  });
});
