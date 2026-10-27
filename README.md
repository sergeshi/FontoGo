# FontoGo

FontoGo is an early, HTML-first font-design workspace with a Python launcher. This repository currently contains a UI prototype, not a production font compiler.

## Run locally

Requirements: Python 3.10+ and Git (Git is optional for serving, but needed for self-update).

```bash
python launcher.py
```

The launcher serves the app on `http://127.0.0.1:8765`, opens a browser, and checks the `main` branch on GitHub. It only applies fast-forward updates when the working tree is clean. Disable update checks with `FONTOGO_DISABLE_UPDATES=1`. Change the port with `FONTOGO_PORT=8766`.

## Current prototype

- New-document dialog with UPM, family/style metadata, cap height, x-height and script selection.
- Unicode glyph grid, script tabs, search and filters. Grey previews use system font fallback stacks; they are visual references only.
- Double-click a glyph to open a basic SVG primitive editor (line, rectangle, ellipse, arc and rounded rectangle), with undo, clear, advance width and left sidebearing.
- Add script sets: Latin, Cyrillic, Hebrew, Greek, Arabic and a small CJK demo set.
- Starter kerning suggestions and a filterable/editable list of generated pairs.
- Family master and axis metadata UI.
- Save to browser local storage, import/export project JSON.
- Keyboard shortcut Ctrl/Cmd+S.

## Known limitations

This is not yet a production font editor. SVG primitives are not yet normalized into a font outline model. The current automatic kerning is a simple heuristic, not a typographic analysis engine. Variable-font controls are project metadata only. Font import/export, full node editing, robust shaping, full CJK coverage, plugin sandbox/permissions, automatic glyph construction and Qt UI are not implemented yet. Do not use the prototype as the only copy of important work; export JSON backups.

## Architecture direction

Keep the browser UI as a replaceable frontend and use a versioned, UI-independent document model. The planned Python core should isolate:
- document/glyph/master models and migration;
- font I/O and compilation (fontTools/fontmake, with optional FontForge bridge);
- shaping and script-aware validation;
- outline geometry and component references;
- kerning classes, exceptions, analysis and export;
- plugin manifest, API versioning, permissions and compatibility checks.

A future Qt client can reuse the same Python services and document schema. The project JSON format is versioned with `schemaVersion`.
