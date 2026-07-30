# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

`exercises.axolingua.com` — a free, filterable library of standalone HTML language-learning exercises, built as a bilingual (ES/EN) Jekyll site using `jekyll-polyglot`. It shares brand infrastructure (design tokens, font stack, build setup) with `axolingua.com`.

## Commands

```bash
bundle install              # install gems (first run / after Gemfile changes)
bundle exec jekyll serve    # local dev server with live reload, http://localhost:4000
bundle exec jekyll build    # production build -> _site/ (what Netlify runs)
```

There is no test suite, linter, or JS build step in this repo — content and templates only.

Netlify runs `bundle exec jekyll build` from `main` with `JEKYLL_ENV=production`, publishing `_site/` (see `netlify.toml`). Ruby version pinned to 3.3.4 there.

## Architecture

### i18n via jekyll-polyglot
- `languages: ["es", "en"]`, `default_lang: "es"` — Spanish lives at root URLs (`/ejercicios/`), English is generated under `/en/...` automatically by the plugin.
- `assets`, `exercises`, and top-level static files (`robots.txt`, `sitemap.xml`, `404.html`) are in `exclude_from_localization` — they are not duplicated per-language.
- Layouts/includes compute `lang_prefix` once (`''` for `es`, `'/en'` otherwise) and reuse it for every internal link — follow this pattern instead of hardcoding `/en/`.
- The ES/EN toggle in `_includes/nav.html` uses polyglot's `{% static_href %}` tag so the link targets the *equivalent* page in the other language rather than being auto-rewritten.

### Copy lives only in `_data/` — never in layouts, includes, or page templates
- `_data/strings.yml` — global UI strings (nav, footer, a11y), keyed by language then string path (`t.nav.exercises`).
- `_data/pages/<page_id>.yml` — per-page copy (hero text, meta title/description, filter labels), keyed by language. A page's front matter sets `page_id: <name>`, and `_includes/head.html` looks up `site.data.pages[page.page_id][site.active_lang]` for meta title/description.
- This separation is intentional and enforced by convention/comments throughout the codebase — when adding UI text, add a data key, don't inline strings in HTML/Liquid.

### Exercise catalog: data-driven, not template-driven
- `_data/exercise_catalog.yml` is the single source of truth — one entry per exercise, referencing a static file in `/exercises/` by `file`. Fields: `slug`, `file`, `skill`, `grammar`, `target_lang`, `level`, `theme`, bilingual `title`/`description`.
- `_data/exercise_taxonomy.yml` supplies human-readable bilingual labels for `skill`/`grammar`/`level`/`theme` values used in the catalog, and drives the filter pills on `/ejercicios/`. **Adding a new exercise requires a catalog entry (and a taxonomy entry if it introduces a new skill/grammar/level/theme value) — never a template change.**
- `ejercicios.html` (permalink `/ejercicios/`) renders the filterable grid entirely from these two data files, embeds each exercise via `<iframe src="/exercises/{{ ex.file }}">`, and implements client-side filtering with vanilla JS matching on `data-skill`/`data-level`/`data-theme` attributes — no build step or framework involved.

### `/exercises/*.html` are standalone, self-contained pages
- Each file under `exercises/` is a complete, independently-stylable HTML document (own `<style>` block, own fonts, sometimes an accompanying `_files/` folder for exported assets/CSS) — they are embedded via iframe and also linked to directly, so they must work with zero dependency on the parent site's layout or CSS.
- They redeclare the Axolingua brand CSS custom properties (colors, fonts) inline at the top of each file rather than importing `_sass/_tokens.scss`, since these files must remain fully portable — keep new/edited exercise files consistent with the token values in `_sass/_tokens.scss` when changing brand colors.
- Filename convention: `skill_grammar_lang_level[_theme].html` (e.g. `drill_tiempos_simples_es_a2_deportes.html`), matching the `file` field in the catalog.
- Netlify long-caches `/exercises/*` as static/immutable — treat existing exercise files as versioned; prefer adding a new file over mutating one in place if behavior changes meaningfully.

### Styling
- `assets/css/main.scss` is the sole Sass entry point, `@use`-ing `_sass/_tokens.scss` (shared, portable design tokens — colors, spacing, radius, motion; kept free of site-specific selectors since it's reused across other Axolingua properties), `_base`, `_components`, and `_exercises` partials, in that order. Sass compiles with `style: compressed`.
- Brand palette: warm ivory/cream backgrounds (never pure white/black), pink = primary/Spanish, jade = secondary/English, ochre = accent/grounding — see the header comments in `_sass/_tokens.scss` for the full rationale.

### Layout structure
- `_layouts/default.html` is the only layout; it includes `head.html` (meta/OG/hreflang/fonts/analytics), `nav.html` (brand, exercises link, ES/EN toggle, mobile menu toggle), and `footer.html`.
- Page meta title/description come from `_data/pages/<page_id>[.lang].meta`, falling back to `_data/pages/home[.lang].meta.description`.
- Plausible analytics is opt-in via `plausible_domain` in `_config.yml` (empty string disables it).
