import { vi } from "vitest";

const messengerMock = {
  storage: {
    local: {
      get: vi.fn(),
      set: vi.fn(),
    },
    onChanged: {
      addListener: vi.fn(),
    },
  },
  permissions: {
    contains: vi.fn(),
    request: vi.fn(),
    getAll: vi.fn(),
    onAdded: { addListener: vi.fn() },
    onRemoved: { addListener: vi.fn() },
  },
  tabs: {
    getCurrent: vi.fn(),
    query: vi.fn(),
  },
  windows: {
    create: vi.fn(),
    getLastFocused: vi.fn(),
  },
  compose: {
    getComposeDetails: vi.fn(),
    setComposeDetails: vi.fn(),
  },
  alarms: {
    create: vi.fn(),
    onAlarm: { addListener: vi.fn() },
  },
  messengerUtilities: {
    parseMailboxString: vi.fn(),
  },
  composeAction: {
    openPopup: vi.fn(),
    onClicked: { addListener: vi.fn() },
  },
  i18n: {
    getMessage: vi.fn((key: string) => key),
  },
  runtime: {
    getURL: vi.fn((path: string) => `moz-extension://test/${path}`),
    openOptionsPage: vi.fn(),
    onInstalled: { addListener: vi.fn() },
    onStartup: { addListener: vi.fn() },
  },
  AddressChipMenu: {
    setCache: vi.fn(),
    onChipMenuClicked: { addListener: vi.fn() },
  },
};

Object.defineProperty(globalThis, "messenger", {
  value: messengerMock,
  writable: true,
});
