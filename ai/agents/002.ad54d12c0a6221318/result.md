**Task:** Survey testing landscape for this Thunderbird MV3 extension.

---

**Current state:** No tests exist. No test framework is installed. CI only runs Prettier. No test files anywhere.

**What's testable and how:**

1. **Unit tests (easiest, highest ROI)** — The API layer (`src/api/index.ts`, `src/api/types.ts`) and any pure logic in composables (`src/composables/`) are framework-independent and can be tested with **Vitest** (natural fit since the project already uses Vite). The `messenger` global would need to be mocked.

2. **Vue component tests** — `@vue/test-utils` + Vitest can render `RecipientCard`, `CreateAliasForm`, etc. in jsdom. Works well for UI logic; won't catch Thunderbird-specific rendering issues.

3. **End-to-end / integration (hard)** — Testing against an actual Thunderbird instance requires `web-ext` + a real Thunderbird binary. Mozilla's `web-ext` CLI can run the extension in Thunderbird; you'd drive it via `puppeteer` or similar, but Thunderbird's WebDriver support is limited. This is significantly more complex to set up and maintain.

**Realistic recommendation:**

- Add **Vitest** for unit + component tests — low friction, no new build system, covers the API client, alias-matching logic, and component behavior.
- Skip E2E automation unless there's a specific regression pain point — the Thunderbird testing story is still rough.
