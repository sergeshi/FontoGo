"""Outline transforms and optional boolean operations."""
from __future__ import annotations
from copy import deepcopy
from .model import Contour, Segment, transform_contour

def translate(contours, dx: float, dy: float):
    return [transform_contour(c, (1,0,0,1,dx,dy)) for c in contours]

def scale(contours, sx: float, sy: float | None = None, origin=(0,0)):
    sy = sx if sy is None else sy; ox,oy=origin
    return [transform_contour(c,(sx,0,0,sy,ox-sx*ox,oy-sy*oy)) for c in contours]

def rotate(contours, degrees: float, origin=(0,0)):
    import math
    a=math.radians(degrees); c=math.cos(a); s=math.sin(a); ox,oy=origin
    return [transform_contour(x,(c,-s,s,c,ox-c*ox+s*oy,oy-s*ox-c*oy)) for x in contours]

def boolean_operation(contours_a, contours_b, operation: str):
    """Perform path boolean via optional skia-pathops. Inputs are fontogo Contours.

    Boolean support is optional and fails explicitly if the dependency is absent; it
    never silently approximates an operation.
    """
    try:
        import pathops
    except ImportError as exc:
        raise RuntimeError("Boolean operations require skia-pathops: pip install skia-pathops") from exc
    def make_path(contours):
        p=pathops.Path()
        for c in contours:
            p.moveTo(*c.start)
            for s in c.segments:
                if s.kind=="line": p.lineTo(*s.end)
                else: p.cubicTo(*s.control1,*s.control2,*s.end)
            if c.closed: p.close()
        return p
    ops={"union":pathops.PathOp.UNION,"difference":pathops.PathOp.DIFFERENCE,"intersection":pathops.PathOp.INTERSECTION,"xor":pathops.PathOp.XOR}
    if operation not in ops: raise ValueError("operation must be union, difference, intersection, or xor")
    result=pathops.op(make_path(contours_a),make_path(contours_b),ops[operation])
    out=[]
    current=None
    for verb, pts in result:
        if verb==pathops.PathVerb.MOVE: current=Contour(tuple(pts[0]),[],True); out.append(current)
        elif verb==pathops.PathVerb.LINE and current: current.segments.append(Segment("line",tuple(pts[0])))
        elif verb==pathops.PathVerb.CUBIC and current: current.segments.append(Segment("cubic",tuple(pts[2]),tuple(pts[0]),tuple(pts[1])))
        elif verb==pathops.PathVerb.CLOSE and current: current.closed=True
    return out
