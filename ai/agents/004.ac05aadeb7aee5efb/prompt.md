Implement an SMTP capture harness for the Thunderbird Marionette test suite at `/home/user/git/luckydonald/AnonAddyThunderbirdExtension/tests/marionette/`. The goal: verify that when the Addy extension rewrites compose recipients, the actual SMTP delivery uses the forwarding address (`alias+local=domain@aliasdomain`), NOT the original recipient. This exercises the "mail → mail" pill label scenario where the visual label differs from the real send address.

## Context

- `conftest.py` — session fixture that builds the XPI, writes a `user.js` TB profile, launches Thunderbird with Marionette, and injects extension storage. The `tb` fixture depends on `mock_server_port` (an int). Thunderbird is launched once per session; user.js is written before launch.
- `mock_server.py` — minimal HTTP server for the addy.io API (already working).
- `test_popup.py` / `test_chip_menu.py` — existing Marionette tests (do NOT modify them).
- The popup's Apply button calls `messenger.compose.setComposeDetails()` to replace the To field with the forwarding address. The experiment also decorates the pill label visually (e.g. "alias@anon.email → user@example.com") but does NOT touch `emailAddress`/`fullAddress` attributes — those remain the real forwarding address.

## What to build

### 1. `tests/marionette/smtp_harness.py` — new file

A threaded SMTP capture server. It:
- Binds to `127.0.0.1:0` (random port)
- Accepts SMTP connections
- Speaks enough SMTP (EHLO, MAIL, RCPT, DATA, QUIT) to satisfy Thunderbird
- Does NOT require authentication (`authMethod=0`)
- Captures each received message into `self.messages` as a dict with keys: `mail_from`, `rcpt_to` (list), `to_header` (str from parsed headers), `cc_header`, `subject`, `raw` (decoded str)
- Exposes `start() -> int` (returns port), `wait_for_message(timeout=20.0) -> dict|None`, `clear()`, `shutdown()`

Key SMTP notes:
- After 354, accumulate bytes until `\r\n.\r\n` appears in the buffer (that's the end-of-DATA marker)
- Undo dot-stuffing (lines starting with `..` → `.`)
- Use `email.parser.BytesParser().parsebytes()` to extract headers
- Send `250-localhost\r\n250 SIZE 10485760\r\n` in response to EHLO (two lines, NOT one call to send)
- Use buffered reads: maintain a `self._buf: bytes` and drain it per-line

### 2. `tests/marionette/conftest.py` — modify

Add:
```python
import smtp_harness

@pytest.fixture(scope="session")
def smtp_server():
    server = smtp_harness.SMTPCaptureServer()
    server.start()
    yield server
    server.shutdown()
```

Modify the `tb` fixture signature to also accept `smtp_server`:
```python
@pytest.fixture(scope="session")
def tb(mock_server_port, smtp_server, tmp_path_factory):
```

Add these lines to the `user_js.write_text(...)` call (inside the multi-line string, before the closing quote):
```
f'user_pref("mail.smtpservers", "smtp1");\n'
f'user_pref("mail.smtp.defaultserver", "smtp1");\n'
f'user_pref("mail.smtpserver.smtp1.hostname", "127.0.0.1");\n'
f'user_pref("mail.smtpserver.smtp1.port", {smtp_server.port});\n'
f'user_pref("mail.smtpserver.smtp1.authMethod", 0);\n'
f'user_pref("mail.smtpserver.smtp1.auth_method", 0);\n'
f'user_pref("mail.smtpserver.smtp1.socketType", 0);\n'
f'user_pref("mail.smtpserver.smtp1.try_ssl", 0);\n'
f'user_pref("mail.smtpserver.smtp1.description", "Test SMTP Capture");\n'
f'user_pref("mail.identity.id1.smtpServer", "smtp1");\n'
```

**Important:** The `user_js.write_text()` currently uses a plain string with `'...'` - you need to convert it to an f-string concatenation or change the approach to write the smtp prefs. Look at the file carefully before editing.

### 3. `tests/marionette/test_outgoing_smtp.py` — new file

Two test methods in `class TestOutgoingSMTP`:

#### `test_popup_path_forwarding_address_reaches_smtp`
1. `smtp_server.clear()`
2. Open compose, add recipient `user@example.com`, set subject `"Addy SMTP Test - Popup"`
3. Open the toolbar popup (click `anonaddytb_luckydonald_de-composeAction-toolbarbutton`)
4. Wait for popup, select `shop@anonaddy.me` alias via `popup_click(... f"input[value='shop@anonaddy.me']")`
5. Click Apply via `popup_click(... ".footer__actions button.primary")`
6. Wait 1.5 s for `setComposeDetails` to propagate
7. Assert compose pill `emailAddress` attribute now contains `"shop+"` (quick sanity check before send)
8. Trigger send: `GenericSendMessage(0)` in compose window chrome context
9. `msg = smtp_server.wait_for_message(timeout=20)` 
10. Cleanup: close all msgcompose/extensionPopup windows
11. Assert `msg is not None`
12. Assert `"shop+user=example.com@anonaddy.me"` in `msg["rcpt_to"]` (exact match in list)
13. Assert `"user@example.com"` NOT in any of `msg["rcpt_to"]`
14. Assert `"shop+user=example.com@anonaddy.me"` in `msg["to_header"]`
15. Assert `"user@example.com"` not in `msg["to_header"]`

#### `test_chip_menu_path_forwarding_address_reaches_smtp`
1. `smtp_server.clear()`
2. Open compose with recipient `user@example.com`, set subject `"Addy SMTP Test - ChipMenu"`
3. Right-click the pill (dispatch `contextmenu` MouseEvent)
4. Open "addy" submenu, then "existing" submenu, wait for alias label `shop@anonaddy.me`
5. Click that alias menu item
6. Wait for pill rewrite: poll `pill.getAttribute("emailAddress")` until it contains `"shop+"` or timeout 10s
7. Trigger send: `GenericSendMessage(0)`
8. `msg = smtp_server.wait_for_message(timeout=20)`
9. Cleanup
10. Same assertions as popup test

**Utility functions to include** (copy/adapt from existing test files):
- `switch_to_main_window(client)` — from test_popup.py
- `handles_by_window_type(client, window_type)` — from test_popup.py
- `open_compose_window(client)` — from test_popup.py (the one with `MsgNewMessage`)
- `add_recipient(client, compose_handle, email)` — from test_popup.py
- `set_subject(client, compose_handle, subject)` — new: finds `#msgSubject` input, sets its value, dispatches `input` event
- `compose_pill_attrs(client, compose_handle)` — from test_popup.py
- `find_popup_handle(client)` — from test_popup.py
- `popup_query(client, popup_handle, js_expr)` — from test_popup.py
- `popup_click(client, popup_handle, selector)` — from test_popup.py
- `right_click_first_pill(client)` — from test_chip_menu.py (dispatches contextmenu MouseEvent)
- `open_submenu(client, label_fragment)` — from test_chip_menu.py
- `click_menu_item(client, label_fragment)` — from test_chip_menu.py
- `wait_for_alias_label(client, alias_email)` — from test_chip_menu.py
- `wait_for_pill_rewrite(client, compose_handle, expected_fragment, timeout=10)` — new: polls pill `emailAddress` attr
- `send_compose(client, compose_handle)` — new: calls `GenericSendMessage(0)` in chrome context
- `close_all_compose_windows(client)` — new: closes all `msgcompose` and `mail:extensionPopup` windows

**Do NOT use `@pytest.mark.usefixtures("tb")`** — instead let `tb` and `smtp_server` be explicit parameters of each test method so pytest injects both.

## SMTP EHLO response — critical detail

You must send TWO separate SMTP lines for EHLO (not one line with `\r\n` embedded in it). Use:
```python
self._conn.sendall(b"250-localhost\r\n250 SIZE 10485760\r\n")
```
or two separate `sendall` calls. Do NOT do `self._write("250-localhost\r\n250 SIZE 10485760")` if `_write` appends a single `\r\n` — that creates a malformed response.

## Files to read before editing

Read these files fully before writing anything:
- `/home/user/git/luckydonald/AnonAddyThunderbirdExtension/tests/marionette/conftest.py`
- `/home/user/git/luckydonald/AnonAddyThunderbirdExtension/tests/marionette/test_popup.py`
- `/home/user/git/luckydonald/AnonAddyThunderbirdExtension/tests/marionette/test_chip_menu.py`

Do NOT run any tests — just write the three files. Do NOT modify test_popup.py or test_chip_menu.py.