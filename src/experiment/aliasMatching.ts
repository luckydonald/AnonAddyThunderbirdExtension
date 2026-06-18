import type { Alias } from "../api/types.js";
import { aliasesForDomain } from "../shared/aliasSearch.js";
import { parseForwardingAddress } from "../shared/forwardingAddress.js";

export function domainForContextMenuAliasLookup(
  email: string,
  addyDomainSet: Set<string>,
): string | null {
  const forwarding = parseForwardingAddress(email, addyDomainSet);
  if (forwarding) {
    return forwarding.originalEmail.match(/@(.+)$/)?.[1]?.toLowerCase() ?? null;
  }

  const domain = email.match(/@(.+)$/)?.[1]?.toLowerCase() ?? null;
  if (!domain || addyDomainSet.has(domain)) return null;
  return domain;
}

export function aliasesForContextMenuEmail(
  aliases: Alias[] | null | undefined,
  email: string,
  addyDomainSet: Set<string>,
  limit = 20,
): Alias[] {
  const domain = domainForContextMenuAliasLookup(email, addyDomainSet);
  return domain ? aliasesForDomain(aliases, domain, limit) : [];
}
