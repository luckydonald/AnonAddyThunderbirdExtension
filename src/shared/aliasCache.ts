import type { Alias } from "../api/types.js";

export interface AliasCache {
  aliases: Alias[];
  fetchedAt: number;
}

export function mergeAliasesIntoCache(
  cache: AliasCache,
  freshAliases: Alias[],
  fetchedAt = Date.now(),
): AliasCache {
  const aliases = [...cache.aliases];
  for (const fresh of freshAliases) {
    const idx = aliases.findIndex((alias) => alias.id === fresh.id);
    if (idx >= 0) aliases[idx] = fresh;
    else aliases.push(fresh);
  }
  return { aliases, fetchedAt };
}
