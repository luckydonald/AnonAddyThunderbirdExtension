"""
Marionette tests for the compose-window toolbar popup (composePopup.html).

Flow:
  1. Open a compose window via Thunderbird's compose API.
  2. Add user@example.com as a To: recipient.
  3. Click the Addy toolbar button.
  4. Switch context to the popup window.
  5. Assert RecipientCard renders with the correct address.
  6. Select an existing alias from the fixture.
  7. Click Apply and assert the To: field is rewritten to forwarding format.
"""

import json
import time

import pytest
from marionette_driver.by import By
from marionette_driver.wait import Wait


RECIPIENT = "user@example.com"
# From fixtures: shop@anonaddy.me — active, description matches "example.com"
ALIAS_EMAIL = "shop@anonaddy.me"


def open_compose_window(client):
    """Open a new compose window and return its window handle."""
    before = set(client.window_handles)
    client.execute_script(
        "messenger.compose.beginNew(null, { to: [arguments[0]] });",
        script_args=[RECIPIENT],
    )
    Wait(client, timeout=10).until(
        lambda _: len(set(client.window_handles) - before) > 0
    )
    new_handles = set(client.window_handles) - before
    return new_handles.pop()


def find_popup_window(client):
    """Return the window handle for the composePopup page, if open."""
    for handle in client.window_handles:
        client.switch_to_window(handle)
        try:
            url = client.execute_script("return window.location.href;")
            if "composePopup" in url:
                return handle
        except Exception:
            pass
    return None


@pytest.mark.usefixtures("tb")
class TestPopup:
    def test_popup_opens_and_shows_recipient(self, tb):
        compose_handle = open_compose_window(tb)
        tb.switch_to_window(compose_handle)

        # Click the Addy compose_action button. Thunderbird exposes it in the toolbar.
        tb.execute_script(
            "messenger.composeAction.openPopup({ windowId: messenger.windows.getCurrent().id });"
        )
        time.sleep(2)

        popup_handle = find_popup_window(tb)
        assert popup_handle is not None, "Popup window did not open"

        tb.switch_to_window(popup_handle)
        Wait(tb, timeout=10).until(
            lambda _: tb.find_elements(By.CSS_SELECTOR, ".recipient-card")
        )

        cards = tb.find_elements(By.CSS_SELECTOR, ".recipient-card")
        assert len(cards) >= 1
        card_text = cards[0].text
        assert "example.com" in card_text.lower()

    def test_apply_rewrites_to_field(self, tb):
        compose_handle = open_compose_window(tb)
        tb.switch_to_window(compose_handle)

        tb.execute_script(
            "messenger.composeAction.openPopup({ windowId: messenger.windows.getCurrent().id });"
        )
        time.sleep(2)

        popup_handle = find_popup_window(tb)
        assert popup_handle is not None

        tb.switch_to_window(popup_handle)
        Wait(tb, timeout=10).until(
            lambda _: tb.find_elements(By.CSS_SELECTOR, ".recipient-card")
        )

        # Select the alias radio/button for ALIAS_EMAIL
        alias_btns = tb.find_elements(
            By.XPATH, f"//*[contains(text(), '{ALIAS_EMAIL}')]"
        )
        assert alias_btns, f"Alias {ALIAS_EMAIL} not found in popup"
        alias_btns[0].click()

        # Click Apply
        apply_btn = tb.find_element(By.CSS_SELECTOR, "button.apply-btn, [data-action='apply']")
        apply_btn.click()

        time.sleep(1)
        tb.switch_to_window(compose_handle)

        details = tb.execute_script(
            "return messenger.compose.getComposeDetails(messenger.tabs.getCurrent().id);"
        )
        to_addresses = details.get("to", [])
        assert any("shop+" in addr and "=example.com@anonaddy.me" in addr for addr in to_addresses), (
            f"Forwarding address not found in To: {to_addresses}"
        )
