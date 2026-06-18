// Thunderbird chrome-context globals — available in privileged experiment scripts.
// Not covered by @types/webextension-polyfill.

declare var ChromeUtils: {
  importESModule(url: string): Record<string, unknown>;
};

declare var Services: {
  wm: {
    addListener(listener: unknown): void;
    removeListener(listener: unknown): void;
    getEnumerator(type: string): { hasMoreElements(): boolean; getNext(): any };
  };
  prompt: {
    prompt(
      parent: unknown,
      title: string,
      text: string,
      value: { value: string },
      check: unknown,
      checkState: unknown,
    ): boolean;
  };
};

declare var Ci: {
  nsIInterfaceRequestor: unknown;
  nsIDOMWindow: unknown;
};
