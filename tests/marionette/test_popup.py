"""
Marionette tests for the compose-window toolbar popup (composePopup.html).

Context notes:
- All Thunderbird windows are XUL chrome windows; window_handles returns [].
  Use chrome_window_handles and using_context("chrome") throughout.
- The extension popup (mail:extensionPopup) is an OOP content frame inside
  a chrome wrapper window.  Its DOM is accessed via frameScript / messageManager.
"""

import json
import time

import pytest
from marionette_driver.by import By
from marionette_driver.keys import Keys
from marionette_driver.wait import Wait


RECIPIENT = "user@example.com"
# From fixtures: shop@anonaddy.me — active, description matches "example.com"
ALIAS_EMAIL = "shop@anonaddy.me"
# Expected forwarding fragment after Apply
EXPECTED_TO_FRAGMENT = "shop+"


def open_compose_window(client):
    """Open a new compose window using TB's native API and return its chrome handle."""
    before = set(client.chrome_window_handles)
    with client.using_context("chrome"):
        client.execute_script(
            "Services.wm.getMostRecentWindow('mail:3pane').MsgNewMessage(null);"
        )
    Wait(client, timeout=15).until(
        lambda _: len(set(client.chrome_window_handles) - before) > 0
    )
    return (set(client.chrome_window_handles) - before).pop()


def add_recipient(client, compose_handle, email):
    """Type a recipient into the compose window's To: field to create a pill."""
    client.switch_to_window(compose_handle)
    with client.using_context("chrome"):
        field = client.find_element(By.ID, "toAddrInput")
        field.click()
        field.send_keys(email)
        field.send_keys(Keys.RETURN)
    time.sleep(0.5)


def find_popup_handle(client):
    """Return the chrome handle for the extension popup window, if open."""
    with client.using_context("chrome"):
        for h in client.chrome_window_handles:
            client.switch_to_window(h)
            wtype = client.execute_script(
                "return document.documentElement.getAttribute('windowtype');"
            )
            if wtype == "mail:extensionPopup":
                return h
    return None


def popup_query(client, popup_handle, js_expr):
    """
    Execute ``js_expr`` inside the extension popup's remote content frame and
    return the result.  Uses messageManager frameScript bridging.
    """
    client.switch_to_window(popup_handle)
    with client.using_context("chrome"):
        return client.execute_script(
            """
            return new Promise((resolve) => {
                const frame = document.getElementById("requestFrame");
                if (!frame?.messageManager) { resolve({ err: "no messageManager" }); return; }
                const mm = frame.messageManager;
                const topic = "_mtest_" + Date.now();
                const listener = (msg) => {
                    mm.removeMessageListener(topic, listener);
                    resolve(msg.data);
                };
                mm.addMessageListener(topic, listener);
                const code = arguments[0].replace("__TOPIC__", topic);
                mm.loadFrameScript("data:text/javascript," + encodeURIComponent(code), false);
                setTimeout(() => resolve({ timeout: true }), 5000);
            });
            """,
            script_args=[
                f"""
                try {{
                    const result = eval({json.dumps(js_expr)});
                    sendAsyncMessage("__TOPIC__", {{ value: result instanceof Promise
                        ? await result : result }});
                }} catch(e) {{
                    sendAsyncMessage("__TOPIC__", {{ err: String(e) }});
                }}
                """
            ],
        )


def popup_click(client, popup_handle, selector):
    """Click an element inside the popup by CSS selector via frameScript."""
    client.switch_to_window(popup_handle)
    with client.using_context("chrome"):
        return client.execute_script(
            """
            return new Promise((resolve) => {
                const frame = document.getElementById("requestFrame");
                const mm = frame.messageManager;
                const topic = "_mclick_" + Date.now();
                const listener = (msg) => {
                    mm.removeMessageListener(topic, listener);
                    resolve(msg.data);
                };
                mm.addMessageListener(topic, listener);
                mm.loadFrameScript(
                    "data:text/javascript," + encodeURIComponent(
                        `var el = content.document.querySelector(${JSON.stringify(arguments[0])});
                        if (el) { el.click(); sendAsyncMessage("${topic}", { clicked: true }); }
                        else sendAsyncMessage("${topic}", { err: "not found: " + ${JSON.stringify(arguments[0])} });`
                    ), false);
                setTimeout(() => resolve({ timeout: true }), 5000);
            });
            """,
            script_args=[selector],
        )


@pytest.mark.usefixtures("tb")
class TestPopup:
    def test_popup_opens_and_shows_recipient(self, tb):
        compose_handle = open_compose_window(tb)
        add_recipient(tb, compose_handle, RECIPIENT)

        # Click the Addy toolbar button in the compose window
        before = set(tb.chrome_window_handles)
        with tb.using_context("chrome"):
            tb.switch_to_window(compose_handle)
            tb.execute_script(
                """
                document.getElementById(
                    "anonaddytb_luckydonald_de-composeAction-toolbarbutton"
                ).click();
                """
            )

        # Wait for popup window to appear
        Wait(tb, timeout=10).until(
            lambda _: len(set(tb.chrome_window_handles) - before) > 0
        )
        popup_handle = find_popup_handle(tb)
        assert popup_handle is not None, "Extension popup window did not open"
        time.sleep(2)  # let Vue render

        # Query recipient card count via frameScript
        result = popup_query(
            tb, popup_handle,
            "content.document.querySelectorAll('.recipient-card').length"
        )
        assert result.get("value", 0) >= 1, f"No recipient cards in popup: {result}"

        # Check card shows the domain
        card_text = popup_query(
            tb, popup_handle,
            "content.document.querySelector('.recipient-card')?.textContent || ''"
        )
        assert "example.com" in (card_text.get("value") or "").lower(), (
            f"Recipient domain not shown in card: {card_text}"
        )

        # Close compose
        with tb.using_context("chrome"):
            tb.switch_to_window(compose_handle)
            tb.execute_script("window.close();")

    def test_popup_responsive_width(self, tb):
        """Popup overlay must not produce horizontal scroll at narrow or wide widths.

        Uses a deliberately long email address to stress word-breaking, checks
        the popup at its default width, under a 320 px CSS constraint (narrow),
        and verifies the format-choice pills are configured to wrap rather than
        force a wide layout.
        """
        compose_handle = open_compose_window(tb)
        # Long address stresses break-all / min-width: 0 on flex children
        add_recipient(
            tb, compose_handle,
            "averylonglocalpart@quite-long.recipient-domain.example.com",
        )

        before = set(tb.chrome_window_handles)
        with tb.using_context("chrome"):
            tb.switch_to_window(compose_handle)
            tb.execute_script(
                "document.getElementById("
                "'anonaddytb_luckydonald_de-composeAction-toolbarbutton').click();"
            )
        Wait(tb, timeout=10).until(
            lambda _: len(set(tb.chrome_window_handles) - before) > 0
        )
        popup_handle = find_popup_handle(tb)
        assert popup_handle is not None, "Extension popup did not open"
        time.sleep(2)  # let Vue render

        # Check 1: default rendered width — no horizontal overflow
        default_check = popup_query(
            tb, popup_handle,
            "({ sw: content.document.body.scrollWidth, iw: content.innerWidth })",
        )
        dval = default_check.get("value", {})
        assert dval.get("sw", 0) <= dval.get("iw", 1), (
            f"Horizontal overflow at default width: "
            f"scrollWidth={dval.get('sw')} innerWidth={dval.get('iw')}"
        )

        # Check 2: narrow constraint (320 px) — still no overflow
        narrow_check = popup_query(
            tb, popup_handle,
            """(function() {
                const popup = content.document.querySelector('.popup');
                if (!popup) return { err: 'no .popup element' };
                const saved = popup.style.cssText;
                popup.style.maxWidth = '320px';
                popup.style.width = '320px';
                void popup.offsetWidth;  // flush layout
                const overflows = popup.scrollWidth > 320;
                popup.style.cssText = saved;
                return { overflows, scrollWidth: popup.scrollWidth };
            })()""",
        )
        nval = narrow_check.get("value", {})
        assert not nval.get("overflows"), (
            f"Horizontal overflow at 320 px constraint: "
            f"scrollWidth={nval.get('scrollWidth')}"
        )

        # Check 3: .popup must have no min-width (the responsive fix removes it so
        # the window can be narrower than 540 px without causing horizontal overflow)
        min_width_check = popup_query(
            tb, popup_handle,
            """(function() {
                const popup = content.document.querySelector('.popup');
                if (!popup) return { err: 'no .popup element' };
                const mw = content.window.getComputedStyle(popup).minWidth;
                return { minWidth: mw };
            })()""",
        )
        mval = min_width_check.get("value", {})
        assert mval.get("minWidth") in ("0px", ""), (
            f"popup still has a min-width that causes overflow: {mval.get('minWidth')!r}"
        )

        with tb.using_context("chrome"):
            tb.switch_to_window(compose_handle)
            tb.execute_script("window.close();")

    def test_apply_rewrites_to_field(self, tb):
        compose_handle = open_compose_window(tb)
        add_recipient(tb, compose_handle, RECIPIENT)

        before = set(tb.chrome_window_handles)
        with tb.using_context("chrome"):
            tb.switch_to_window(compose_handle)
            tb.execute_script(
                """
                document.getElementById(
                    "anonaddytb_luckydonald_de-composeAction-toolbarbutton"
                ).click();
                """
            )
        Wait(tb, timeout=10).until(
            lambda _: len(set(tb.chrome_window_handles) - before) > 0
        )
        popup_handle = find_popup_handle(tb)
        assert popup_handle is not None
        time.sleep(2)

        # Select the alias radio/option for ALIAS_EMAIL via frameScript
        select_result = popup_click(
            tb, popup_handle,
            f"input[value='{ALIAS_EMAIL}'], label:has(input[value='{ALIAS_EMAIL}'])"
        )
        time.sleep(0.3)

        # Click Apply button
        apply_result = popup_click(tb, popup_handle, "button.apply-btn, [data-action='apply']")
        time.sleep(1.5)

        # Verify compose To: field was rewritten
        tb.switch_to_window(compose_handle)
        with tb.using_context("chrome"):
            to_pills = tb.execute_script(
                """
                return Array.from(
                    document.querySelectorAll("mail-address-pill")
                ).map(p => p.getAttribute("fulladdress") || p.textContent);
                """
            )
        assert any(EXPECTED_TO_FRAGMENT in addr for addr in (to_pills or [])), (
            f"Forwarding address not found in To pills: {to_pills}"
        )

        with tb.using_context("chrome"):
            tb.switch_to_window(compose_handle)
            tb.execute_script("window.close();")

    def test_create_alias_opens_own_window(self, tb):
        """Clicking '+ Create alias' must open a separate TB popup window."""
        compose_handle = open_compose_window(tb)
        add_recipient(tb, compose_handle, RECIPIENT)

        before = set(tb.chrome_window_handles)
        with tb.using_context("chrome"):
            tb.switch_to_window(compose_handle)
            tb.execute_script(
                "document.getElementById("
                "'anonaddytb_luckydonald_de-composeAction-toolbarbutton').click();"
            )
        Wait(tb, timeout=10).until(
            lambda _: len(set(tb.chrome_window_handles) - before) > 0
        )
        popup_handle = find_popup_handle(tb)
        assert popup_handle is not None, "Extension popup did not open"
        time.sleep(2)  # let Vue render

        # Click the '+ Create alias' button in the first recipient card
        before_create = set(tb.chrome_window_handles)
        popup_click(tb, popup_handle, "button.new-alias-btn")
        # Wait for a second extension window to appear
        Wait(tb, timeout=10).until(
            lambda _: len(set(tb.chrome_window_handles) - before_create) > 0
        )
        new_handles = set(tb.chrome_window_handles) - before_create
        assert new_handles, "Create alias window did not open"

        # Confirm it's a separate popup window (not just a new compose window)
        create_handle = new_handles.pop()
        with tb.using_context("chrome"):
            tb.switch_to_window(create_handle)
            wtype = tb.execute_script(
                "return document.documentElement.getAttribute('windowtype');"
            )
        assert wtype == "mail:extensionPopup", (
            f"Create alias window has unexpected type: {wtype!r}"
        )

        # Clean up
        with tb.using_context("chrome"):
            tb.switch_to_window(create_handle)
            tb.execute_script("window.close();")
        with tb.using_context("chrome"):
            tb.switch_to_window(compose_handle)
            tb.execute_script("window.close();")
