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
    getAll(): Promise<{ origins: string[]; permissions: string[] }>;
    onAdded: {
      addListener(
        callback: (permissions: {
          origins?: string[];
          permissions?: string[];
        }) => void,
      ): void;
    };
    onRemoved: {
      addListener(
        callback: (permissions: {
          origins?: string[];
          permissions?: string[];
        }) => void,
      ): void;
    };
  };
  tabs: {
    getCurrent(): Promise<{ id: number }>;
    query(queryInfo: {
      windowId?: number;
      active?: boolean;
      type?: string;
    }): Promise<Array<{ id: number }>>;
    onRemoved: {
      addListener(callback: (tabId: number) => void): void;
    };
  };
  windows: {
    create(createData: {
      url?: string;
      type?: "normal" | "popup" | "panel" | "detached_panel";
      width?: number;
      height?: number;
    }): Promise<{ id: number }>;
    remove(windowId: number): Promise<void>;
    getLastFocused(options?: {
      windowTypes?: string[];
    }): Promise<{ id: number; focused: boolean }>;
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
    onClicked: {
      addListener(callback: (tab: { id: number }) => void): void;
    };
  };
  i18n: {
    getMessage(messageName: string, substitutions?: string | string[]): string;
  };
  runtime: {
    getURL(path: string): string;
    openOptionsPage(): Promise<void>;
    sendMessage(message: Record<string, unknown>): Promise<unknown>;
    onMessage: {
      addListener(
        callback: (
          message: Record<string, unknown>,
          sender: { id?: string; tab?: { id: number } },
        ) => void | Promise<unknown>,
      ): void;
    };
    onInstalled: {
      addListener(callback: (details: { reason: string }) => void): void;
    };
    onStartup: {
      addListener(callback: () => void): void;
    };
  };
  AddressChipMenu: {
    setCache(data: {
      aliases: Array<{ id: string; email: string; active: boolean }>;
      domainOptions: {
        data: string[];
        defaultAliasDomain: string;
        defaultAliasFormat: string;
      };
    }): void;
    onChipMenuClicked: {
      addListener(
        callback: (info: {
          email: string;
          displayName: string;
          fieldType: string;
          action: "open_popup" | "select_alias" | "create_alias";
          aliasEmail?: string;
          domain?: string;
          format?: string;
          customPrefix?: string;
        }) => void,
      ): void;
    };
  };
};
