# Memory Index

- [Thunderbird Marionette Chrome API patterns](marionette_tb_chrome_patterns.md) — empirically discovered TB/Marionette patterns: chrome context, window handles, compose window, extension popup OOP frame, storage injection
- [Thunderbird Marionette system access setup](marionette_system_access.md) — how to enable chrome system access: flag + env var, Flatpak-specific sandwich
- [User safety preference: destructive commands](user_safety_destructive.md) — only kill known PIDs; never use broad pkill on TB without explicit auth
- [XUL popuphidden bubbling fix](xul_popuphidden_bubbling.md) — { once: true } cleanup fires for child popup events; use e.target guard instead
- [Experiment alias matching](experiment_alias_matching.md) — must match by description (not email), same as popup, or Existing submenu shows nothing
- [Experiment IIFE build pattern](experiment_iife_build.md) — second Vite config compiles experiment to IIFE; globalThis=sandbox for class registration; export default is stripped by esbuild before Rollup sees it
- [Vite entry splitting breaks popup](vite_entry_splitting_popup.md) — preserveEntrySignatures + extra Vite entry extracts shared code as external module, white-screens popup; keep popup self-contained
- [.d.ts alongside .js for TypeScript imports](dts_alongside_js_typing.md) — add matching .d.ts to type a JS module without allowJs; bundler uses .js for content, .d.ts for types
- [Unit and Marionette fix session](unittest_marionette_fix_session.md) — clean extension builds, active mail-window compose opening, storage/permission seeding, mock GET recording, NetUtil method ordering, CSP-safe popup frame scripts
