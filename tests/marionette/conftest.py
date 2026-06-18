"""
pytest session fixtures for Marionette-driven Thunderbird tests.

Prerequisites:
  - Thunderbird installed; path in THUNDERBIRD_BIN env var (default: "thunderbird")
  - uv available; run via: uv run pytest

The fixture:
  1. Builds the .xpi (runs make at repo root)
  2. Starts the addy.io mock HTTP server
  3. Launches Thunderbird with a temp profile and --marionette flag
  4. Installs the extension
  5. Injects options (hostUrl + apiKey) into extension storage
  6. Yields the Marionette client
"""

import os
import shlex
import subprocess
import time
from pathlib import Path

import pytest
from marionette_driver.marionette import Marionette

import mock_server as mock_server_mod

REPO_ROOT = Path(__file__).parent.parent.parent
XPI_PATH = REPO_ROOT / "AnonAddyTB.xpi"
# Supports plain paths ("thunderbird", "/usr/bin/thunderbird") and
# multi-word commands ("flatpak run org.mozilla.Thunderbird").
THUNDERBIRD_CMD = shlex.split(os.environ.get("THUNDERBIRD_BIN", "thunderbird"))


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

    # Enable Marionette via profile prefs
    user_js = profile_dir / "user.js"
    user_js.write_text(
        'user_pref("marionette.enabled", true);\n'
        'user_pref("marionette.port", 2828);\n'
    )

    proc = subprocess.Popen(
        THUNDERBIRD_CMD + ["--marionette", "--no-remote", "--profile", str(profile_dir)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Wait for Thunderbird to start and open its Marionette socket
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

    # Install the extension (temp=True so it survives without signing)
    client.addon_install(str(XPI_PATH), temp=True)
    time.sleep(2)  # give the extension a moment to initialize

    # Inject extension storage: point hostUrl at mock server, set a dummy apiKey.
    # We execute a script in the first available browser window that has
    # access to the browser.storage API.
    host_url = f"http://127.0.0.1:{mock_server_port}"
    client.execute_script(
        """
        browser.storage.local.set({
            options: { hostUrl: arguments[0], apiKey: "test-key" }
        });
        """,
        script_args=[host_url],
    )

    yield client

    client.cleanup()
    proc.terminate()
    proc.wait(timeout=10)
