import type { Alias } from "../api/types.js";

/**
 * Returns active aliases whose description contains `domain` (case-insensitive),
 * up to `limit` results.
 *
 * Both the popup (matchingAliases) and the experiment (matchingAliasesForEmail)
 * delegate here so they always behave identically.
 */
export function aliasesForDomain(
  aliases: Alias[] | null | undefined,
  domain: string,
  limit = 10,
): Alias[] {
  const lower = domain.toLowerCase();
  return (aliases ?? [])
    .filter((a) => a.active && (a.description ?? "").toLowerCase().includes(lower))
    .slice(0, limit);
}
