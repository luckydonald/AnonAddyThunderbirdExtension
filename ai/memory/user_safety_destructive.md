---
name: user-safety-destructive
description: "User strongly objects to broad destructive commands (pkill, rm -rf, etc.) hitting processes/files they own unless explicitly authorized first"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: b3c2110f-ae97-47f6-bf3d-647bd0eaab60
---

Never use broad `pkill -f thunderbird` or similar commands that could kill the user's
own running Thunderbird instance. Only kill known subprocess PIDs (e.g. `proc.terminate()`
on the PID we launched).

**Why:** Claude accidentally killed the user's personal Thunderbird session with
`pkill -f thunderbird` while trying to clean up test processes. User was upset: "HEY YOU
JUST KILLED MY THUNDERBIRD, TOO!" This caused loss of their work in progress.

**How to apply:** For any kill/terminate command, scope it to specific PIDs. If a broad
kill is genuinely needed, ask the user first and wait for explicit authorization
("alright you can kill all thunderbird" counts as explicit auth for that one session
action, but does NOT generalize to future sessions or other process types).
