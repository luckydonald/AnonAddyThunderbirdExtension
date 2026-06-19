import { parseForwardingAddress } from "../shared/forwardingAddress.js";

export type PillDecorationState =
  | { icon: "proxied"; label: string }
  | { icon: "aliased"; label: null }
  | { icon: "none"; label: null };

/**
 * Pure function: given a pill's emailAddress and the set of known Addy domains,
 * return what icon state and display label the pill should have.
 *
 * Callers (decoratePill in implementation.ts) apply the result to the DOM.
 * Keeping this logic pure makes it unit-testable without a Thunderbird environment.
 */
export function computePillDecoration(
  email: string,
  addyDomainSet: Set<string>,
): PillDecorationState {
  const fwd = parseForwardingAddress(email, addyDomainSet);
  if (fwd) {
    return {
      icon: "proxied",
      label: `${fwd.aliasEmail} → ${fwd.originalEmail}`,
    };
  }
  const domain = email.match(/@(.+)$/)?.[1]?.toLowerCase() ?? "";
  if (addyDomainSet.has(domain)) {
    return { icon: "aliased", label: null };
  }
  return { icon: "none", label: null };
}
