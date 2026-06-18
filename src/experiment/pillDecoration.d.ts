export declare function decoratePillViaTextNode(
  pill: Element,
  displayText: string | null | undefined,
): boolean;

export declare function decoratePillViaCSSAdopted(
  pill: Element,
  displayText: string | null | undefined,
): boolean;

export declare function upsertPillIcon(
  pill: Element,
  pillIconMap: WeakMap<Element, HTMLImageElement>,
  iconUrl: string,
  proxied: boolean,
): void;

export declare function removePillIcon(
  pill: Element,
  pillIconMap: WeakMap<Element, HTMLImageElement>,
): void;
