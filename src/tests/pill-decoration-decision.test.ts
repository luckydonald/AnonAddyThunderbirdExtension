import { describe, it, expect } from "vitest";
import { computePillDecoration } from "../experiment/pillDecorationDecision.js";

const ADDY_DOMAINS = new Set(["anon.email", "anonaddy.me"]);

// ─── proxied: forwarding address on a known Addy domain ──────────────────────

describe("computePillDecoration — proxied (forwarding address)", () => {
  it("returns icon=proxied and a human-readable label for a forwarding address", () => {
    expect(
      computePillDecoration("alias+user=example.com@anon.email", ADDY_DOMAINS),
    ).toEqual({ icon: "proxied", label: "alias@anon.email → user@example.com" });
  });

  it("works for the second Addy domain in the set", () => {
    expect(
      computePillDecoration("foo+bar=bar.org@anonaddy.me", ADDY_DOMAINS),
    ).toEqual({ icon: "proxied", label: "foo@anonaddy.me → bar@bar.org" });
  });

  it("includes the full original email (local+domain) in the label", () => {
    const result = computePillDecoration(
      "priv+contact=newsletters.example.com@anon.email",
      ADDY_DOMAINS,
    );
    expect(result.icon).toBe("proxied");
    expect(result.label).toBe(
      "priv@anon.email → contact@newsletters.example.com",
    );
  });
});

// ─── aliased: plain address on a known Addy domain, not a forwarding addr ────

describe("computePillDecoration — aliased (plain Addy-domain address)", () => {
  it("returns icon=aliased and null label for a plain Addy address", () => {
    expect(
      computePillDecoration("someuser@anon.email", ADDY_DOMAINS),
    ).toEqual({ icon: "aliased", label: null });
  });

  it("is case-insensitive for the domain part", () => {
    expect(
      computePillDecoration("user@ANON.EMAIL", ADDY_DOMAINS),
    ).toEqual({ icon: "aliased", label: null });
  });

  it("recognises any alias-looking local part that lacks the +orig=domain encoding", () => {
    expect(
      computePillDecoration("random-words@anonaddy.me", ADDY_DOMAINS),
    ).toEqual({ icon: "aliased", label: null });
  });
});

// ─── none: address on a domain that is not in the Addy domain set ────────────

describe("computePillDecoration — none (external / non-Addy domain)", () => {
  it("returns icon=none and null label for an ordinary external address", () => {
    expect(
      computePillDecoration("user@gmail.com", ADDY_DOMAINS),
    ).toEqual({ icon: "none", label: null });
  });

  it("returns icon=none even if the local part looks like a forwarding address but the domain is not Addy", () => {
    // The +orig=domain pattern is only meaningful when the domain is in the Addy set.
    expect(
      computePillDecoration("alias+user=example.com@not-addy.com", ADDY_DOMAINS),
    ).toEqual({ icon: "none", label: null });
  });

  it("returns icon=none for an empty string", () => {
    expect(computePillDecoration("", ADDY_DOMAINS)).toEqual({
      icon: "none",
      label: null,
    });
  });

  it("returns icon=none when the Addy domain set is empty", () => {
    expect(
      computePillDecoration("alias+user=example.com@anon.email", new Set()),
    ).toEqual({ icon: "none", label: null });
  });
});
