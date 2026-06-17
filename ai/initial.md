/plan Alright, the plugin is nice, but it lacks a bit. Here's what I want:
1. Switch to using modern Vue.js 3+, with TS and SCSS.
2. If the custom domain in the settings is not yet allowed for that plugin, it will fail silently and not store the host & api-key.
   - Instead, it should tell you that it needs network access to that domain in order to validate, and request that from the browser.
   - It should clearly communicate if it saved or failed, and why.
3. Currently, it will only create email aliases for the default domain, and not allow you to choose others.
   1. For that the domains available should periodically be cached in the background, so when clicking the plugin's button, you don't need to wait for a fetch.
   2. If it catches previous registered emails, cache that in the background, too.
   3. when opening the tab, start a fresh fetch.
   4. Right now the GUI is barebones and not very good.
      1. Checkboxes for what would be radio buttons
      2. Error Text "There are no recipients to modify." is not clear that you need to add a mail address to the _To_ field first.
   5. The list of existing aliases to reuse is good, keep it but improve UX.
   6. Alias creation ui must have
      1. the dropdown of which domain (with search)
      2. how the alias shall be generated (`random_characters`, `random_words`, `random_male_name`, `random_female_name`, `random_noun`, `custom`)
      3. show a custom prefix field. Placeholder shall be _custom_`, and the field followed by `@` and the choosen domain above, i.e.: `[ custom ] @example.com` - in this fields split way where it's a different colored "part of the input element".
   7. Allow disabling & deletion of the alias created.
   8. `Please wait` should be a spinner. Imitate the 80s cartoon-video transition with the batman logo swirling and zooming in and out (repeatedly); using the already packed addy.io logo.
4. The `Go to addy.io` link should reflect the domain in the settings.
5. Add a link to the settings, too.
6. Add a GitHub build workflow to pack tagged commits as releases (unsigned, for manually installing).
7. Can we add a dropdown on the email in the TO/CC/BBC bar?
   - If yes, the structure would be:
   1. [addy logo] Use Addy alias for sending >
      - direct click on this item opens the GUI popup, hovering causes it to unfold.
      - all further menu entries are regular navigation.
      1. [reuse symbol] Existing >
         - list of existing custom domains previously used for that.
         1. existing-alias@example.org (**done**)
         - if more than 5, see if there's more than one mail domain, and split by that
         2. …@mail.example.com >
            1. foobar@example.com (**done**)
      2. [server symbol] New >
         1. [addy-domain favicon or server symbol] addy.io >
            - the configured anonaddy/addy.io host
            - or e.g. `anon.example.com`
            - if more than one anonaddy server is configured (otherwise skip):
            1. [mail-domain favicon or mail symbol] …@mail.example.com >
               - email domains available (similar to the dropdown)
               - e.g. `@mail.example.com` or `@example.org` or `@mail.org`
               - how to generate the alias:
               1. [fitting icon] Characters (**done**)
               2. [fitting icon] Words (**done**)
               3. [fitting icon] Male name (**done**)
               4. [fitting icon] Female name (**done**)
               5. [fitting icon] Noun (**done**)
               6. [fitting icon] Custom…
                  1. _Custom_ opens a `prompt()` or similar in native Thunderbird UI.
                  2. user hits OK (**done**)
   - The _(**done**)_ above is not displayed, it's for the control flow and means that it's now going to:
     1. create the alias (similar to the current behavior)
     2. replace the selected mail address we had the dropdown on with its new alias.
