› /plan Implement a python script for @ai/template/by-feature/git_remote_fix/init.md
› Name it `git_remote_fix` though, copy your plan to @ai/template/by-feature/git_remote_fix/plan.md , then continue implementing `git_remote_fix.py`.
› Commit after milestones and steps done, format '[base] ai: run: <message>'. Rather do many commits than too little.

› I moved the tests for that script into ai/scripts/tests, document with a README.md in that folder how to launch it.

› Write TTD tests:
1. The name field and select and check all/none should be all reachable via up/down move as well
2. start with input focus at name field (last character upon focus)
3. There's 2 spaces too much after the username, the ending `│` is two chars to much to the right.
4. down arrow goes to multi-select
5. up arrow from top multi-select goes back to username field
6. up arrow in multi-select should to the next item, scroll if needed
7. scrollable area is git username edit field and the multiselect, only excluding the gray hotkey footer (Tab focus, Up/down move, …)
8. The indicator has correct color
9. Wrong color for `code` stuff (i.e. `.git` or `<remote name>` are wrongly blue; should be highlight color [aka. pink])
10. Wrong color for active checkboxes (are in green/aqua; should be highlight color [aka. pink])
11. do not colorize _partial_ and _disabled_ icons, unless focused.
12. do not colorize parent selection icons, unless directly focused.
13. down arrow from last multi-select item goes to Check all (indicator moves there too.)
14. the `▎` / `▁` indicator (`ai/template/by-feature/git_remote_fix/init.md`, _cursor blink_ sections) are not implemented it seems.
15. That cursor (and when blink is off, the character there) shall be colored in the highlight color (pink)
16. The icons of check all/none should not be colorized if not focused.
17. between `Check all` and `Check none` should not be an empty line.
18. Tab and shift-tab to switch between input groups is good, keep.
19. The `a check all`, `n check none`, `q cancel` should not be available (= not shown or strikethrough) when in the text edit field.
20. The text edit border color on focus is green/aqua, not pink (highlight).
21. write the key codes as `tab)  focus`, `A)  check all`, `Q|ESC)  cancel`, `Enter) next element/submit` etc.
22. Enter in the text field shall go to the multi-select, too.
23. Shortly (`0.25s`) invert hotkeys upon clicking them, like the macOS menu bar does.
