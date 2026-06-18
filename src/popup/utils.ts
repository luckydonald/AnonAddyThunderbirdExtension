import type { Alias } from "../api/types.js";

export function matchingAliases(aliases: Alias[], domain: string): Alias[] {
  const lower = domain.toLowerCase();
  const matched = aliases.filter(
    (a) => a.active && (a.description ?? "").toLowerCase().includes(lower),
  );
  return matched.slice(0, 10);
}

export function parseForwardingAddress(
  email: string,
  addyDomainSet: Set<string>,
): { originalEmail: string; aliasEmail: string } | null {
  const dm = email.match(/^(.+)@(.+)$/);
  if (!dm) return null;
  const [, localPart, domain] = dm;
  if (!addyDomainSet.has(domain.toLowerCase())) return null;
  const fw = localPart.match(/^(.+)\+(.+)=(.+)$/);
  if (!fw) return null;
  const [, aliasLocal, recipLocal, recipDomain] = fw;
  return {
    originalEmail: `${recipLocal}@${recipDomain}`,
    aliasEmail: `${aliasLocal}@${domain}`,
  };
}

export function buildForwardingAddress(
  aliasEmail: string,
  originalEmail: string,
): string | null {
  const am = aliasEmail.match(/^(.+)@(.+)$/);
  const om = originalEmail.match(/^(.+)@(.+)$/);
  if (!am || !om) return null;
  return `${am[1]}+${om[1]}=${om[2]}@${am[2]}`;
}
