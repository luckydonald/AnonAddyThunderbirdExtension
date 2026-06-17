interface MessengerStorageArea {
  get(keys: Record<string, unknown>): Promise<Record<string, unknown>>;
  set(items: Record<string, unknown>): Promise<void>;
}

interface MessengerPermissions {
  contains(permissions: { origins?: string[] }): Promise<boolean>;
  request(permissions: { origins?: string[] }): Promise<boolean>;
}

declare const messenger: {
  storage: {
    local: MessengerStorageArea;
  };
  permissions: MessengerPermissions;
};
