import { describe, expect, it, vi } from "vitest";
import {
  createPopupWindowTracker,
  shouldCloseForRemovedTab,
} from "../popup/windowTracker.js";

describe("createPopupWindowTracker", () => {
  it("closes every remembered New Alias window when the Addy popup closes", async () => {
    const closeWindow = vi.fn().mockResolvedValue(undefined);
    const tracker = createPopupWindowTracker(closeWindow);

    tracker.remember(12);
    tracker.remember(34);
    await tracker.closeAll();

    expect(closeWindow).toHaveBeenCalledWith(12);
    expect(closeWindow).toHaveBeenCalledWith(34);
  });

  it("does not close the same child window twice", async () => {
    const closeWindow = vi.fn().mockResolvedValue(undefined);
    const tracker = createPopupWindowTracker(closeWindow);

    tracker.remember(12);
    await tracker.closeAll();
    await tracker.closeAll();

    expect(closeWindow).toHaveBeenCalledTimes(1);
  });
});

describe("shouldCloseForRemovedTab", () => {
  it("closes the Addy popup when its compose tab is removed", () => {
    expect(shouldCloseForRemovedTab(7, 7)).toBe(true);
  });

  it("keeps the Addy popup open for unrelated removed tabs", () => {
    expect(shouldCloseForRemovedTab(8, 7)).toBe(false);
  });
});
