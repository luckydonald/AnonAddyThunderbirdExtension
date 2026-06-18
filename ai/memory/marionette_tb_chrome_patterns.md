---
name: marionette-tb-chrome-patterns
description: "Empirically verified Thunderbird/Marionette interaction patterns — chrome context, window handles, compose, extension popup OOP bridging, storage injection"
metadata:
    node_type: memory
    type: project
    originSessionId: b3c2110f-ae97-47f6-bf3d-647bd0eaab60
---

## All TB windows are XUL chrome windows

- `client.window_handles` always returns `[]` — there are no content windows.
- Use `client.chrome_window_handles` and `client.switch_to_window(handle)` exclusively.
- All `execute_script` calls must be wrapped with `with client.using_context("chrome"):`.

## Window types (windowtype attribute)

| windowtype            | Description             |
| --------------------- | ----------------------- |
| `mail:3pane`          | Main Thunderbird window |
| `msgcompose`          | Compose window          |
| `mail:extensionPopup` | Extension toolbar popup |

## Opening a compose window

`messenger.compose.beginNew()` does NOT work from Marionette chrome context — `messenger` is
the XPCOM `nsIMessenger` mail service, not the WebExtension API.

**Correct approach:**

```python
before = set(client.chrome_window_handles)
with client.using_context("chrome"):
    client.execute_script(
        "Services.wm.getMostRecentWindow('mail:3pane').MsgNewMessage(null);"
    )
Wait(client, timeout=15).until(
    lambda _: len(set(client.chrome_window_handles) - before) > 0
)
new_handle = (set(client.chrome_window_handles) - before).pop()
```

## Adding a recipient pill

The To: field ID is `toAddrInput`. Send the email + RETURN to create a pill:

```python
with client.using_context("chrome"):
    field = client.find_element(By.ID, "toAddrInput")
    field.send_keys(email + Keys.RETURN)
```

## Addy toolbar button ID

`anonaddytb_luckydonald_de-composeAction-toolbarbutton`

## Extension popup is OOP (out-of-process)

`mail:extensionPopup` contains `<browser id="requestFrame" isRemote=True>`.
`contentDocument` and `contentWindow` are null from chrome context. `switch_to_frame`
does not work for XUL remote browser elements.

**Bridge via messageManager frameScript:**

```python
client.switch_to_window(popup_handle)
with client.using_context("chrome"):
    result = client.execute_script("""
        return new Promise((resolve) => {
            const frame = document.getElementById("requestFrame");
            const mm = frame.messageManager;
            const topic = "_mtest_" + Date.now();
            mm.addMessageListener(topic, (msg) => {
                mm.removeMessageListener(topic, arguments.callee);
                resolve(msg.data);
            });
            mm.loadFrameScript("data:text/javascript," +
                encodeURIComponent(`sendAsyncMessage("${topic}", { value: YOUR_EXPR });`),
                false);
            setTimeout(() => resolve({ timeout: true }), 5000);
        });
    """)
```

## Chip (address pill) context menu

`mail-address-pill` elements are in the compose chrome document.
Trigger right-click via dispatched MouseEvent:

```javascript
const pill = document.querySelector("mail-address-pill");
pill.dispatchEvent(
    new MouseEvent("contextmenu", {
        bubbles: true,
        cancelable: true,
        button: 2,
    }),
);
```

The experiment injects XUL `<menu>` and `<menuitem>` elements into the popup.
Find them with `document.querySelectorAll("menuitem, menu")` and check `getAttribute("label")`.

## Closing a chrome window

```python
with client.using_context("chrome"):
    client.switch_to_window(handle)
    client.execute_script("window.close();")
```

## Extension storage injection (browser.storage.local)

MV3 extensions use IndexedDB. Write via `ExtensionStorageIDB` from chrome context:

```javascript
const { ExtensionStorageIDB } = ChromeUtils.importESModule(
    "resource://gre/modules/ExtensionStorageIDB.sys.mjs",
);
const policy = WebExtensionPolicy.getByID("AnonAddyTB@luckydonald.de");
const principal = ExtensionStorageIDB.getStoragePrincipal(policy.extension);
const db = await ExtensionStorageIDB.open(principal);
await db.set({ options: { hostUrl: "http://...", apiKey: "test-key" } });
```

Verified working — returns the stored JSON when read back immediately.

## setTimeout / clearTimeout in experiment (privileged JS)

Not in global scope in `implementation.js`. Must import:

```javascript
var { setTimeout, clearTimeout } = ChromeUtils.importESModule(
    "resource://gre/modules/Timer.sys.mjs",
);
```

## Shadow DOM / composedPath

Address pills are custom elements. Use `e.composedPath()` to find across shadow DOM:

```javascript
e.composedPath().find(
    (el) => el.tagName?.toLowerCase() === "mail-address-pill",
);
```

`closest()` does not cross shadow-DOM boundaries.

## Thunderbird's onPillPopupShowing crash

TB registers `onpopupshowing="onPillPopupShowing(event)"` which bubbles for every
menupopup opening and crashes when `popup.triggerNode` is not a pill.
Fix: add a bubbling `stopPropagation()` listener on the top-level injected menuPopup.
