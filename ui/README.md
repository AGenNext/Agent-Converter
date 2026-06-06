# Research Agent chat UI components

Framework-free UI components for the Research Deep Agent's chat interface,
explorable in [Storybook](https://storybook.js.org/). The same components back
the served control panel (`/static/index.html`).

## Components

- `ConfidenceChip(level)` — HIGH / MEDIUM / LOW / UNVERIFIED tag.
- `MessageBubble({role, text})` — user or agent chat bubble.
- `FindingItem({text, source, confidence})` — a key finding row.
- `SourceItem({tier, label})` — a source with its credibility tier.
- `StatusBar({text, spinning})` — live progress / readiness indicator.

They are plain functions returning DOM nodes, so they drop into any page with
no build step. `src/theme.css` holds the shared design tokens and styles.

## Run Storybook

```bash
cd ui
npm install
npm run storybook      # opens http://localhost:6006
```

Build a static Storybook for hosting:

```bash
npm run build-storybook
```

## Relationship to the served panel

The control panel in `../static/index.html` is the production chat UI (it talks
to the agent's streaming endpoints). This package is the component catalog:
build and document components here, then reuse them in the panel. Keeping the
visual language in one `theme.css` keeps the two in sync.
