# Vendor Dependencies

This extension uses a Vite build process. The following runtime libraries are bundled
into the extension output by Vite. Build-only tools (vite, vue-tsc, sass, typescript,
prettier) are not shipped and are not listed here.

| Library | Version | Source URL                                 |
| ------- | ------- | ------------------------------------------ |
| Vue     | 3.5.38  | https://github.com/vuejs/core/tree/v3.5.38 |

No library files are committed to the repository directly; all dependencies are
downloaded by `npm ci` during the build process (see `DEVELOPER.md`).
