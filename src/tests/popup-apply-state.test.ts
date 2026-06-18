import { describe, expect, it } from "vitest";
import { hasApplyableChanges } from "../popup/applyState.js";

describe("hasApplyableChanges", () => {
  it("allows applying when a pre-aliased recipient is changed back to Don't replace", () => {
    expect(
      hasApplyableChanges([
        {
          composeAddress: "shop+user=example.com@anon.email",
          parsed: { address: "user@example.com" },
          selectedAlias: null,
        },
      ]),
    ).toBe(true);
  });

  it("allows applying when an alias is selected for a plain recipient", () => {
    expect(
      hasApplyableChanges([
        {
          composeAddress: "user@example.com",
          parsed: { address: "user@example.com" },
          selectedAlias: "shop@anon.email",
        },
      ]),
    ).toBe(true);
  });

  it("does not allow applying when a plain recipient has no alias selected", () => {
    expect(
      hasApplyableChanges([
        {
          composeAddress: "user@example.com",
          parsed: { address: "user@example.com" },
          selectedAlias: null,
        },
      ]),
    ).toBe(false);
  });
});
