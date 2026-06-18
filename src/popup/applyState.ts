export interface ApplyableRecipient {
  composeAddress: string;
  parsed: {
    address: string;
  };
  selectedAlias: string | null;
}

export function hasApplyableChanges(recipients: ApplyableRecipient[]): boolean {
  return recipients.some(
    (recipient) =>
      recipient.selectedAlias !== null ||
      recipient.composeAddress !== recipient.parsed.address,
  );
}
