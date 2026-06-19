import { describe, expect, it } from "vitest";
import { shouldSyncCacheToExperiment } from "../background/cacheSync.js";

describe("shouldSyncCacheToExperiment", () => {
  it("syncs when popup or menu refreshes write aliasCache", () => {
    expect(shouldSyncCacheToExperiment({ aliasCache: {} })).toBe(true);
  });

  it("syncs when domain options are written back to cache", () => {
    expect(shouldSyncCacheToExperiment({ domainOptions: {} })).toBe(true);
  });

  it("does not treat options changes as a plain cache sync", () => {
    expect(shouldSyncCacheToExperiment({ options: {} })).toBe(false);
  });
});
