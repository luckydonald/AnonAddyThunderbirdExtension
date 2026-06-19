type XulIconElement = {
  classList?: {
    add(...tokens: string[]): void;
  };
  setAttribute(name: string, value: string): void;
  tagName?: string;
};

export function setXulIcon(element: XulIconElement, iconUrl: string): void {
  element.setAttribute("image", iconUrl);

  const tagName = element.tagName?.toLowerCase();
  const iconClass = tagName === "menu" ? "menu-iconic" : "menuitem-iconic";
  element.classList?.add(iconClass);
}
