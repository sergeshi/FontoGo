# FontoGo

FontoGo is an HTML-first font workspace with a Python launcher and an emerging UI-independent Python core. This is an early-stage project; see limitations below before using it for production fonts.

## Run the desktop app (recommended)

Requirements: Python 3.10+ and dependencies from `requirements.txt`.

```bash
python -m pip install -r requirements.txt
python desktop.py
```

The Qt desktop shell provides a native window, right-click context menu and native clipboard access. While a glyph editor is open, use the context menu item **Вставить вектор из буфера** or press Ctrl/Cmd+V. SVG paths and common SVG primitives are imported as editable objects. Complex transforms, styles, filters and clipping may not be preserved exactly; raster images are not converted into outlines.

## Run the browser prototype (optional)

```bash
python launcher.py
```

The launcher serves the app on `http://127.0.0.1:8765`, opens a browser, and checks the `main` branch on GitHub. It only applies fast-forward updates when the working tree is clean. Disable update checks with `FONTOGO_DISABLE_UPDATES=1`. Change the port with `FONTOGO_PORT=8766`.

## Python font core (new)

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Import a TTF/OTF into a JSON document, then export the project as a TrueType-flavoured TTF:

```bash
python -m fontogo_core.cli SomeFont.otf working-copy.json
python -m fontogo_core.cli working-copy.json MyFont.ttf
```

The input font is never overwritten by these commands. Use an output path different from the source. Keep backups of important source files.

The `fontogo_core` package includes:
- A UI-independent document, glyph, contour, segment, component, master, cmap and kerning model.
- Explicit line and cubic Bézier segments, component affine transforms and contour translation/scale/rotation helpers.
- Snapshot-based undo/redo history for UI commands.
- TTF/OTF import through fontTools; legacy `kern` pairs are read where present.
- TTF compilation with glyph outlines, components, horizontal metrics, Unicode cmap and a legacy `kern` table.
- Optional boolean path operations through `skia-pathops`.

Run model tests with `python -m unittest discover -s tests`.

## Current UI prototype

- New-document dialog with UPM, family/style metadata, cap height, x-height and script selection.
- Unicode glyph grid, script tabs, search and filters. Grey previews use system font fallback stacks; they are visual references only.
- Double-click a glyph to open a basic SVG primitive editor (line, rectangle, ellipse, arc and rounded rectangle).
- Add script sets: Latin, Cyrillic, Hebrew, Greek, Arabic and a small CJK demo set.
- Starter kerning suggestions and a filterable/editable list of generated pairs.
- Family master and axis metadata UI; local browser saves and project JSON import/export.

## Important limitations

The Python model is the start of the core, not yet integrated into the browser editor. The browser still stores primitive shapes rather than the new contour model. Imported quadratic outlines are converted to cubic curves for editing. The exporter currently compiles TrueType `glyf` outlines to TTF; although OTF/CFF outlines can be imported for inspection/editing, CFF-flavoured OTF export is not implemented. GPOS kerning classes, mark positioning, complex-script shaping, a professional automatic kerning analyser, variable-font compilation, full node-editing UI, plugin sandbox/permissions, and full CJK coverage remain unimplemented. Boolean operations require the optional `skia-pathops` dependency. Do not use this prototype as the only copy of important work.

## Architecture direction

The HTML interface should remain replaceable. Keep business logic in the versioned Python model and services so a future Qt client can reuse them. The next integration milestone is to connect the SVG Bézier/node editor to `fontogo_core.model`, then add regression tests around import/export fidelity before implementing advanced kerning, interpolation and plugins.
