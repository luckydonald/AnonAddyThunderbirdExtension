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
24. Add a [ Submit → ] button, as 4th group. Again embedded into the up/down and the tab logic.
25. The submit button is all-colorized (pink) on focus, and inverts for `0.25s` after clicking before we go to the next "page".
26. Use `↑` (`UPWARDS ARROW`) and `↓` (`DOWNWARDS ARROW`) instead of `Up` and `Down` for moveing the focus
27. If in edit field, add `←` (`LEFTWARDS ARROW`) and `→` (`RIGHTWARDS ARROW`) for moving the cursor
28. (Removed)
29. Use `␛` (`SYMBOL FOR ESCAPE`) for escape.
30. Use `MATHEMATICAL MONOSPACE SMALL` characters for alphanumeric-single-char keys, (i.e. for `q` show `𝚚` (`MATHEMATICAL MONOSPACE SMALL Q`: `𝚚`))
31. Use `⏎` (`RETURN SYMBOL`) for Enter
32. Use `⇥` (`RIGHTWARDS ARROW TO BAR`) for Tab
33. Use `⟯` (`MATHEMATICAL RIGHT FLATTENED PARENTHESIS`) instead of the normal `)` between character and label.

> Already better. But there's still stuff to fixx; let's do round 3:
1. Add a `r) refresh` command, which redraws the whole gui, in case something got stuck

> Let's do round 3 of fixes (cont'd):
- remember to start with _Writing and committing TTD tests_
2. I would expect `r` to completely clear the screen and draw it all from scratch, based on the current state.
3. When quickly going past two lines always get stuck displaying something else:
   - a) origin checkbox
     - Directly under `Select the remote urls to change:`
     1) unfocused
        - unfocused should: `     ◎ empty`
        - unfocused actual: `⋑      e◎ ty`
     2) focused
        - focused should: `⋑    ◎ empty`
        - focused actual: `⋑    ◎ e◎ ty`
     - Both issues appear after passing over it once.
   - b) check all
     - The first of the two
     - but not "check none"
     1) unfocused
        - unfocused should: `    ◉ Check all`
        - unfocused actual: `⋑      h◉ Check all`
     2) focused
        - focused should: `⋑   ◉ Check all`
        - focused actual: `⋑   ◉ Check all all`
   - c) Text box
     - Direct after `Enter the git username to use:`
       1) unfocused
          - unfocused should (1/3): `  ╭───┬────────────────────────────────────────╮`
          - unfocused should (2/3): `  │ ✎ │ luckydonald                            │`
          - unfocused should (3/3): `  ╰━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯`
          - unfocused actual (1/3): `  ╭╭───┬────────────────────────────────────────╮`
          - unfocused actual (2/3): `  │ ✎ │ luckydonald                              │`
          - unfocused actual (3/3): `  ╰━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯`
       2) focused
          - focused should: _(same as **unfocused should**)_
          - focused actual (1/3): `  ╭╭───╭───┬────────────────────────────────────────╮`
          - focused actual (2/3): `  │ ✎ │ luckydoonal▁▁                            │`
          - focused actual (3/3): `  ╰━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯`
4. 2nd level _active_ state has wrong icon. Here's a full test sequence:
   1. Given a push or fetch, which has a `.git` suffix, both currently turned off
   2. Observe:
      1. State: push: off, suffix off
      2. both have the `○` icon. (correct)
   3. Toggle the _suffix_ option _on_
   4. Observe:
      1. State: push: off, suffix on
      2. `◒` push and `●` suffix (correct)
   5. Toggle the _fetch/push_ option _on_
   6. Observe:
      1. State: push: on, suffix on
      2. `●` push and `●` suffix (correct)
   7. Toggle the _suffix_ option _off_ again.
   8. Observe:
      1. State: push: on, suffix off
      2. `◒` push and `○` suffix (incorrect!)
      - Correct would be:  `●` push and `○` suffix (`init.md` spec)
      - Implement instead: `◓` push and `○` suffix (actually better)
   - Write this as test first (accepting both `◓` and `●` for step 8.), then fix it.
