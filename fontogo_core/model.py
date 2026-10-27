"""UI-independent, serializable glyph model and command history.

Coordinates use font units with the usual font convention: positive y points up.
Contours contain explicit line/cubic segments; components reference another glyph.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from copy import deepcopy
from typing import Any
import json
import math

@dataclass
class Segment:
    kind: str  # "line" or "cubic"
    end: tuple[float, float]
    control1: tuple[float, float] | None = None
    control2: tuple[float, float] | None = None
    def validate(self) -> None:
        if self.kind not in {"line", "cubic"}:
            raise ValueError(f"Unsupported segment kind: {self.kind}")
        if self.kind == "cubic" and (self.control1 is None or self.control2 is None):
            raise ValueError("Cubic segments require two control points")

@dataclass
class Contour:
    start: tuple[float, float]
    segments: list[Segment] = field(default_factory=list)
    closed: bool = True
    def validate(self) -> None:
        if len(self.start) != 2:
            raise ValueError("Contour start must be an (x, y) pair")
        for seg in self.segments: seg.validate()

@dataclass
class Component:
    base_glyph: str
    # x' = xx*x + xy*y + dx; y' = yx*x + yy*y + dy
    transform: tuple[float, float, float, float, float, float] = (1, 0, 0, 1, 0, 0)

@dataclass
class Glyph:
    name: str
    codepoints: list[int] = field(default_factory=list)
    advance_width: int = 600
    left_side_bearing: int = 0
    contours: list[Contour] = field(default_factory=list)
    components: list[Component] = field(default_factory=list)
    unicodes: list[int] = field(default_factory=list)
    def validate(self) -> None:
        if self.advance_width < 0: raise ValueError("Advance width cannot be negative")
        for c in self.contours: c.validate()
        for cp in self.codepoints + self.unicodes:
            if cp < 0 or cp > 0x10FFFF: raise ValueError(f"Invalid Unicode codepoint: {cp}")

@dataclass
class Master:
    name: str = "Regular"
    location: dict[str, float] = field(default_factory=dict)
    glyphs: dict[str, Glyph] = field(default_factory=dict)

@dataclass
class Document:
    family_name: str = "Untitled"
    style_name: str = "Regular"
    units_per_em: int = 1000
    glyphs: dict[str, Glyph] = field(default_factory=dict)
    cmap: dict[int, str] = field(default_factory=dict)
    masters: list[Master] = field(default_factory=lambda: [Master()])
    kerning: dict[tuple[str, str], int] = field(default_factory=dict)
    axes: list[dict[str, Any]] = field(default_factory=list)
    schema_version: int = 2
    def validate(self) -> None:
        if not 16 <= self.units_per_em <= 16384: raise ValueError("UPM must be between 16 and 16384")
        for name, glyph in self.glyphs.items():
            if name != glyph.name: raise ValueError(f"Glyph key/name mismatch: {name!r}")
            glyph.validate()
        for cp, name in self.cmap.items():
            if not 0 <= int(cp) <= 0x10FFFF: raise ValueError(f"Invalid cmap codepoint: {cp}")
            if name not in self.glyphs: raise ValueError(f"cmap references missing glyph: {name}")
        for (left, right), value in self.kerning.items():
            if left not in self.glyphs or right not in self.glyphs: raise ValueError("Kerning pair references missing glyph")
            if not isinstance(value, int): raise ValueError("Kerning values must be integers")
    def to_dict(self) -> dict[str, Any]:
        def conv(v):
            if isinstance(v, tuple): return list(v)
            if isinstance(v, dict): return {(" ".join(k) if isinstance(k, tuple) else str(k)): conv(x) for k,x in v.items()}
            if isinstance(v, list): return [conv(x) for x in v]
            if hasattr(v, "__dataclass_fields__"): return {k: conv(x) for k,x in asdict(v).items()}
            return v
        return conv(self)
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Document":
        def segment(x): return Segment(x["kind"], tuple(x["end"]), tuple(x["control1"]) if x.get("control1") else None, tuple(x["control2"]) if x.get("control2") else None)
        def contour(x): return Contour(tuple(x["start"]), [segment(s) for s in x.get("segments", [])], x.get("closed", True))
        glyphs = {}
        for key, x in raw.get("glyphs", {}).items():
            glyphs[key] = Glyph(x.get("name", key), x.get("codepoints", []), x.get("advance_width", 600), x.get("left_side_bearing", 0), [contour(c) for c in x.get("contours", [])], [Component(c["base_glyph"], tuple(c.get("transform", (1,0,0,1,0,0)))) for c in x.get("components", [])], x.get("unicodes", []))
        masters = [Master(m.get("name","Regular"), m.get("location",{}), {k: glyphs.get(k, Glyph(k)) for k in m.get("glyphs", {})}) for m in raw.get("masters", [])] or [Master()]
        doc = cls(raw.get("family_name","Untitled"), raw.get("style_name","Regular"), int(raw.get("units_per_em",1000)), glyphs, {int(k):v for k,v in raw.get("cmap",{}).items()}, masters, {}, raw.get("axes",[]), int(raw.get("schema_version",2)))
        for key, val in raw.get("kerning", {}).items():
            pair = tuple(key.split(" ",1)) if isinstance(key,str) else tuple(key)
            if len(pair)==2: doc.kerning[pair]=int(val)
        doc.validate()
        return doc

class UndoHistory:
    """Snapshot-based undo/redo; push before each user-visible mutation."""
    def __init__(self, initial: Any, limit: int = 200):
        self.limit = max(1, limit); self._past = []; self._future = []; self._current = deepcopy(initial)
    @property
    def current(self): return deepcopy(self._current)
    def commit(self, value: Any) -> None:
        self._past.append(self._current)
        if len(self._past) > self.limit: self._past.pop(0)
        self._current = deepcopy(value); self._future.clear()
    def undo(self):
        if not self._past: return None
        self._future.append(self._current); self._current = self._past.pop(); return deepcopy(self._current)
    def redo(self):
        if not self._future: return None
        self._past.append(self._current); self._current = self._future.pop(); return deepcopy(self._current)

def transform_point(point, matrix):
    xx, xy, yx, yy, dx, dy = matrix
    x, y = point
    return (xx*x + xy*y + dx, yx*x + yy*y + dy)

def transform_contour(contour: Contour, matrix) -> Contour:
    return Contour(transform_point(contour.start, matrix), [
        Segment(s.kind, transform_point(s.end, matrix),
                transform_point(s.control1, matrix) if s.control1 else None,
                transform_point(s.control2, matrix) if s.control2 else None)
        for s in contour.segments], contour.closed)

def transformed_glyph(glyph: Glyph, matrix) -> Glyph:
    result = deepcopy(glyph); result.contours = [transform_contour(c, matrix) for c in glyph.contours]
    # Components retain a composable transform rather than being destructively decomposed.
    a,b,c,d,e,f = matrix
    result.components = [Component(x.base_glyph, (
        a*x.transform[0]+b*x.transform[2], a*x.transform[1]+b*x.transform[3],
        c*x.transform[0]+d*x.transform[2], c*x.transform[1]+d*x.transform[3],
        a*x.transform[4]+b*x.transform[5]+e, c*x.transform[4]+d*x.transform[5]+f
    )) for x in glyph.components]
    return result
