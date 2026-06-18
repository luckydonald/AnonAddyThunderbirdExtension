---
name: marionette-system-access
description: "How to enable Marionette chrome/system access in Thunderbird 151+, including Flatpak-specific setup"
metadata: 
  node_type: memory
  type: project
  originSessionId: b3c2110f-ae97-47f6-bf3d-647bd0eaab60
---

## Two mechanisms must fire simultaneously

`RemoteAgent.allowSystemAccess` is set from `MOZ_REMOTE_ALLOW_SYSTEM_ACCESS` env var
at constructor time (before CLI flag handling), and also from `--remote-allow-system-access`
CLI flag via the `command-line-startup` observer. **Both are required.**

## Native install

```python
tb_args = [
    "--marionette",
    "--remote-allow-system-access",
    "--no-remote",
    "--profile", str(profile_dir),
]
env = {**os.environ, "MOZ_REMOTE_ALLOW_SYSTEM_ACCESS": "1"}
subprocess.Popen(THUNDERBIRD_CMD + tb_args, env=env)
```

## Flatpak install

Flatpak runs TB in a bwrap sandbox with its own env. Use `--env=VAR=VALUE` Flatpak option
to pass env vars into the sandbox, AND `--filesystem=/tmp` for temp profile access.
The outer Python process env also gets the var (belt-and-suspenders).

```python
app_id = THUNDERBIRD_CMD[-1]   # "net.thunderbird.Thunderbird"
flatpak_opts = THUNDERBIRD_CMD[1:-1]   # ["run"] from "flatpak run ..."
cmd = [
    "flatpak",
    *flatpak_opts,
    "--filesystem=/tmp",
    "--env=MOZ_REMOTE_ALLOW_SYSTEM_ACCESS=1",
    app_id,
    "--marionette",
    "--remote-allow-system-access",
    "--no-remote",
    "--profile", str(profile_dir),
]
env = {**os.environ, "MOZ_REMOTE_ALLOW_SYSTEM_ACCESS": "1"}
subprocess.Popen(cmd, env=env)
```

## user.js: no pref needed

There is no `remote.system-access.enabled` pref. Do not add one — it does nothing and
caused confusion. System access is controlled entirely by env var + CLI flag.

## Marionette user.js prefs (required)

```javascript
user_pref("marionette.enabled", true);
user_pref("marionette.port", 2828);
```

## Verified on: Thunderbird 151 (Flatpak net.thunderbird.Thunderbird)
