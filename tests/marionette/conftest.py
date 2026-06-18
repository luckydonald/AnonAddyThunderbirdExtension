"""
pytest session fixtures for Marionette-driven Thunderbird tests.

Prerequisites:
  - Thunderbird installed; path in THUNDERBIRD_BIN env var (default: "thunderbird")
    Flatpak: THUNDERBIRD_BIN="flatpak run net.thunderbird.Thunderbird"
  - uv available; run via: uv run pytest

The fixture:
  1. Builds the .xpi (runs make at repo root)
  2. Starts the addy.io mock HTTP server
  3. Pre-installs the extension and writes a profile with account + Marionette prefs
  4. Launches Thunderbird with --marionette --no-remote
  5. Injects extension storage (hostUrl + apiKey) via the extension's options page
  6. Yields the Marionette client
"""

import json
import os
import shlex
import shutil
import subprocess
import time
from pathlib import Path

import pytest
from marionette_driver.marionette import Marionette

import mock_server as mock_server_mod

REPO_ROOT = Path(__file__).parent.parent.parent
XPI_PATH = REPO_ROOT / "AnonAddyTB.xpi"
EXT_ID = "AnonAddyTB@luckydonald.de"

# Supports plain paths ("thunderbird", "/usr/bin/thunderbird") and
# multi-word commands ("flatpak run net.thunderbird.Thunderbird").
THUNDERBIRD_CMD = shlex.split(os.environ.get("THUNDERBIRD_BIN", "thunderbird"))


def _build_launch_cmd(profile_dir: Path) -> tuple[list[str], dict]:
    """Build the subprocess argv and environment for launching Thunderbird.

    ``MOZ_REMOTE_ALLOW_SYSTEM_ACCESS`` is the env-var that RemoteAgent checks
    at construction time (before CLI flag handling) to enable chrome context.
    We set it in the subprocess env for native installs and via ``--env=`` for
    Flatpak (which uses a separate sandbox env).

    When running via flatpak, also inserts ``--filesystem=/tmp`` so the sandbox
    can access the pytest temp profile directory.
    """
    tb_args = [
        "--marionette",
        "--remote-allow-system-access",
        "--no-remote",
        "--profile",
        str(profile_dir),
    ]
    env = {**os.environ, "MOZ_REMOTE_ALLOW_SYSTEM_ACCESS": "1"}

    if THUNDERBIRD_CMD[0] != "flatpak":
        return THUNDERBIRD_CMD + tb_args, env

    app_id = THUNDERBIRD_CMD[-1]
    flatpak_opts = THUNDERBIRD_CMD[1:-1]
    cmd = [
        "flatpak",
        *flatpak_opts,
        "--filesystem=/tmp",
        "--env=MOZ_REMOTE_ALLOW_SYSTEM_ACCESS=1",
        app_id,
        *tb_args,
    ]
    return cmd, env


def _wait_for_window(client: Marionette, timeout: int = 30) -> None:
    """Switch to the first available chrome window, retrying until one exists.

    Thunderbird's main window is a XUL chrome window — it appears in
    ``chrome_window_handles``, not the content-only ``window_handles``.
    """
    for _ in range(timeout):
        handles = client.chrome_window_handles
        if handles:
            client.switch_to_window(handles[0])
            return
        time.sleep(1)
    raise RuntimeError("No Thunderbird window became available within timeout")


@pytest.fixture(scope="session")
def mock_server_port():
    server, port = mock_server_mod.start()
    yield port
    server.shutdown()


@pytest.fixture(scope="session")
def tb(mock_server_port, tmp_path_factory):
    # Build the extension
    subprocess.run(["make"], cwd=REPO_ROOT, check=True, capture_output=True)

    profile_dir = tmp_path_factory.mktemp("tb-profile")

    # Pre-install extension by dropping .xpi into extensions/ before launch.
    # The filename must match the extension ID from manifest.json.
    ext_dir = profile_dir / "extensions"
    ext_dir.mkdir()
    shutil.copy(XPI_PATH, ext_dir / f"{EXT_ID}.xpi")

    user_js = profile_dir / "user.js"
    user_js.write_text(
        # Marionette — enable listening socket.
        # Chrome context (system access) is granted via MOZ_REMOTE_ALLOW_SYSTEM_ACCESS
        # in the subprocess environment (set by _build_launch_cmd).
        'user_pref("marionette.enabled", true);\n'
        'user_pref("marionette.port", 2828);\n'
        # Allow unsigned extensions
        'user_pref("xpinstall.signatures.required", false);\n'
        'user_pref("extensions.autoDisableScopes", 0);\n'
        'user_pref("extensions.enabledScopes", 15);\n'
        # Suppress first-run / account setup wizard
        'user_pref("mail.provider.suppress_dialog_on_startup", true);\n'
        'user_pref("mail.spotlight.firstRunDone", true);\n'
        'user_pref("mail.winsearch.firstRunDone", true);\n'
        'user_pref("mailnews.start_page.enabled", false);\n'
        'user_pref("datareporting.healthreport.uploadEnabled", false);\n'
        'user_pref("datareporting.policy.dataSubmissionEnabled", false);\n'
        'user_pref("app.shield.optoutstudies.enabled", false);\n'
        'user_pref("browser.shell.checkDefaultBrowser", false);\n'
        # Minimal local-only account so the compose button is active
        'user_pref("mail.accountmanager.accounts", "account1");\n'
        'user_pref("mail.accountmanager.localfoldersserver", "server1");\n'
        'user_pref("mail.accountmanager.defaultaccount", "account1");\n'
        'user_pref("mail.server.server1.hostname", "Local Folders");\n'
        'user_pref("mail.server.server1.name", "Local Folders");\n'
        'user_pref("mail.server.server1.type", "none");\n'
        'user_pref("mail.server.server1.userName", "nobody");\n'
        'user_pref("mail.account.account1.identities", "id1");\n'
        'user_pref("mail.account.account1.server", "server1");\n'
        'user_pref("mail.identity.id1.fullName", "Test User");\n'
        'user_pref("mail.identity.id1.useremail", "test@example.com");\n'
        'user_pref("mail.identity.id1.valid", true);\n'
    )

    launch_cmd, launch_env = _build_launch_cmd(profile_dir)
    proc = subprocess.Popen(
        launch_cmd,
        env=launch_env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Wait for Marionette socket
    client = None
    for _ in range(30):
        try:
            client = Marionette(host="localhost", port=2828)
            client.start_session()
            break
        except Exception:
            time.sleep(1)
    else:
        proc.terminate()
        pytest.fail("Thunderbird did not start or Marionette did not become available")

    _wait_for_window(client)
    time.sleep(3)  # let extension finish loading

    # Inject extension storage via ExtensionStorageIDB from chrome context.
    # browser.storage.local for MV3 extensions uses IndexedDB.  We write to it
    # directly through the privileged ExtensionStorageIDB module rather than
    # opening the options page (which would require a content browsing context
    # that Thunderbird does not expose to Marionette).
    host_url = f"http://127.0.0.1:{mock_server_port}"
    try:
        with client.using_context("chrome"):
            result = client.execute_script(
                """
                return (async () => {
                    const { ExtensionStorageIDB } = ChromeUtils.importESModule(
                        "resource://gre/modules/ExtensionStorageIDB.sys.mjs"
                    );
                    const policy = WebExtensionPolicy.getByID(arguments[0]);
                    if (!policy) return "no policy";
                    const principal = ExtensionStorageIDB.getStoragePrincipal(policy.extension);
                    const db = await ExtensionStorageIDB.open(principal);
                    await db.set({ options: { hostUrl: arguments[1], apiKey: "test-key" } });
                    const check = await db.get(["options"]);
                    return JSON.stringify(check);
                })();
                """,
                script_args=[EXT_ID, host_url],
            )
        print(f"Storage injection result: {result}")
    except Exception as e:
        # Non-fatal: tests that need storage will fail with a clear message
        print(f"Warning: could not inject extension storage: {e}")

    yield client

    client.cleanup()
    proc.terminate()
    proc.wait(timeout=10)
