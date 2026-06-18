export interface WindowAttachmentLifecycle {
  ensureAttached(): void;
  releaseEventListener(): void;
  shutdown(): void;
}

export function createWindowAttachmentLifecycle(options: {
  addWindowListener(): void;
  removeWindowListener(): void;
  attachExistingWindows(): void;
  cleanupAttachedWindows(): void;
}): WindowAttachmentLifecycle {
  let attached = false;

  return {
    ensureAttached() {
      if (attached) return;
      options.addWindowListener();
      options.attachExistingWindows();
      attached = true;
    },

    releaseEventListener() {
      // MV3 service workers unload their event listener conduits frequently.
      // Keep compose-window hooks installed so the Thunderbird UI does not lose
      // the Addy menu until the background wakes again.
    },

    shutdown() {
      if (!attached) return;
      options.removeWindowListener();
      options.cleanupAttachedWindows();
      attached = false;
    },
  };
}
