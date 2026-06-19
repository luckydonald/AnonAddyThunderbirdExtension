import { describe, expect, it } from "vitest";
import { setXulIcon } from "../experiment/xulIcon.js";

describe("setXulIcon", () => {
  it("marks XUL menu roots as menu-iconic so their image renders", () => {
    const menu = document.createElement("menu");

    setXulIcon(menu, "moz-extension://addon/icon.svg");

    expect(menu.getAttribute("image")).toBe("moz-extension://addon/icon.svg");
    expect(menu.classList.contains("menu-iconic")).toBe(true);
  });

  it("marks XUL menuitem leaves as menuitem-iconic so their image renders", () => {
    const menuitem = document.createElement("menuitem");

    setXulIcon(menuitem, "moz-extension://addon/experiment/icons/alias.svg");

    expect(menuitem.getAttribute("image")).toBe(
      "moz-extension://addon/experiment/icons/alias.svg",
    );
    expect(menuitem.classList.contains("menuitem-iconic")).toBe(true);
  });
});
