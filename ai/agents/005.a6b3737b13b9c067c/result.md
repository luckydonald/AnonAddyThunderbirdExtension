Excellent. Now I have a complete picture. Let me create a comprehensive summary of all the findings:

## Summary

I've conducted a very thorough search of the AnonAddy Thunderbird extension codebase. Here are all the files related to pills, experiments, tests, icons, and CSS:

### 1. Experiment API Files (src/experiment/)

**Main Implementation:**
- `/home/user/git/luckydonald/AnonAddyThunderbirdExtension/src/experiment/implementation.ts` — The core privileged experiment code that injects the AddressChipMenu context menu into compose windows, handles pill decoration, and manages window attachment lifecycle.

**Supporting Modules:**
- `/home/user/git/luckydonald/AnonAddyThunderbirdExtension/src/experiment/schema.json` — WebExtension Experiment API schema declaring the AddressChipMenu namespace with `setCache()` function and `onChipMenuClicked` event.
- `/home/user/git/luckydonald/AnonAddyThunderbirdExtension/src/experiment/pillDecoration.js` — Pure JS module (not bundled) with five functions for decorating mail-address-pills:
  - `decoratePillViaAttributes()` — Updates the pill's label attribute
  - `decoratePillViaTextNode()` — Mutates the shadow DOM text element
  - `decoratePillViaCSSAdopted()` — Injects adopted CSS stylesheets into shadow root
  - `upsertPillIcon()` — Inserts/updates a 12×12px icon before the pill with class `addy-pill-icon`, either `addy-proxied` (colored) or `addy-aliased` (grayscale + opacity 0.6)
  - `removePillIcon()` — Removes the icon from DOM

- `/home/user/git/luckydonald/AnonAddyThunderbirdExtension/src/experiment/pillDecoration.d.ts` — TypeScript declarations for the JS module.
- `/home/user/git/luckydonald/AnonAddyThunderbirdExtension/src/experiment/menuIcons.ts` — Creates menu icon URLs from base URI; defines `MenuIconUrls` interface and `createMenuIconUrls()` function.
- `/home/user/git/luckydonald/AnonAddyThunderbirdExtension/src/experiment/xulIcon.ts` — Applies XUL icon attributes; sets `image` attribute and adds `menu-iconic` or `menuitem-iconic` class.
- `/home/user/git/luckydonald/AnonAddyThunderbirdExtension/src/experiment/windowAttachmentLifecycle.ts` — Manages window listener lifecycle with `createWindowAttachmentLifecycle()` factory returning `ensureAttached()`, `releaseEventListener()`, and `shutdown()`.
- `/home/user/git/luckydonald/AnonAddyThunderbirdExtension/src/experiment/aliasMatching.ts` — Two functions for context menu alias lookup:
  - `domainForContextMenuAliasLookup()` — Extracts the recipient domain (handles forwarding addresses)
  - `aliasesForContextMenuEmail()` — Returns matching aliases for an email
- `/home/user/git/luckydonald/AnonAddyThunderbirdExtension/src/experiment/utils.js` — Wrapper `matchingAliasesForEmail()` that extracts domain and caps results at 20.

**Icon Files (src/experiment/icons/):**
- All SVG icons use `fill="#4a90d9"` (blue) as the primary color and `fill="#2f6fa8"` (darker blue) for accents/secondary elements:
  - `existing.svg` — Arrow icon
  - `new.svg` — Plus/cross icon
  - `alias.svg` — Envelope icon
  - `domain.svg` — Domain/envelope icon
  - `picker.svg` — Picker/menu lines with circle
  - `server.svg` — Server/rack icon
  - `format-characters.svg` — Monospace "Az" text
  - `format-words.svg` — Three horizontal lines (words)
  - `format-male-name.svg` — Male head silhouette
  - `format-female-name.svg` — Female head silhouette with hair
  - `format-noun.svg` — Arrow pointing to speech bubble
  - `format-custom.svg` — Pencil/edit icon

### 2. Pill Decoration CSS

**In implementation.ts (lines 250–267):**
```css
.addy-pill-icon {
  width: 12px;
  height: 12px;
  vertical-align: middle;
  margin-right: 3px;
  pointer-events: none;
}
.addy-pill-icon.addy-aliased {
  filter: grayscale(1) opacity(0.6);
}
```

Key behavior:
- Icon shows **colored** (`addy-proxied` class) when the pill contains a forwarding address (e.g., `alias+user=domain@anondomain`)
- Icon shows **grayscale + 60% opacity** (`addy-aliased` class) when the pill's domain is an Addy domain but NOT a forwarding address
- Icon is **removed** entirely when the domain is not an Addy domain

### 3. Test Files (src/tests/)

**Unit Tests:**
- `/home/user/git/luckydonald/AnonAddyThunderbirdExtension/src/tests/pill-decoration.test.js` — 266 lines testing all five pill decoration functions with shadow DOM, text node restoration, CSS adoption, icon insertion/updates, and class toggling
- `/home/user/git/luckydonald/AnonAddyThunderbirdExtension/src/tests/menu-icons.test.ts` — Tests icon URL generation
- `/home/user/git/luckydonald/AnonAddyThunderbirdExtension/src/tests/xul-icon.test.ts` — Tests XUL icon attribute and class setting
- `/home/user/git/luckydonald/AnonAddyThunderbirdExtension/src/tests/experiment-alias-matching.test.ts` — Tests alias lookup for forwarding addresses
- `/home/user/git/luckydonald/AnonAddyThunderbirdExtension/src/tests/experiment-utils.test.js` — Tests email-to-domain extraction and 20-item cap
- `/home/user/git/luckydonald/AnonAddyThunderbirdExtension/src/tests/window-attachment-lifecycle.test.ts` — Tests lifecycle state management
- `/home/user/git/luckydonald/AnonAddyThunderbirdExtension/src/tests/popup-utils.test.ts` — Tests forwarding address parsing/building

**Marionette Integration Tests:**
- `/home/user/git/luckydonald/AnonAddyThunderbirdExtension/tests/marionette/test_chip_menu.py` — Tests right-click context menu on pills in compose windows

### 4. Shared Modules (src/shared/)

- `/home/user/git/luckydonald/AnonAddyThunderbirdExtension/src/shared/forwardingAddress.ts` — `parseForwardingAddress()` and `buildForwardingAddress()` for the `local+recip=domain@anondomain` format
- `/home/user/git/luckydonald/AnonAddyThunderbirdExtension/src/shared/aliasSearch.ts` — `aliasesForDomain()` filters active aliases by description (case-insensitive)
- `/home/user/git/luckydonald/AnonAddyThunderbirdExtension/src/shared/aliasCache.ts` — Alias cache management

### 5. Test Fixtures (tests/fixtures/)

- `/home/user/git/luckydonald/AnonAddyThunderbirdExtension/tests/fixtures/aliases.json` — Sample aliases from multiple domains (anonaddy.me, anon.email, relay.example.com)
- `/home/user/git/luckydonald/AnonAddyThunderbirdExtension/tests/fixtures/domain-options.json` — Domain list
- `/home/user/git/luckydonald/AnonAddyThunderbirdExtension/tests/fixtures/compose-details.json` — Sample compose window state
- `/home/user/git/luckydonald/AnonAddyThunderbirdExtension/tests/fixtures/forwarding-cases.json` — Test cases for forwarding address parsing

### 6. Popup Component Files (src/popup/)

- `/home/user/git/luckydonald/AnonAddyThunderbirdExtension/src/popup/App.vue` — Main popup Vue app (150+ lines)
- `/home/user/git/luckydonald/AnonAddyThunderbirdExtension/src/popup/components/RecipientCard.vue` — Per-recipient card component with alias selection, search, and forwarding address preview
- `/home/user/git/luckydonald/AnonAddyThunderbirdExtension/src/popup/styles/main.scss` — Global popup styles
- `/home/user/git/luckydonald/AnonAddyThunderbirdExtension/src/popup/styles/_variables.scss` — Color palette and spacing constants

**Key Color & Typography:**
- Primary: `#1a73e8` (blue)
- Text: `#1a1a1a`
- Muted: `#666`
- Border: `#ccc`
- Danger: `#c0392b`
- Font sizes: 14px base, 12px small
- Window min-width: 540px

### 7. Key Implementation Details

**Pill Decoration Logic (implementation.ts lines 269–294):**

When a mail-address-pill is added/changed:
1. Parse the email to detect if it's a forwarding address
2. If forwarding address (parsed successfully): Display icon colored + show aliased format label
3. If plain Addy domain: Display icon grayscale + opacity 60% + no label change
4. If external domain: Remove icon entirely

**Three Decoration Approaches (all attempted):**
- **Attributes:** Mutate the pill's `label` attribute (safe, always works)
- **Text Node:** Directly mutate shadow DOM text (attempts fallback selectors)
- **CSS Adopted:** Inject stylesheet using `attr(data-addy-label)` pseudo-element (best-effort)

All three are called together to maximize compatibility across Thunderbird versions.