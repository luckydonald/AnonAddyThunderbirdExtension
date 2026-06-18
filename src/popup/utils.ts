import type { Alias } from "../api/types.js";
import { aliasesForDomain } from "../shared/aliasSearch.js";

export function matchingAliases(aliases: Alias[], domain: string): Alias[] {
  return aliasesForDomain(aliases, domain, 10);
}

export {
  parseForwardingAddress,
  buildForwardingAddress,
} from "../shared/forwardingAddress.js";
