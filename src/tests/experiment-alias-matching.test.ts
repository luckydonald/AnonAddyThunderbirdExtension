import { describe, expect, it } from "vitest";
import {
  aliasesForContextMenuEmail,
  domainForContextMenuAliasLookup,
} from "../experiment/aliasMatching.js";
import type { Alias } from "../api/types.js";

const addyDomains = new Set(["anon.email"]);
const aliases: Alias[] = [
  {
    id: "matching",
    local_part: "shop",
    domain: "anon.email",
    email: "shop@anon.email",
    active: true,
    description: "Shopping alias for example.com",
  },
  {
    id: "inactive",
    local_part: "old",
    domain: "anon.email",
    email: "old@anon.email",
    active: false,
    description: "Old alias for example.com",
  },
  {
    id: "other",
    local_part: "other",
    domain: "anon.email",
    email: "other@anon.email",
    active: true,
    description: "Other alias for other.test",
  },
];

describe("domainForContextMenuAliasLookup", () => {
  it("uses the original recipient domain for forwarding Addy addresses", () => {
    expect(
      domainForContextMenuAliasLookup(
        "shop+user=example.com@anon.email",
        addyDomains,
      ),
    ).toBe("example.com");
  });

  it("uses the direct recipient domain for plain external addresses", () => {
    expect(
      domainForContextMenuAliasLookup("user@example.com", addyDomains),
    ).toBe("example.com");
  });

  it("does not search existing aliases for a plain Addy-domain address", () => {
    expect(
      domainForContextMenuAliasLookup("shop@anon.email", addyDomains),
    ).toBe(null);
  });
});

describe("aliasesForContextMenuEmail", () => {
  it("returns existing aliases for an already-translated pill", () => {
    const result = aliasesForContextMenuEmail(
      aliases,
      "shop+user=example.com@anon.email",
      addyDomains,
    );

    expect(result.map((alias) => alias.id)).toEqual(["matching"]);
  });
});
