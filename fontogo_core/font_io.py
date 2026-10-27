"""TrueType/OpenType font import and TrueType-flavoured export using fontTools.

Import preserves line and cubic contours and component references. Quadratic outlines
are converted to equivalent cubic segments for editing. Export currently writes
glyf-based TrueType outlines; CFF/CFF2 outlines can be imported for editing but are
not yet recompiled back to CFF-flavoured OTF.
"""
from __future__ import annotations
from pathlib import Path
from .model import Document, Glyph, Contour, Segment, Component

def _fonttools():
    try:
        from fontTools.ttLib import TTFont
        from fontTools.pens.recordingPen import RecordingPen
        from fontTools.pens.ttGlyphPen import TTGlyphPen
        from fontTools.pens.transformPen import TransformPen
        return TTFont, RecordingPen, TTGlyphPen, TransformPen
    except ImportError as exc:
        raise RuntimeError("Font I/O requires fontTools. Install with: pip install fonttools") from exc

def import_font(path: str | Path) -> Document:
    TTFont, RecordingPen, _, _ = _fonttools()
    font = TTFont(str(path), recalcBBoxes=False, recalcTimestamp=False)
    try:
        upm = int(font["head"].unitsPerEm)
        names = font["name"]
        def name_id(i, default):
            try: return names.getDebugName(i) or default
            except Exception: return default
        family, style = name_id(1,"Untitled"), name_id(2,"Regular")
        glyph_order = font.getGlyphOrder()
        cmap = {}
        for table in font["cmap"].tables:
            if table.isUnicode():
                for cp, name in table.cmap.items(): cmap.setdefault(cp,name)
        glyf = font["glyf"] if "glyf" in font else None
        glyph_set = font.getGlyphSet()
        doc = Document(family, style, upm)
        doc.cmap = {int(cp): name for cp,name in cmap.items() if name in glyph_order}
        for name in glyph_order:
            g = Glyph(name)
            if glyf is not None:
                source = glyf[name]
                g.advance_width = int(font["hmtx"].metrics.get(name,(upm,0))[0])
                g.left_side_bearing = int(font["hmtx"].metrics.get(name,(upm,0))[1])
                if source.isComposite():
                    for comp in source.components:
                        transform = (1,0,0,1,0,0)
                        if hasattr(comp, "getComponentInfo"):
                            base, tr = comp.getComponentInfo(); transform = tuple(float(v) for v in tr)
                        g.components.append(Component(comp.glyphName, transform))
            else:
                g.advance_width = int(font["hmtx"].metrics.get(name,(upm,0))[0])
                g.left_side_bearing = int(font["hmtx"].metrics.get(name,(upm,0))[1])
            pen = RecordingPen()
            glyph_set[name].draw(pen)
            current = None
            contours = []
            for op, pts in pen.value:
                if op == "moveTo":
                    if current: contours.append(current)
                    current = Contour(tuple(map(float,pts[0])), [], False)
                elif op == "lineTo" and current:
                    current.segments.append(Segment("line",tuple(map(float,pts[0]))))
                elif op == "curveTo" and current:
                    p1,p2,p3=pts
                    current.segments.append(Segment("cubic",tuple(map(float,p3)),tuple(map(float,p1)),tuple(map(float,p2))))
                elif op == "qCurveTo" and current:
                    # Convert each quadratic to cubic. For multi-point qCurveTo, implied
                    # on-curve points are midpoints between consecutive off-curve points.
                    qpts=list(pts)
                    if qpts and qpts[-1] is None:
                        qpts=qpts[:-1]
                        if qpts:
                            first=qpts[0]; last=qpts[-1]
                            start=current.start
                            end=((last[0]+first[0])/2,(last[1]+first[1])/2)
                            qpts.append(end)
                    start=current.segments[-1].end if current.segments else current.start
                    for i in range(0,len(qpts)-1,2):
                        control=qpts[i]; end=qpts[i+1]
                        if i+2 < len(qpts): end=((qpts[i+1][0]+qpts[i+2][0])/2,(qpts[i+1][1]+qpts[i+2][1])/2)
                        c1=(start[0]+2*(control[0]-start[0])/3,start[1]+2*(control[1]-start[1])/3)
                        c2=(end[0]+2*(control[0]-end[0])/3,end[1]+2*(control[1]-end[1])/3)
                        current.segments.append(Segment("cubic",tuple(map(float,end)),tuple(map(float,c1)),tuple(map(float,c2))))
                        start=end
                elif op in ("closePath","endPath") and current:
                    current.closed = op == "closePath"; contours.append(current); current=None
            if current: contours.append(current)
            g.contours=contours
            g.unicodes=[cp for cp,n in doc.cmap.items() if n==name]
            g.codepoints=list(g.unicodes)
            doc.glyphs[name]=g
        # Preserve legacy kern pairs where present; GPOS class kerning is not flattened here.
        if "kern" in font:
            for subtable in font["kern"].kernTables:
                for pair,value in getattr(subtable,"kernTable",{}).items():
                    if pair[0] in doc.glyphs and pair[1] in doc.glyphs: doc.kerning[pair]=int(value)
        doc.validate()
        return doc
    finally:
        font.close()

def export_ttf(document: Document, path: str | Path) -> None:
    """Compile a validated model into a minimal installable TrueType font."""
    TTFont, _, TTGlyphPen, _ = _fonttools()
    from fontTools.fontBuilder import FontBuilder
    document.validate()
    order = [".notdef"] + [n for n in document.glyphs if n != ".notdef"]
    if len(order) != len(set(order)): raise ValueError("Duplicate glyph names")
    fb = FontBuilder(document.units_per_em, isTTF=True)
    fb.setupGlyphOrder(order)
    cmap = {int(cp):name for cp,name in document.cmap.items() if name in order}
    fb.setupCharacterMap(cmap)
    glyphs = {}
    for name in order:
        g = document.glyphs.get(name, Glyph(name, advance_width=document.units_per_em//2))
        pen = TTGlyphPen(None)
        # Components are retained as components when possible. A component-only glyph
        # can be exported directly; mixing components and explicit contours is supported
        # by TTGlyphPen as well.
        for comp in g.components:
            pen.addComponent(comp.base_glyph, tuple(comp.transform))
        for contour in g.contours:
            if not contour.closed: continue
            pen.moveTo(tuple(round(v) for v in contour.start))
            for seg in contour.segments:
                if seg.kind == "line": pen.lineTo(tuple(round(v) for v in seg.end))
                else: pen.curveTo(tuple(round(v) for v in seg.control1),tuple(round(v) for v in seg.control2),tuple(round(v) for v in seg.end))
            pen.closePath()
        glyphs[name]=pen.glyph()
    fb.setupGlyf(glyphs)
    fb.setupHorizontalMetrics({n:(max(0,int(document.glyphs[n].advance_width)),int(document.glyphs[n].left_side_bearing)) if n in document.glyphs else (document.units_per_em//2,0) for n in order})
    fb.setupHorizontalHeader(ascent=int(document.units_per_em*.8), descent=-int(document.units_per_em*.2))
    fb.setupNameTable({"familyName":document.family_name,"styleName":document.style_name,"uniqueFontIdentifier":document.family_name+"-"+document.style_name,"fullName":document.family_name+" "+document.style_name,"psName":(document.family_name+"-"+document.style_name).replace(" ","")})
    fb.setupOS2(sTypoAscender=int(document.units_per_em*.8),sTypoDescender=-int(document.units_per_em*.2),usWinAscent=int(document.units_per_em*.9),usWinDescent=int(document.units_per_em*.2))
    fb.setupPost()
    fb.setupMaxp()
    font=fb.font
    if document.kerning:
        from fontTools.ttLib import newTable
        kern=newTable("kern"); kern.version=0
        sub=newTable("kern").kernTables
        from fontTools.ttLib.tables._k_e_r_n import KernTable_format_0
        table=KernTable_format_0(); table.version=0; table.coverage=1
        table.kernTable={(l,r):int(v) for (l,r),v in document.kerning.items() if l in order and r in order}
        kern.kernTables=[table]; font["kern"]=kern
    font.save(str(path))
