import { describe, expect, it, vi } from "vitest";
import { createWindowAttachmentLifecycle } from "../experiment/windowAttachmentLifecycle.js";

describe("createWindowAttachmentLifecycle", () => {
  it("keeps compose hooks attached when a background event listener unloads", () => {
    const addWindowListener = vi.fn();
    const removeWindowListener = vi.fn();
    const attachExistingWindows = vi.fn();
    const cleanupAttachedWindows = vi.fn();

    const lifecycle = createWindowAttachmentLifecycle({
      addWindowListener,
      removeWindowListener,
      attachExistingWindows,
      cleanupAttachedWindows,
    });

    lifecycle.ensureAttached();
    lifecycle.releaseEventListener();
    lifecycle.ensureAttached();

    expect(addWindowListener).toHaveBeenCalledTimes(1);
    expect(attachExistingWindows).toHaveBeenCalledTimes(1);
    expect(removeWindowListener).not.toHaveBeenCalled();
    expect(cleanupAttachedWindows).not.toHaveBeenCalled();
  });

  it("removes compose hooks on explicit experiment shutdown", () => {
    const addWindowListener = vi.fn();
    const removeWindowListener = vi.fn();
    const attachExistingWindows = vi.fn();
    const cleanupAttachedWindows = vi.fn();

    const lifecycle = createWindowAttachmentLifecycle({
      addWindowListener,
      removeWindowListener,
      attachExistingWindows,
      cleanupAttachedWindows,
    });

    lifecycle.ensureAttached();
    lifecycle.shutdown();

    expect(removeWindowListener).toHaveBeenCalledTimes(1);
    expect(cleanupAttachedWindows).toHaveBeenCalledTimes(1);
  });
});
