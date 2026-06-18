import { aliasesForDomain } from "../shared/aliasSearch.js";

/**
 * Returns active aliases whose description contains the recipient domain
 * (case-insensitive), capped at 20.  Delegates to the shared
 * `aliasesForDomain` so the experiment and the popup use identical matching
 * logic.
 *
 * Note: `implementation.js` keeps an inline copy of this logic (it runs in
 * a privileged TB context that Vite does not bundle).  Keep both in sync —
 * this file is the testable source of truth.
 */
export function matchingAliasesForEmail(aliases, email) {
  const m = email.match(/@(.+)$/);
  if (!m) return [];
  return aliasesForDomain(aliases, m[1], 20);
}
