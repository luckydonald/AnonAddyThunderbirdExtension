export function shouldSyncCacheToExperiment(
  changes: Record<string, unknown>,
): boolean {
  return "aliasCache" in changes || "domainOptions" in changes;
}
