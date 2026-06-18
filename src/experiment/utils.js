// Pure functions extracted for unit testing.
// implementation.js uses equivalent inline logic that closes over _cacheData.

/**
 * Returns aliases whose email address contains the recipient domain as a substring,
 * capped at 20. Note: matches by alias *email*, not description — different from
 * the popup's matchingAliases which matches by description.
 */
export function matchingAliasesForEmail(aliases, email) {
  const m = email.match(/@(.+)$/);
  if (!m) return [];
  const domain = m[1].toLowerCase();
  return (aliases || [])
    .filter((a) => a.active && a.email.toLowerCase().includes(domain))
    .slice(0, 20);
}
