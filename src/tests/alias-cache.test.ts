import { describe, expect, it } from "vitest";
import { mergeAliasesIntoCache } from "../shared/aliasCache.js";
import type { Alias } from "../api/types.js";

function alias(id: string, email: string): Alias {
  return {
    id,
    local_part: email.split("@")[0],
    domain: email.split("@")[1],
    email,
    active: true,
    description: "",
  };
}

describe("mergeAliasesIntoCache", () => {
  it("updates existing aliases and appends new aliases by ID", () => {
    const result = mergeAliasesIntoCache(
      { aliases: [alias("a1", "old@anon.email")], fetchedAt: 1 },
      [alias("a1", "new@anon.email"), alias("a2", "extra@anon.email")],
      99,
    );

    expect(result.aliases.map((entry) => entry.email)).toEqual([
      "new@anon.email",
      "extra@anon.email",
    ]);
    expect(result.fetchedAt).toBe(99);
  });
});
