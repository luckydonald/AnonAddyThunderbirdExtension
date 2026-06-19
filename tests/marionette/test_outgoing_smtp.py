"""
Marionette tests asserting that alias substitution (both popup and chip-menu paths)
produces SMTP deliveries addressed to the forwarding address — NOT to the original
recipient.

These tests exercise the "mail → mail" scenario: the pill label is decorated with a
human-readable "alias → original" string, but the actual outgoing address must be
the aliasLocal+recipientLocal=recipientDomain@aliasDomain forwarding format.

A real SMTP capture server (smtp_harness.SMTPCaptureServer) receives the mail so
we can inspect both the RCPT TO envelope and the To: header.
"""

import contextlib
import time

from marionette_driver.by import By
from marionette_driver.keys import Keys
from marionette_driver.wait import Wait


RECIPIENT = "user@example.com"
ALIAS_EMAIL = "shop@anonaddy.me"
# Expected forwarding address after Apply / alias selection
FORWARDING_ADDRESS = "shop+user=example.com@anonaddy.me"


# ─── Compose-window helpers ────────────────────────────────────────────────────


def switch_to_main_window(client):
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


def handles_by_window_type(client, window_type: str):
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


def open_compose_window(client):
    """Open a new blank compose window and return its chrome handle."""
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


def add_recipient(client, compose_handle, email):
    """Type a recipient into the To: field and wait for the pill to appear."""
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


def set_subject(client, compose_handle, subject):
    """Set the compose window subject field."""
    client.switch_to_window(compose_handle)
    with client.using_context("chrome"):
        client.execute_script(
            """
            const field = document.getElementById("msgSubject");
            if (field) {
                field.value = arguments[0];
                field.dispatchEvent(new Event("input", { bubbles: true }));
                field.dispatchEvent(new Event("change", { bubbles: true }));
            }
            """,
            script_args=[subject],
        )


def compose_pill_attrs(client, compose_handle):
    client.switch_to_window(compose_handle)
    with client.using_context("chrome"):
        return client.execute_script(
            """
            const pill = document.querySelector("mail-address-pill");
            if (!pill) return null;
            return {
                emailAddress: pill.getAttribute("emailAddress") || "",
                fullAddress: pill.getAttribute("fullAddress") || "",
                label: pill.getAttribute("label") || "",
                text: pill.textContent || "",
            };
            """
        )


def find_popup_handle(client):
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


def right_click_first_pill(client, compose_handle):
    """Dispatch a contextmenu event on the first mail-address-pill."""
    client.switch_to_window(compose_handle)
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
    time.sleep(0.7)


def open_submenu(client, compose_handle, menu_label_fragment: str):
    client.switch_to_window(compose_handle)
    with client.using_context("chrome"):
        result = client.execute_script(
            """
            const frag = arguments[0].toLowerCase();
            for (const tag of ["menu", "menuitem"]) {
                for (const el of document.querySelectorAll(tag)) {
                    const lbl = (el.getAttribute("label") || el.textContent || "").toLowerCase();
                    if (lbl.includes(frag)) {
                        if (typeof el.openMenu === "function") el.openMenu(true);
                        else el.click();
                        return true;
                    }
                }
            }
            return false;
            """,
            script_args=[menu_label_fragment],
        )
    time.sleep(0.3)
    return result


def click_menu_item(client, compose_handle, label_fragment: str):
    client.switch_to_window(compose_handle)
    with client.using_context("chrome"):
        return client.execute_script(
            """
            const frag = arguments[0].toLowerCase();
            const root = [...document.querySelectorAll("menu")]
                .find((el) => (el.getAttribute("label") || "") ===
                    "Use Addy alias for sending");
            const items = root
                ? root.querySelectorAll("menuitem")
                : document.querySelectorAll("menuitem");
            for (const it of items) {
                const lbl = (it.getAttribute("label") || it.textContent || "").toLowerCase();
                if (lbl.includes(frag) && typeof it._addyRunCommand === "function") {
                    it._addyRunCommand();
                    return true;
                }
            }
            for (const it of items) {
                const lbl = (it.getAttribute("label") || it.textContent || "").toLowerCase();
                if (lbl.includes(frag)) {
                    it.dispatchEvent(new Event("command", { bubbles: true, cancelable: true }));
                    if (typeof it.doCommand === "function") it.doCommand();
                    it.click();
                    return true;
                }
            }
            return false;
            """,
            script_args=[label_fragment],
        )


def wait_for_alias_label(client, compose_handle, alias_email: str):
    """Wait until the alias email appears as a menuitem label in the compose doc."""
    last_labels = []
    deadline = time.time() + 10
    while time.time() < deadline:
        client.switch_to_window(compose_handle)
        with client.using_context("chrome"):
            last_labels = client.execute_script(
                """
                const root = [...document.querySelectorAll("menu")]
                    .find((el) => (el.getAttribute("label") || "") ===
                        "Use Addy alias for sending");
                const items = root
                    ? root.querySelectorAll("menuitem")
                    : document.querySelectorAll("menuitem");
                return [...items]
                    .map((it) => it.getAttribute("label") || "")
                    .filter((label) =>
                        label.includes("@anonaddy.me") ||
                        label.includes("@anon.email")
                    );
                """
            )
        if alias_email in last_labels:
            return last_labels
        time.sleep(0.1)
    raise AssertionError(
        f"Alias {alias_email} not visible in Existing submenu after 10 s. "
        f"Last labels seen: {last_labels}"
    )


def wait_for_pill_rewrite(client, compose_handle, expected_fragment: str, timeout: float = 10):
    """Poll the compose pill emailAddress until it contains expected_fragment."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        attrs = compose_pill_attrs(client, compose_handle)
        if attrs and expected_fragment in attrs.get("emailAddress", ""):
            return attrs
        time.sleep(0.2)
    attrs = compose_pill_attrs(client, compose_handle)
    raise AssertionError(
        f"Pill emailAddress did not contain {expected_fragment!r} within {timeout} s. "
        f"Final attrs: {attrs}"
    )


def send_compose(client, compose_handle):
    """Trigger an immediate SMTP send via GenericSendMessage(0) (DeliverNow)."""
    client.switch_to_window(compose_handle)
    with client.using_context("chrome"):
        client.execute_script(
            """
            if (typeof GenericSendMessage === "function") {
                GenericSendMessage(0);
            } else {
                // Fallback: use the send toolbar button
                const btn = document.getElementById("button-send");
                if (btn) btn.click();
            }
            """
        )


def close_all_compose_windows(client):
    """Close all msgcompose and mail:extensionPopup windows."""
    for wtype in ("msgcompose", "mail:extensionPopup"):
        for handle in handles_by_window_type(client, wtype):
            with contextlib.suppress(Exception):
                with client.using_context("chrome"):
                    client.switch_to_window(handle)
                    client.execute_script("window.close();")
    time.sleep(0.5)


# ─── Tests ────────────────────────────────────────────────────────────────────


class TestOutgoingSMTP:
    def test_popup_path_forwarding_address_reaches_smtp(self, tb, smtp_server):
        """Popup Apply → SMTP envelope and To: header must contain the forwarding
        address, never the original recipient."""
        smtp_server.clear()

        compose_handle = open_compose_window(tb)
        add_recipient(tb, compose_handle, RECIPIENT)
        set_subject(tb, compose_handle, "Addy SMTP Test - Popup")

        # Open the toolbar popup
        before_all = set(tb.chrome_window_handles)
        with tb.using_context("chrome"):
            tb.switch_to_window(compose_handle)
            tb.execute_script(
                "document.getElementById("
                "'anonaddytb_luckydonald_de-composeAction-toolbarbutton').click();"
            )
        Wait(tb, timeout=10).until(
            lambda _: len(set(tb.chrome_window_handles) - before_all) > 0
        )
        popup_handle = find_popup_handle(tb)
        assert popup_handle is not None, "Extension popup did not open"
        time.sleep(2)  # let Vue render

        # Select the alias radio button
        select_result = popup_click(tb, popup_handle, f"input[value='{ALIAS_EMAIL}']")
        assert select_result.get("clicked"), f"Could not select alias: {select_result}"
        time.sleep(0.3)

        # Click Apply
        apply_result = popup_click(tb, popup_handle, ".footer__actions button.primary")
        assert apply_result.get("clicked"), f"Could not click Apply: {apply_result}"
        time.sleep(1.5)

        # Sanity-check: pill emailAddress should already carry the forwarding address
        attrs = compose_pill_attrs(tb, compose_handle)
        assert attrs and "shop+" in attrs.get("emailAddress", ""), (
            f"Pill not rewritten before send: {attrs}"
        )

        # Trigger SMTP delivery
        send_compose(tb, compose_handle)

        # Wait for the SMTP harness to capture the message
        msg = smtp_server.wait_for_message(timeout=20)
        close_all_compose_windows(tb)

        assert msg is not None, (
            "SMTP capture server did not receive a message within 20 s — "
            "check that the SMTP prefs point at the test harness port"
        )
        assert FORWARDING_ADDRESS in msg["rcpt_to"], (
            f"Forwarding address not in RCPT TO envelope: {msg['rcpt_to']}"
        )
        assert RECIPIENT not in msg["rcpt_to"], (
            f"Original recipient leaked into RCPT TO envelope: {msg['rcpt_to']}"
        )
        assert FORWARDING_ADDRESS in msg["to_header"], (
            f"Forwarding address not in To: header: {msg['to_header']!r}"
        )
        assert RECIPIENT not in msg["to_header"], (
            f"Original recipient leaked into To: header: {msg['to_header']!r}"
        )

    def test_chip_menu_path_forwarding_address_reaches_smtp(self, tb, smtp_server):
        """Chip-menu alias selection → SMTP envelope and To: header must contain
        the forwarding address, never the original recipient."""
        smtp_server.clear()

        compose_handle = open_compose_window(tb)
        add_recipient(tb, compose_handle, RECIPIENT)
        set_subject(tb, compose_handle, "Addy SMTP Test - ChipMenu")

        # Right-click the pill to open the context menu
        right_click_first_pill(tb, compose_handle)

        # Navigate: Addy → Existing… → alias
        opened = open_submenu(tb, compose_handle, "addy")
        assert opened, "Could not open Addy menu"

        opened2 = open_submenu(tb, compose_handle, "existing")
        assert opened2, "Could not open Existing submenu"

        wait_for_alias_label(tb, compose_handle, ALIAS_EMAIL)

        clicked = click_menu_item(tb, compose_handle, ALIAS_EMAIL)
        assert clicked, f"Could not click alias item '{ALIAS_EMAIL}'"

        # The experiment rewrites the pill asynchronously — poll until it settles
        wait_for_pill_rewrite(tb, compose_handle, "shop+", timeout=10)

        # Trigger SMTP delivery
        send_compose(tb, compose_handle)

        # Wait for the SMTP harness to capture the message
        msg = smtp_server.wait_for_message(timeout=20)
        close_all_compose_windows(tb)

        assert msg is not None, (
            "SMTP capture server did not receive a message within 20 s — "
            "check that the SMTP prefs point at the test harness port"
        )
        assert FORWARDING_ADDRESS in msg["rcpt_to"], (
            f"Forwarding address not in RCPT TO envelope: {msg['rcpt_to']}"
        )
        assert RECIPIENT not in msg["rcpt_to"], (
            f"Original recipient leaked into RCPT TO envelope: {msg['rcpt_to']}"
        )
        assert FORWARDING_ADDRESS in msg["to_header"], (
            f"Forwarding address not in To: header: {msg['to_header']!r}"
        )
        assert RECIPIENT not in msg["to_header"], (
            f"Original recipient leaked into To: header: {msg['to_header']!r}"
        )
