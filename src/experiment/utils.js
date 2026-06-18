// Pure functions extracted for unit testing.
// implementation.js uses equivalent inline logic that closes over _cacheData.

/**
 * Returns aliases whose *description* contains the recipient domain as a
 * substring (case-insensitive), capped at 20.  Mirrors the popup's
 * `matchingAliases` logic so both UI surfaces show the same candidates.
 */
export function matchingAliasesForEmail(aliases, email) {
  const m = email.match(/@(.+)$/);
  if (!m) return [];
  const domain = m[1].toLowerCase();
  return (aliases || [])
    .filter((a) => a.active && (a.description ?? "").toLowerCase().includes(domain))
    .slice(0, 20);
}
