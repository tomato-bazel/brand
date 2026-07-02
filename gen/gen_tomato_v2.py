#!/usr/bin/env python3
"""tomato-bazel mark v2 — ANGULAR / GEOMETRIC / ABSTRACT redesign.

Where ``gen_tomato.py`` is the soft, friendly, round cartoon tomato, this is the
deliberate opposite: a sharp, designed, geometric mark that harmonizes with
Bazel's angular green brand SPIRIT (NOT a copy of Bazel's actual logo — this is
an original mark that only borrows the angular + green vibe).

Same brando convention as v1: ONE Spec drives everything, shapely is the exact
CSG (straight-edged polygons here — no smooth buffering of the body), emission is
through ``@brando//marklib`` as canonical LAYERS + a composite, so the same Spec
yields the flat SVG, the per-layer assets and (via raster_tomato_v2.py) the PNGs.

Three distinct angular DIRECTIONS, selected by ``Spec.style``:

  * ``lowpoly`` — the tomato body as triangulated facets (gem-like), each facet a
    flat polygon with a subtly different red tone for a faceted low-poly look,
    crowned by sharp angular green calyx blades.
  * ``flat``    — a bold, flat, 2-color angular tomato: an octagonal body
    silhouette + a single crisp angular green chevron calyx. Very clean.
  * ``mark``    — a minimal mark: one strong angular tomato body (hexagon-ish)
    + one sharp green leaf, tuned to still read as a tomato at favicon size.

Geometry lives in a unit-ish model space centered on the body; ``_tf`` maps it to
the square canvas. Construction is deterministic — no randomness — so the output
is reproducible.

CLI: ``gen_tomato_v2.py <out-dir>`` emits every VARIANT's layered set.
"""
import math
import os
import sys
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from shapely.affinity import rotate, translate
from shapely.geometry import Polygon
from shapely.ops import unary_union

from marklib import Canvas, geom_to_path


# A faceted body is a set of (polygon, fill) pairs; we keep them as model-space
# point lists + a tone key so the same construction drives SVG and raster.
@dataclass
class Facet:
    pts: List[Tuple[float, float]]
    tone: str  # one of "base" / "dark" / "light" (resolved against the palette)


@dataclass
class Spec:
    # ---- which angular direction ----
    style: str = "lowpoly"  # lowpoly | flat | mark

    # ---- body geometry (model units; body roughly spans x in [-1,1]) ----
    body_w: float = 1.00          # body half-width
    body_h: float = 0.92          # body half-height
    body_sides: int = 8           # silhouette facets for the flat/mark octagon/hexagon
    crown_drop: float = 0.30      # how far the crown notch (calyx seat) dips (frac body_h)
    crown_w: float = 0.34         # half-width of the crown notch (frac body_w)

    # ---- calyx (the angular green star/chevron on top) ----
    blades: int = 6               # radiating triangular blades (lowpoly)
    blade_len: float = 0.66       # blade length (model units)
    blade_w: float = 0.18         # blade half-width at base (sharp = small)
    blade_spread: float = 200.0   # total fan angle (degrees)
    calyx_y: float = 0.06         # vertical offset of the calyx anchor below body top
    hub_r: float = 0.13           # central angular hub radius (frac body_w)
    hub_sides: int = 6            # hub is a small polygon, not a circle (stay angular)

    # ---- colors ---- (designed reds; Bazel-leaning greens)
    body: str = "#E64A33"         # primary body red (facet "base")
    body_dark: str = "#C0392B"    # deeper facet tone
    body_light: str = "#F2664E"   # highlight facet tone
    calyx: str = "#43A047"        # Bazel-leaning leaf green (the deliberate nod)
    calyx_dark: str = "#388E3C"   # deeper green for alternating blades
    calyx_light: str = "#4CAF50"  # brighter green accent
    bg: str = "#15161A"           # ink rounded-square bg (fastverk family)

    # ---- toggles ----
    two_tone_calyx: bool = True   # alternate blade greens (lowpoly/mark); flat = single
    background: str = "ink"       # ink | white | none(transparent)
    bg_round: float = 0.22        # rounded-square corner radius (frac of canvas)
    canvas: int = 1024


class TomatoV2:
    """Deterministic shapely construction of the ANGULAR tomato + brando emission.

    No buffer-rounding of the body — every edge is a straight line so the mark
    stays crisp and faceted. The body is built as explicit facet polygons (for
    the low-poly multi-tone look) plus a derived solid silhouette used for the
    calyx seat math and for the rasterizer's hit-tests.
    """

    def __init__(self, s: Spec):
        self.s = s
        self.facets: List[Facet] = self._body_facets()
        self.body_geom = unary_union([Polygon(f.pts).buffer(0) for f in self.facets])
        _, miny, _, _ = self.body_geom.bounds
        # seat the calyx in the crown notch, on the center axis
        self.calyx_anchor = (0.0, miny + s.calyx_y * s.body_h)
        self.calyx_parts: List[Tuple[object, str]] = self._calyx()  # (geom, tone)
        self.calyx_geom = unary_union([g for g, _ in self.calyx_parts])

    # ---- palette resolution ----
    def _tone(self, key: str) -> str:
        s = self.s
        return {"base": s.body, "dark": s.body_dark, "light": s.body_light}[key]

    def _green(self, key: str) -> str:
        s = self.s
        return {"base": s.calyx, "dark": s.calyx_dark, "light": s.calyx_light}[key]

    # ---- silhouette helpers ----
    def _ngon(self, cx, cy, rx, ry, sides, rot_deg=0.0):
        rot = math.radians(rot_deg)
        return [
            (cx + rx * math.cos(rot + 2 * math.pi * i / sides),
             cy + ry * math.sin(rot + 2 * math.pi * i / sides))
            for i in range(sides)
        ]

    # ---- BODY: per-style faceting -------------------------------------------
    def _body_facets(self) -> List[Facet]:
        return getattr(self, f"_facets_{self.s.style}")()

    def _crown_notch(self):
        """Two top vertices flanking a V-notch where the calyx seats. Returns the
        outline (clockwise-ish) of an angular tomato shoulder with a crown dip."""
        s = self.s
        w, h = s.body_w, s.body_h
        cw = s.crown_w * w
        cd = s.crown_drop * h
        # An angular gem outline: pointed-ish bottom, wide angular shoulders, and a
        # central V notch at the top for the calyx. y-down (svg) -> top is -h.
        return [
            (0.0, -h + cd),         # 0 center of crown notch (dipped down)
            (cw, -h + 0.10 * h),    # 1 right shoulder peak
            (w, -0.34 * h),         # 2 upper-right corner
            (w * 0.86, 0.30 * h),   # 3 lower-right corner
            (w * 0.40, h),          # 4 right of base point
            (-w * 0.40, h),         # 5 left of base point
            (-w * 0.86, 0.30 * h),  # 6 lower-left corner
            (-w, -0.34 * h),        # 7 upper-left corner
            (-cw, -h + 0.10 * h),   # 8 left shoulder peak
        ]

    def _facets_lowpoly(self) -> List[Facet]:
        """Triangulate the angular outline from an interior apex into gem facets,
        assigning tones in a deterministic light->dark sweep for a low-poly look."""
        out = self._crown_notch()
        s = self.s
        # interior facet hub, slightly upper-left of center -> implies a light source
        apex = (-0.16 * s.body_w, -0.10 * s.body_h)
        n = len(out)
        # tone sweep: brightest on the upper-left facets, darkest lower-right
        # order facets by the angle of their midpoint so tone varies smoothly.
        tris = []
        for i in range(n):
            a = out[i]
            b = out[(i + 1) % n]
            mid = ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)
            ang = math.atan2(mid[1] - apex[1], mid[0] - apex[0])  # -pi..pi
            tris.append((ang, [apex, a, b]))
        # map angle -> tone: upper-left (angle near -3pi/4) brightest
        def tone_for(ang):
            # distance (wrapped) from the "light" direction (upper-left, y-down)
            light_dir = math.radians(-135)
            d = abs((ang - light_dir + math.pi) % (2 * math.pi) - math.pi)  # 0..pi
            if d < math.pi / 3:
                return "light"
            if d < 2 * math.pi / 3:
                return "base"
            return "dark"
        facets = [Facet(pts=pts, tone=tone_for(ang)) for ang, pts in tris]
        return facets

    def _facets_flat(self) -> List[Facet]:
        """A single bold octagonal body silhouette (2-color overall: 1 red)."""
        s = self.s
        # octagon, flattened a touch, with the crown notch carved by overlaying the
        # angular outline (keeps the calyx seat). One solid base-tone facet.
        oct_pts = self._ngon(0.0, 0.0, s.body_w, s.body_h, s.body_sides,
                             rot_deg=90.0 / s.body_sides + 90.0)
        body = Polygon(oct_pts).buffer(0)
        # carve a shallow V crown notch at the top so the chevron calyx seats in it
        cw = s.crown_w * s.body_w
        cd = s.crown_drop * 0.8 * s.body_h
        top = body.bounds[1]
        notch = Polygon([
            (-cw, top - 0.02 * s.body_h),
            (cw, top - 0.02 * s.body_h),
            (0.0, top + cd),
        ]).buffer(0)
        body = body.difference(notch).buffer(0)
        ext = list(body.exterior.coords)
        return [Facet(pts=ext, tone="base")]

    def _facets_mark(self) -> List[Facet]:
        """Minimal favicon mark: a hexagon-ish angular body, two-tone split down
        the center so it still has facet character at tiny sizes."""
        s = self.s
        hexd = self._ngon(0.0, 0.05 * s.body_h, s.body_w, s.body_h, 6, rot_deg=90.0)
        body = Polygon(hexd).buffer(0)
        # crown notch
        cw = s.crown_w * 1.1 * s.body_w
        top = body.bounds[1]
        notch = Polygon([
            (-cw, top - 0.02 * s.body_h),
            (cw, top - 0.02 * s.body_h),
            (0.0, top + 0.34 * s.body_h),
        ]).buffer(0)
        body = body.difference(notch).buffer(0)
        # split into a light-left / dark-right facet along a tilted axis for
        # readable contrast even at 16px.
        minx, miny, maxx, maxy = body.bounds
        big = 4 * max(maxx - minx, maxy - miny)
        # tilted half-plane through center
        cx, cy = (minx + maxx) / 2.0, (miny + maxy) / 2.0
        axis = rotate(Polygon([
            (cx, cy - big), (cx + big, cy - big),
            (cx + big, cy + big), (cx, cy + big),
        ]), -18, origin=(cx, cy))  # right half-plane, tilted
        right = body.intersection(axis).buffer(0)
        left = body.difference(axis).buffer(0)
        facets = []
        for g, tone in ((left, "light"), (right, "dark")):
            if g.is_empty:
                continue
            geoms = g.geoms if g.geom_type in ("MultiPolygon", "GeometryCollection") else [g]
            for poly in geoms:
                if poly.geom_type == "Polygon":
                    facets.append(Facet(pts=list(poly.exterior.coords), tone=tone))
        return facets

    # ---- CALYX: angular green blades ----------------------------------------
    def _blade(self, length, halfw):
        """One sharp isoceles triangle blade pointing up (-y), tip at distance len,
        base spanning [-halfw, halfw]. No curve, no rounding -> crisp + angular."""
        return Polygon([
            (-halfw, 0.0),
            (0.0, -length),   # the sharp point
            (halfw, 0.0),
        ])

    def _calyx(self) -> List[Tuple[object, str]]:
        return getattr(self, f"_calyx_{self.s.style}")()

    def _calyx_blades_fan(self) -> List[Tuple[object, str]]:
        """The shared radiating-blade fan used by lowpoly + mark."""
        s = self.s
        ax, ay = self.calyx_anchor
        n = s.blades
        if n == 1:
            angles = [0.0]
        else:
            half = s.blade_spread / 2.0
            angles = [-half + s.blade_spread * i / (n - 1) for i in range(n)]
        parts = []
        for i, a in enumerate(angles):
            t = abs(a) / (s.blade_spread / 2.0 + 1e-9)
            length = s.blade_len * (1.0 - 0.22 * t)  # outer blades shorter -> star
            blade = self._blade(length, s.blade_w * (1.0 - 0.18 * t))
            blade = rotate(blade, -a, origin=(0, 0))  # svg y-down: -a tilts outward
            blade = translate(blade, xoff=ax, yoff=ay)
            tone = "base"
            if s.two_tone_calyx:
                tone = "light" if i % 2 == 0 else "dark"
            parts.append((blade.buffer(0), tone))
        # a small ANGULAR hub (polygon, not circle) fuses the blade bases
        hub = Polygon(self._ngon(ax, ay, s.hub_r * s.body_w, s.hub_r * s.body_w,
                                 s.hub_sides, rot_deg=90.0)).buffer(0)
        parts.append((hub, "base"))
        return parts

    def _calyx_lowpoly(self):
        return self._calyx_blades_fan()

    def _calyx_mark(self):
        # fewer, bolder blades for the favicon mark
        return self._calyx_blades_fan()

    def _calyx_flat(self):
        """A single crisp angular green star (one solid green) seated INTO the
        crown notch — the clean, bold 2-color option. A 5-point spiky star whose
        lower points overlap the body shoulders so it reads as a fused calyx (no
        floating gap)."""
        s = self.s
        ax, ay = self.calyx_anchor
        # seat the star a touch lower so its base overlaps the octagon crown.
        ay = ay + 0.12 * s.body_h
        w = 0.66 * s.body_w
        up = 0.52 * s.body_h         # top spike reach (above body)
        side = 0.30 * s.body_h       # side spikes
        down = 0.16 * s.body_h       # lower points drape onto the shoulders
        inner = 0.16 * s.body_w      # inner radius (valley between points)
        star = Polygon([
            (0.0, ay - up),              # top spike
            (inner, ay - inner),
            (w, ay - side),              # upper-right spike
            (inner * 1.4, ay + inner * 0.4),
            (0.62 * w, ay + down),       # lower-right point (onto shoulder)
            (0.0, ay + inner * 0.5),     # bottom valley (overlaps body)
            (-0.62 * w, ay + down),      # lower-left point (onto shoulder)
            (-inner * 1.4, ay + inner * 0.4),
            (-w, ay - side),             # upper-left spike
            (-inner, ay - inner),
        ]).buffer(0)
        return [(star, "base")]

    # ---- transform model -> canvas (square; fit whole mark) -----------------
    def _full_bounds(self):
        return unary_union([self.body_geom, self.calyx_geom]).bounds

    def _tf(self):
        s = self.s
        S = s.canvas
        minx, miny, maxx, maxy = self._full_bounds()
        span = max(maxx - minx, maxy - miny)
        fill = 0.82 if s.style != "mark" else 0.88  # mark fills more for tiny sizes
        scale_f = fill * S / span
        cx = (minx + maxx) / 2.0
        cy = (miny + maxy) / 2.0
        return lambda x, y: (S / 2 + (x - cx) * scale_f, S / 2 + (y - cy) * scale_f)

    # ---- emission (via brando marklib) --------------------------------------
    def _bg_fill(self):
        if self.s.background == "none":
            return None
        return self.s.bg if self.s.background == "ink" else "#FFFFFF"

    def _canvas(self):
        s = self.s
        c = Canvas(size=s.canvas, tf=self._tf(), bg_round=s.bg_round)
        bg = self._bg_fill()
        if bg is not None:
            c.add_background(bg)
        # body facets, back-to-front. Each facet is its own flat-fill layer so the
        # low-poly multi-tone look survives into the per-layer SVGs and raster.
        if s.style == "lowpoly":
            # group facets by tone into 3 clean layers (base/dark/light) so the
            # emitted assets stay tidy while keeping the faceted appearance.
            for tone in ("dark", "base", "light"):
                geoms = [Polygon(f.pts).buffer(0) for f in self.facets if f.tone == tone]
                if geoms:
                    c.add_layer(f"body_{tone}", unary_union(geoms), self._tone(tone))
        else:
            for tone in ("dark", "base", "light"):
                geoms = [Polygon(f.pts).buffer(0) for f in self.facets if f.tone == tone]
                if geoms:
                    c.add_layer(f"body_{tone}", unary_union(geoms), self._tone(tone))
        # calyx blades, grouped by tone into clean layers
        for tone in ("dark", "base", "light"):
            geoms = [g for g, t in self.calyx_parts if t == tone]
            if geoms:
                c.add_layer(f"calyx_{tone}", unary_union(geoms), self._green(tone))
        return c

    def canvas(self):
        return self._canvas()

    def render(self, path):
        self._canvas().render(path)

    def emit(self, base):
        self._canvas().emit(base)


# The candidate family: 3 angular directions x (ink / transparent). Ink is the
# org-avatar background; transparent is for placing on any surface.
def _variants():
    v = {}
    for style in ("lowpoly", "flat", "mark"):
        v[f"{style}_inkbg"] = Spec(style=style, background="ink")
        v[f"{style}_transparent"] = Spec(style=style, background="none")
    return v


VARIANTS = _variants()


def main(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    for name, spec in VARIANTS.items():
        TomatoV2(spec).emit(os.path.join(out_dir, f"tomato_v2_{name}"))
        print(f"emit tomato_v2_{name} -> {out_dir}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ".")
