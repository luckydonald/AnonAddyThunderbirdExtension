interface StorageArea {
  get(keys: Record<string, unknown>): Promise<Record<string, unknown>>;
  set(items: Record<string, unknown>): Promise<void>;
}

interface ComposeDetails {
  to: string[];
  cc: string[];
  bcc: string[];
}

declare const messenger: {
  storage: {
    local: StorageArea;
    onChanged: {
      addListener(
        callback: (
          changes: Record<string, { oldValue?: unknown; newValue?: unknown }>,
        ) => void,
      ): void;
    };
  };
  permissions: {
    contains(permissions: { origins?: string[] }): Promise<boolean>;
    request(permissions: { origins?: string[] }): Promise<boolean>;
  };
  tabs: {
    getCurrent(): Promise<{ id: number }>;
  };
  compose: {
    getComposeDetails(tabId: number): Promise<ComposeDetails>;
    setComposeDetails(
      tabId: number,
      details: Partial<ComposeDetails>,
    ): Promise<void>;
  };
  alarms: {
    create(
      name: string,
      alarmInfo: { when?: number; periodInMinutes?: number },
    ): void;
    onAlarm: {
      addListener(callback: (alarm: { name: string }) => void): void;
    };
  };
  messengerUtilities: {
    parseMailboxString(
      address: string,
    ): Promise<Array<{ email: string; name: string }>>;
  };
  composeAction: {
    openPopup(options?: { windowId?: number }): Promise<boolean>;
  };
  i18n: {
    getMessage(messageName: string, substitutions?: string | string[]): string;
  };
  runtime: {
    openOptionsPage(): Promise<void>;
    onInstalled: {
      addListener(callback: (details: { reason: string }) => void): void;
    };
  };
  AddressChipMenu: {
    onChipMenuClicked: {
      addListener(
        callback: (info: {
          email: string;
          displayName: string;
          fieldType: string;
        }) => void,
      ): void;
    };
  };
};
