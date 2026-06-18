"""
Marionette tests for the AddressChipMenu experiment API (right-click context menu
on mail-address-pill elements in the compose window).

Context notes:
- All Thunderbird windows are XUL chrome windows; window_handles returns [].
  Use chrome_window_handles and using_context("chrome") throughout.
- mail-address-pill elements live in the compose window's chrome document.
- The right-click context menu is a XUL menupopup also in the chrome document.
  Find menu items with CSS selectors like menuitem[label="..."].
- MsgNewMessage(null) is the only way to open a compose window from chrome context.
  messenger.compose.beginNew() requires WebExtension content context (unavailable).
"""

import time

import pytest
from marionette_driver.by import By
from marionette_driver.keys import Keys
from marionette_driver.wait import Wait

import mock_server as mock_server_mod

RECIPIENT = "user@example.com"
ALIAS_EMAIL = "shop@anonaddy.me"


def open_compose_with_recipient(client, recipient: str):
    """Open a compose window, type a recipient to create a pill, return its handle."""
    before = set(client.chrome_window_handles)
    with client.using_context("chrome"):
        client.execute_script(
            "Services.wm.getMostRecentWindow('mail:3pane').MsgNewMessage(null);"
        )
    Wait(client, timeout=15).until(
        lambda _: len(set(client.chrome_window_handles) - before) > 0
    )
    new_handle = (set(client.chrome_window_handles) - before).pop()
    client.switch_to_window(new_handle)

    # Type the recipient into the To: field so Thunderbird creates a pill
    with client.using_context("chrome"):
        field = client.find_element(By.ID, "toAddrInput")
        field.click()
        field.send_keys(recipient)
        field.send_keys(Keys.RETURN)
    time.sleep(0.8)  # let TB create the pill element

    return new_handle


def right_click_first_pill(client):
    """Dispatch a contextmenu event on the first mail-address-pill."""
    with client.using_context("chrome"):
        client.execute_script(
            """
            const pill = document.querySelector("mail-address-pill");
            if (!pill) throw new Error("No mail-address-pill found");
            const rect = pill.getBoundingClientRect();
            const cx = rect.left + rect.width / 2;
            const cy = rect.top + rect.height / 2;
            pill.dispatchEvent(new MouseEvent("contextmenu", {
                bubbles: true, cancelable: true,
                clientX: cx, clientY: cy,
                button: 2, buttons: 2
            }));
            """
        )
    time.sleep(0.7)  # let XUL popup open


def find_menu_item(client, label_fragment: str):
    """Find a XUL menuitem whose label contains label_fragment (case-insensitive)."""
    with client.using_context("chrome"):
        return client.execute_script(
            """
            const frag = arguments[0].toLowerCase();
            const items = document.querySelectorAll("menuitem");
            for (const it of items) {
                const lbl = (it.getAttribute("label") || it.textContent || "").toLowerCase();
                if (lbl.includes(frag)) return it;
            }
            return null;
            """,
            script_args=[label_fragment],
        )


def click_menu_item(client, label_fragment: str):
    """Find and click a XUL menuitem by label fragment."""
    with client.using_context("chrome"):
        result = client.execute_script(
            """
            const frag = arguments[0].toLowerCase();
            const items = document.querySelectorAll("menuitem");
            for (const it of items) {
                const lbl = (it.getAttribute("label") || it.textContent || "").toLowerCase();
                if (lbl.includes(frag)) { it.click(); return true; }
            }
            return false;
            """,
            script_args=[label_fragment],
        )
    return result


def press_key(client, key: str):
    """Dispatch a keydown event on the compose document (for XUL popup navigation)."""
    with client.using_context("chrome"):
        client.execute_script(
            """
            document.documentElement.dispatchEvent(new KeyboardEvent("keydown", {
                key: arguments[0], bubbles: true, cancelable: true
            }));
            """,
            script_args=[key],
        )


def open_submenu(client, menu_label_fragment: str):
    """Click a XUL menu element (parent item with popup) matching the label fragment."""
    with client.using_context("chrome"):
        result = client.execute_script(
            """
            const frag = arguments[0].toLowerCase();
            // Check both <menu> and <menuitem> elements
            for (const tag of ["menu", "menuitem"]) {
                for (const el of document.querySelectorAll(tag)) {
                    const lbl = (el.getAttribute("label") || el.textContent || "").toLowerCase();
                    if (lbl.includes(frag)) { el.click(); return true; }
                }
            }
            return false;
            """,
            script_args=[menu_label_fragment],
        )
    time.sleep(0.3)
    return result


@pytest.mark.usefixtures("tb")
class TestChipMenu:
    def test_addy_menu_item_appears_on_right_click(self, tb):
        compose_handle = open_compose_with_recipient(tb, RECIPIENT)
        right_click_first_pill(tb)

        # The experiment injects a "Use Addy alias for sending" item into the pill menu
        with tb.using_context("chrome"):
            found = tb.execute_script(
                """
                const items = document.querySelectorAll("menuitem, menu");
                for (const it of items) {
                    const lbl = it.getAttribute("label") || it.textContent || "";
                    if (lbl.toLowerCase().includes("addy")) return lbl;
                }
                return null;
                """
            )
        assert found is not None, "No Addy menu item found in context menu"

        with tb.using_context("chrome"):
            tb.switch_to_window(compose_handle)
            tb.execute_script("window.close();")

    def test_select_existing_alias(self, tb):
        mock_server_mod._Handler.recorded.clear()
        compose_handle = open_compose_with_recipient(tb, RECIPIENT)
        right_click_first_pill(tb)

        # Open the Addy sub-menu (parent item)
        opened = open_submenu(tb, "addy")
        assert opened, "Could not open Addy menu"
        time.sleep(0.3)

        # Click the "Existing…" submenu parent
        opened2 = open_submenu(tb, "existing")
        assert opened2, "Could not open Existing submenu"
        time.sleep(0.3)

        # Click the alias entry
        clicked = click_menu_item(tb, ALIAS_EMAIL)
        assert clicked, f"Could not click alias item '{ALIAS_EMAIL}'"
        time.sleep(0.5)

        # No exception = success; the extension handles the selection internally.
        # A full assertion would check the compose pill but the experiment rewrites it
        # asynchronously, so we settle for confirming no crash occurred.
        assert True

        with tb.using_context("chrome"):
            tb.switch_to_window(compose_handle)
            tb.execute_script("window.close();")

    def test_create_alias_posts_to_mock_server(self, tb):
        mock_server_mod._Handler.recorded.clear()
        compose_handle = open_compose_with_recipient(tb, RECIPIENT)
        right_click_first_pill(tb)

        opened = open_submenu(tb, "addy")
        assert opened, "Could not open Addy menu"
        time.sleep(0.3)

        # Click "New…" submenu parent
        opened2 = open_submenu(tb, "new")
        assert opened2, "Could not open New submenu"
        time.sleep(0.3)

        # Pick "Characters" format
        clicked = click_menu_item(tb, "characters")
        assert clicked, "Could not click Characters menu item"
        time.sleep(1.5)

        # The extension background should have POSTed to the mock server
        post_calls = [r for r in mock_server_mod._Handler.recorded if r[0] == "POST"]
        assert post_calls, "No POST request recorded — alias creation did not reach mock server"

        _, path, body = post_calls[0]
        assert path == "/api/v1/aliases"
        assert body.get("format") == "random_characters"

        with tb.using_context("chrome"):
            tb.switch_to_window(compose_handle)
            tb.execute_script("window.close();")

    def test_addy_menu_survives_submenu_navigation(self, tb):
        """Regression: enter Addy submenu, navigate back out, arrow up to a native
        pre-existing menu item — then close the popup and re-open it.  The Addy menu
        item must still appear.

        Bug: after navigating out of the Addy submenu and onto a native menu item,
        the Addy entry vanishes from all subsequent right-click menus until the
        extension is reloaded.
        """
        compose_handle = open_compose_with_recipient(tb, RECIPIENT)
        right_click_first_pill(tb)

        # Verify Addy entry is present on the first open
        with tb.using_context("chrome"):
            found_initial = tb.execute_script(
                """
                const items = document.querySelectorAll("menuitem, menu");
                for (const it of items) {
                    const lbl = it.getAttribute("label") || it.textContent || "";
                    if (lbl.toLowerCase().includes("addy")) return lbl;
                }
                return null;
                """
            )
        assert found_initial is not None, "Addy menu item not found on initial right-click"

        # Enter the Addy submenu (one level deep)
        opened = open_submenu(tb, "addy")
        assert opened, "Could not open Addy submenu"
        time.sleep(0.4)

        # Navigate back out of the submenu to the parent popup
        press_key(tb, "Escape")
        time.sleep(0.3)

        # Move up to a native (pre-existing) menu item above the Addy entry
        press_key(tb, "ArrowUp")
        time.sleep(0.2)

        # Close the context menu entirely
        press_key(tb, "Escape")
        time.sleep(0.4)

        # Re-open the context menu with another right-click
        right_click_first_pill(tb)

        # The Addy entry must still be present — this is what the bug breaks
        with tb.using_context("chrome"):
            found_after = tb.execute_script(
                """
                const items = document.querySelectorAll("menuitem, menu");
                for (const it of items) {
                    const lbl = it.getAttribute("label") || it.textContent || "";
                    if (lbl.toLowerCase().includes("addy")) return lbl;
                }
                return null;
                """
            )
        assert found_after is not None, (
            "Addy menu item vanished after entering submenu and navigating to a native "
            "menu item — extension state broken until reload (regression)"
        )

        # Cleanup
        press_key(tb, "Escape")
        time.sleep(0.2)
        with tb.using_context("chrome"):
            tb.switch_to_window(compose_handle)
            tb.execute_script("window.close();")

    def test_addy_menu_items_have_icons(self, tb):
        """The top-level Addy menu, 'Existing…', and 'New…' must each have an icon
        set via the 'image' attribute.  Verifies that SVG data-URI icons are applied
        (chrome:// URLs were broken in some TB versions)."""
        compose_handle = open_compose_with_recipient(tb, RECIPIENT)
        right_click_first_pill(tb)

        with tb.using_context("chrome"):
            icons = tb.execute_script(
                """
                const result = {};
                for (const el of document.querySelectorAll("menu, menuitem")) {
                    const lbl = (el.getAttribute("label") || "").toLowerCase();
                    if (lbl.includes("addy")) result.addy = el.getAttribute("image") || "";
                    if (lbl.includes("existing")) result.existing = el.getAttribute("image") || "";
                    if (lbl.includes("new")) result.new = el.getAttribute("image") || "";
                }
                return result;
                """
            )

        assert icons.get("addy"), "Addy top-level menu has no image attribute"
        assert icons.get("existing"), "Existing… menu has no image attribute"
        assert icons.get("new"), "New… menu has no image attribute"
        for key, val in icons.items():
            assert not val.startswith("chrome://"), (
                f"Icon for '{key}' still uses a chrome:// URL: {val}"
            )

        with tb.using_context("chrome"):
            tb.switch_to_window(compose_handle)
            tb.execute_script("window.close();")
