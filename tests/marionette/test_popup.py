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


def switch_to_main_window(client):
    """Switch to Thunderbird's main 3pane chrome window and mail tab."""
    with client.using_context("chrome"):
        for handle in client.chrome_window_handles:
            client.switch_to_window(handle)
            window_type = client.execute_script(
                "return document.documentElement.getAttribute('windowtype');"
            )
            if window_type == "mail:3pane":
                client.execute_script(
                    """
                    const tabmail = document.getElementById("tabmail");
                    const tabs = tabmail?.tabInfo || [];
                    const mailTab = tabs.find((tab) =>
                        ["folder", "mail3PaneTab"].includes(tab.mode?.name)
                    );
                    if (mailTab) tabmail.switchToTab(mailTab);
                    """
                )
                return handle
    raise RuntimeError("No Thunderbird main 3pane window found")


def open_compose_window(client):
    """Open a new compose window using TB's native API and return its chrome handle."""
    switch_to_main_window(client)
    before = set(handles_by_window_type(client, "msgcompose"))
    switch_to_main_window(client)
    with client.using_context("chrome"):
        client.execute_script(
            """
            const win = window;
            win.focus();
            win.MsgNewMessage(null);
            """
        )
    try:
        new_handles = Wait(client, timeout=5).until(
            lambda _: set(handles_by_window_type(client, "msgcompose")) - before
        )
    except Exception:
        with client.using_context("chrome"):
            client.execute_script(
                """
                const win = window;
                win.focus();
                if (typeof win.goDoCommand === "function") {
                    win.goDoCommand("cmd_newMessage");
                    return;
                }
                const controller =
                    win.document.commandDispatcher.getControllerForCommand("cmd_newMessage");
                if (!controller) throw new Error("No cmd_newMessage controller");
                controller.doCommand("cmd_newMessage");
                """
            )
        new_handles = Wait(client, timeout=15).until(
            lambda _: set(handles_by_window_type(client, "msgcompose")) - before
        )
    return new_handles.pop()


def handles_by_window_type(client, window_type: str):
    """Return chrome handles whose documentElement windowtype matches."""
    handles = []
    with client.using_context("chrome"):
        for handle in client.chrome_window_handles:
            try:
                client.switch_to_window(handle)
                current = client.execute_script(
                    "return document.documentElement.getAttribute('windowtype');"
                )
            except Exception:
                continue
            if current == window_type:
                handles.append(handle)
    return handles


def add_recipient(client, compose_handle, email):
    """Type a recipient into the compose window's To: field to create a pill."""
    client.switch_to_window(compose_handle)
    with client.using_context("chrome"):
        Wait(client, timeout=10).until(
            lambda _: client.execute_script(
                """
                return !!document.getElementById("toAddrInput") ||
                    !!document.querySelector("mail-address-row input");
                """
            )
        )
        field = client.find_element(By.CSS_SELECTOR, "#toAddrInput, mail-address-row input")
        field.click()
        field.send_keys(email)
        field.send_keys(Keys.RETURN)
        Wait(client, timeout=10).until(
            lambda _: client.execute_script(
                """
                const expected = arguments[0].toLowerCase();
                return [...document.querySelectorAll("mail-address-pill")]
                    .some((pill) =>
                        ((pill.getAttribute("emailAddress") ||
                          pill.getAttribute("fullAddress") ||
                          pill.textContent || "").toLowerCase()).includes(expected)
                    );
                """,
                script_args=[email],
            )
        )
    time.sleep(0.2)


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
                mm.loadFrameScript(
                    "data:text/javascript," + encodeURIComponent(
                        `try {
                            var result = (${arguments[0]});
                            sendAsyncMessage("${topic}", { value: result });
                        } catch(e) {
                            sendAsyncMessage("${topic}", { err: String(e) });
                        }`
                    ), false);
                setTimeout(() => resolve({ timeout: true }), 5000);
            });
            """,
            script_args=[js_expr],
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
                        if (el) {
                            if (el instanceof content.HTMLInputElement &&
                                (el.type === "radio" || el.type === "checkbox")) {
                                el.checked = true;
                                el.dispatchEvent(new content.Event("input", { bubbles: true }));
                                el.dispatchEvent(new content.Event("change", { bubbles: true }));
                                sendAsyncMessage("${topic}", { clicked: true });
                            } else {
                                el.click();
                                sendAsyncMessage("${topic}", { clicked: true });
                            }
                        }
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
            "content.document.querySelectorAll('.card').length"
        )
        assert result.get("value", 0) >= 1, f"No recipient cards in popup: {result}"

        # Check card shows the domain
        card_address = popup_query(
            tb, popup_handle,
            "content.document.querySelector('.card__address-input')?.value || ''"
        )
        assert "example.com" in (card_address.get("value") or "").lower(), (
            f"Recipient domain not shown in card address: {card_address}"
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
            f"input[value='{ALIAS_EMAIL}']"
        )
        assert select_result.get("clicked"), f"Could not select alias: {select_result}"
        time.sleep(0.3)
        selection_state = popup_query(
            tb,
            popup_handle,
            f"""({{
                checked: content.document.querySelector("input[value='{ALIAS_EMAIL}']")?.checked,
                applyDisabled: content.document.querySelector(".footer__actions button.primary")?.disabled,
            }})""",
        )
        assert selection_state.get("value", {}).get("checked"), selection_state
        assert not selection_state.get("value", {}).get("applyDisabled"), selection_state

        # Click Apply button
        apply_result = popup_click(tb, popup_handle, ".footer__actions button.primary")
        assert apply_result.get("clicked"), f"Could not click Apply: {apply_result}"
        time.sleep(1.5)

        # Verify compose To: field was rewritten
        tb.switch_to_window(compose_handle)
        with tb.using_context("chrome"):
            to_pills = tb.execute_script(
                """
                return Array.from(
                    document.querySelectorAll("mail-address-pill")
                ).map(p =>
                    p.getAttribute("emailAddress") ||
                    p.getAttribute("fullAddress") ||
                    p.textContent
                );
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
