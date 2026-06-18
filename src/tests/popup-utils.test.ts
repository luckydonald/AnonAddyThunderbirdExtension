import { describe, it, expect } from "vitest";
import {
  matchingAliases,
  parseForwardingAddress,
  buildForwardingAddress,
} from "../popup/utils.js";
import type { Alias } from "../api/types.js";
import aliases from "../../tests/fixtures/aliases.json";
import forwardingCases from "../../tests/fixtures/forwarding-cases.json";
import domainOptions from "../../tests/fixtures/domain-options.json";

const fixtureAliases = aliases as Alias[];
const addyDomainSet = new Set(domainOptions.data.map((d) => d.toLowerCase()));

// ─── matchingAliases ──────────────────────────────────────────────────────────

describe("matchingAliases", () => {
  it("returns aliases matching domain by description (case-insensitive)", () => {
    const result = matchingAliases(fixtureAliases, "example.com");
    const ids = result.map((a) => a.id);
    expect(ids).toContain("a1");
    expect(ids).toContain("a2");
    expect(ids).toContain("a3");
  });

  it("excludes inactive aliases", () => {
    const result = matchingAliases(fixtureAliases, "example.com");
    expect(result.find((a) => a.id === "a4")).toBeUndefined();
  });

  it("excludes aliases with non-matching descriptions", () => {
    const result = matchingAliases(fixtureAliases, "example.com");
    expect(result.find((a) => a.id === "a5")).toBeUndefined();
  });

  it("is case-insensitive on both sides", () => {
    const result = matchingAliases(fixtureAliases, "EXAMPLE.COM");
    expect(result.map((a) => a.id)).toContain("a1");
  });

  it("caps results at 10", () => {
    const many: Alias[] = Array.from({ length: 15 }, (_, i) => ({
      id: `m${i}`,
      local_part: `alias${i}`,
      domain: "anon.email",
      email: `alias${i}@anon.email`,
      active: true,
      description: `alias for example.com #${i}`,
    }));
    expect(matchingAliases(many, "example.com")).toHaveLength(10);
  });

  it("returns empty array when nothing matches", () => {
    expect(matchingAliases(fixtureAliases, "no-match.io")).toHaveLength(0);
  });
});

// ─── parseForwardingAddress ───────────────────────────────────────────────────

describe("parseForwardingAddress", () => {
  const validCases = forwardingCases.filter((c) => c.originalEmail !== null);
  const invalidCases = forwardingCases.filter((c) => c.originalEmail === null);

  it.each(validCases)(
    "parses $description",
    ({ forwardingAddress, originalEmail, aliasEmail }) => {
      const result = parseForwardingAddress(forwardingAddress, addyDomainSet);
      expect(result).not.toBeNull();
      expect(result?.originalEmail).toBe(originalEmail);
      expect(result?.aliasEmail).toBe(aliasEmail);
    },
  );

  it.each(invalidCases)(
    "returns null for $description",
    ({ forwardingAddress }) => {
      expect(
        parseForwardingAddress(forwardingAddress, addyDomainSet),
      ).toBeNull();
    },
  );

  it("returns null for a plain email address", () => {
    expect(
      parseForwardingAddress("user@example.com", addyDomainSet),
    ).toBeNull();
  });
});

// ─── buildForwardingAddress ───────────────────────────────────────────────────

describe("buildForwardingAddress", () => {
  it("constructs the correct forwarding format", () => {
    expect(buildForwardingAddress("shop@anonaddy.me", "user@example.com")).toBe(
      "shop+user=example.com@anonaddy.me",
    );
  });

  it("round-trips with valid forwarding cases from fixtures", () => {
    for (const c of validCases) {
      expect(buildForwardingAddress(c.aliasEmail!, c.originalEmail!)).toBe(
        c.forwardingAddress,
      );
    }
  });

  it("returns null for malformed alias email", () => {
    expect(buildForwardingAddress("notanemail", "user@example.com")).toBeNull();
  });

  it("returns null for malformed original email", () => {
    expect(buildForwardingAddress("shop@anonaddy.me", "notanemail")).toBeNull();
  });
});

// Re-declared here so the round-trip test in the describe block can access it.
const validCases = forwardingCases.filter((c) => c.originalEmail !== null);
