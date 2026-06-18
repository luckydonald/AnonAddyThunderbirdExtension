export interface PopupWindowTracker {
  remember(windowId: number | undefined): void;
  closeAll(): Promise<void>;
}

export function createPopupWindowTracker(
  closeWindow: (windowId: number) => Promise<void>,
): PopupWindowTracker {
  const windowIds = new Set<number>();

  return {
    remember(windowId) {
      if (windowId !== undefined) windowIds.add(windowId);
    },

    async closeAll() {
      const ids = [...windowIds];
      windowIds.clear();
      await Promise.all(
        ids.map((windowId) => closeWindow(windowId).catch(() => undefined)),
      );
    },
  };
}

export function shouldCloseForRemovedTab(
  removedTabId: number,
  composeTabId: number,
): boolean {
  return removedTabId === composeTabId;
}
