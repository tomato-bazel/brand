#!/usr/bin/env python3
"""tomato-bazel mark — a friendly, fully-parametric TOMATO.

tomato-bazel is a curated fork / distribution of Bazel (a "Bazel distro"). Its
mark is its OWN brand: a clean, modern, friendly tomato. The green calyx on top
is a deliberate nod to Bazel's green-leaf logo — the bridge between the brands.

ONE Spec drives everything, mirroring gen_mark.py: shapely is the exact CSG
(boolean polygon ops on the body lobes, dimple, calyx leaves and stem);
emission is svgwrite, as canonical LAYERS (bg / body / calyx) + a composite, so
the same Spec yields the flat SVG, the gradient SVG and the per-layer assets.

Geometry lives in a unit-ish model space centered on the body; `_tf` maps it to
the square canvas with a small optical-center nudge. Construction is
deterministic — no randomness — so the output is reproducible.

CLI: `gen_tomato.py <out-dir>` emits every VARIANT's layered set into <out-dir>.
"""
import math
import os
import sys
from dataclasses import dataclass

from shapely.affinity import rotate, translate
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

from marklib import Canvas, geom_to_path


@dataclass
class Spec:
    # ---- body geometry (model units; body roughly spans x in [-1,1]) ----
    body_w: float = 1.00          # body half-width
    body_h: float = 0.84          # body half-height (wider than tall -> friendly)
    lobes: int = 4                # side-lobe ellipses unioned in for subtle vertical lobing
    lobe_spread: float = 0.30     # how far the outer lobes sit from center (frac of body_w)
    lobe_w: float = 0.62          # lobe half-width (frac of body_w)
    lobe_h: float = 0.97          # lobe half-height (frac of body_h)
    round_amt: float = 0.06       # buffer-rounding of the body (frac of body_w) -> smooth seams
    dimple: float = 0.05          # bottom dimple depth (0 = none); a soft, shallow base notch
    dimple_w: float = 0.26        # dimple half-width (frac of body_w)
    top_flat: float = 0.06        # flatten the body crown slightly so the calyx seats cleanly

    # ---- calyx (the green star on top) ----
    leaves: int = 5               # number of radiating leaf points (5 or 6)
    leaf_len: float = 0.60        # leaf length (model units, from the calyx anchor)
    leaf_w: float = 0.24          # leaf half-width at its base (broader = friendlier)
    leaf_curve: float = 0.16      # sideways curve of each leaf tip (0 = straight)
    leaf_round: float = 0.07      # buffer-rounding of the calyx (frac of leaf_len)
    leaf_spread: float = 210.0    # total fan angle covered by the leaves (degrees)
    hub_r: float = 0.18           # central hub radius (frac of body_w) the leaves spring from
    calyx_y: float = 0.04         # vertical offset of the calyx anchor below body top (model units)
    stem_w: float = 0.075         # stem nub half-width
    stem_h: float = 0.20          # stem nub height above the calyx anchor

    # ---- colors ----
    body: str = "#E64A33"         # primary body red
    body2: str = "#C0392B"        # deeper gradient end (bottom); used iff gradient=True
    calyx: str = "#3FA34D"        # Bazel-leaning leaf green
    calyx2: str = "#2E7D3A"       # deeper calyx gradient end; used iff gradient=True
    highlight: str = "#FFFFFF"    # soft specular highlight color
    bg: str = "#15161A"           # ink rounded-square bg (matches fastverk family)

    # ---- toggles ----
    gradient: bool = True         # subtle vertical gradient on body + calyx
    show_highlight: bool = True   # soft specular highlight on the body
    highlight_opacity: float = 0.16
    background: str = "ink"       # ink | white | none(transparent)
    bg_round: float = 0.22        # rounded-square corner radius (frac of canvas)
    canvas: int = 1024


class Tomato:
    """Deterministic shapely construction + svgwrite emission of the tomato."""

    SEG = 96  # polygon segments per ellipse (smooth enough at 1024px)

    def __init__(self, s: Spec):
        self.s = s
        self.body_geom = self._body()
        # anchor the calyx just below the body crown, on the center axis, so the
        # leaf bases overlap the shoulders (no floating star).
        _, miny, _, _ = self.body_geom.bounds
        self.calyx_anchor = (0.0, miny + s.calyx_y * s.body_h)
        self.calyx_geom = self._calyx()

    # ---- primitives ----
    @staticmethod
    def _ellipse(cx, cy, rx, ry, n=SEG):
        return Polygon([
            (cx + rx * math.cos(2 * math.pi * i / n),
             cy + ry * math.sin(2 * math.pi * i / n))
            for i in range(n)
        ])

    @staticmethod
    def _round(g, r):
        # smooth seams/corners: dilate then erode (a morphological closing-ish round).
        if r <= 0:
            return g.buffer(0)
        return g.buffer(r, join_style=1).buffer(-r, join_style=1).buffer(0)

    # ---- body: a soft superellipse-ish blob from unioned lobes, minus a dimple ----
    def _body(self):
        s = self.s
        parts = [self._ellipse(0.0, 0.0, s.body_w, s.body_h)]
        if s.lobes > 0:
            # symmetric side lobes give the SUBTLE vertical lobing of a real tomato.
            # They sit close to center and are tall+narrow, so the union stays a
            # single gently-undulating blob rather than a lumpy cluster.
            n_each = max(1, s.lobes // 2)
            for k in range(1, n_each + 1):
                dx = s.lobe_spread * s.body_w * k / n_each
                rx = s.lobe_w * s.body_w * (1.0 - 0.10 * (k - 1))
                ry = s.lobe_h * s.body_h
                parts.append(self._ellipse(dx, 0.0, rx, ry))
                parts.append(self._ellipse(-dx, 0.0, rx, ry))
        body = self._round(unary_union(parts), s.round_amt * s.body_w)
        if s.top_flat > 0:  # gently flatten the crown so the calyx seats cleanly
            top = body.bounds[1]
            body = body.difference(
                box(-2 * s.body_w, top, 2 * s.body_w, top + s.top_flat * s.body_h)).buffer(0)
        if s.dimple > 0:  # shallow, soft notch at the base (a tomato's blossom end)
            notch = self._ellipse(0.0, s.body_h + s.dimple * 0.4,
                                  s.dimple_w * s.body_w, s.dimple * s.body_h * 1.4)
            body = self._round(body.difference(notch), 0.5 * s.round_amt * s.body_w)
        return body

    # ---- one tapered, gently-curved leaf pointing "up" (-y), tip at distance len ----
    def _leaf(self, length, halfw, curve):
        # A smooth leaf: base spans [-halfw, halfw], a bulged shoulder, then a tip
        # offset sideways by curve*len. Extra mid-points keep the silhouette soft.
        tipx = curve * length
        pts = [
            (-halfw, 0.10 * length),
            (-0.92 * halfw, -0.30 * length),
            (tipx - 0.18 * halfw, -0.74 * length),   # upper-left shoulder
            (tipx, -length),                          # the point
            (tipx + 0.18 * halfw, -0.74 * length),   # upper-right shoulder
            (0.92 * halfw, -0.30 * length),
            (halfw, 0.10 * length),
        ]
        return Polygon(pts).buffer(0)

    def _calyx(self):
        s = self.s
        ax, ay = self.calyx_anchor
        parts = []
        n = s.leaves
        # fan the leaves across leaf_spread, centered on straight-up. A wide spread
        # lets the outer leaves drape down over the tomato's shoulders.
        if n == 1:
            angles = [0.0]
        else:
            half = s.leaf_spread / 2.0
            angles = [-half + s.leaf_spread * i / (n - 1) for i in range(n)]
        for a in angles:
            # outer leaves a touch shorter than the central one
            t = abs(a) / (s.leaf_spread / 2.0 + 1e-9)
            length = s.leaf_len * (1.0 - 0.16 * t)
            # curl every tip outward (away from center) for an organic star
            sign = -1.0 if a < 0 else (1.0 if a > 0 else 0.0)
            leaf = self._leaf(length, s.leaf_w, s.leaf_curve * sign)
            leaf = rotate(leaf, -a, origin=(0, 0))  # svg/shapely y-down: -a tilts outward
            leaf = translate(leaf, xoff=ax, yoff=ay)
            parts.append(leaf)
        # a small central hub fuses the leaf bases into one clean star (no gaps)
        parts.append(self._ellipse(ax, ay, s.hub_r * s.body_w, s.hub_r * s.body_w))
        # central stem nub rising from the hub
        stem = Polygon([
            (ax - s.stem_w, ay),
            (ax + s.stem_w, ay),
            (ax + s.stem_w * 0.6, ay - s.stem_h),
            (ax - s.stem_w * 0.6, ay - s.stem_h),
        ]).buffer(0)
        parts.append(stem)
        return self._round(unary_union(parts), s.leaf_round * s.leaf_len)

    # ---- transform model -> canvas (square, with a slight optical-center nudge) ----
    def _tf(self):
        s = self.s
        S = s.canvas
        # fit the whole mark (body + calyx) into ~78% of the canvas
        minx, miny, maxx, maxy = self._full_bounds()
        span = max(maxx - minx, maxy - miny)
        scale_f = 0.80 * S / span
        cx = (minx + maxx) / 2.0
        cy = (miny + maxy) / 2.0
        return lambda x, y: (S / 2 + (x - cx) * scale_f, S / 2 + (y - cy) * scale_f)

    def _full_bounds(self):
        u = unary_union([self.body_geom, self.calyx_geom])
        return u.bounds

    def _d(self, g):                                # geometry -> SVG path (marklib)
        return geom_to_path(g, self._tf())

    # ---- soft specular highlight: a small tilted ellipse on the upper-left body ----
    def _highlight_geom(self):
        s = self.s
        minx, miny, maxx, maxy = self.body_geom.bounds
        cx = minx + 0.33 * (maxx - minx)
        cy = miny + 0.26 * (maxy - miny)
        e = self._ellipse(cx, cy, 0.24 * s.body_w, 0.14 * s.body_h)
        e = rotate(e, -30, origin=(cx, cy))
        return e.intersection(self.body_geom)

    # ---- emission (via brando marklib) ----
    def _bg_fill(self):
        if self.s.background == "none":
            return None
        return self.s.bg if self.s.background == "ink" else "#FFFFFF"

    def _canvas(self):                              # assemble the marklib Canvas
        s = self.s
        c = Canvas(size=s.canvas, tf=self._tf(), bg_round=s.bg_round)
        bg = self._bg_fill()
        if bg is not None:
            c.add_background(bg)
        body_grad = (s.body, s.body2) if s.gradient else None
        c.add_layer("body", self.body_geom, s.body, gradient=body_grad)
        if s.show_highlight:
            # composite-only overlay (no standalone .highlight.svg asset).
            hl = self._highlight_geom()
            c.add_layer("highlight", hl, s.highlight,
                        opacity=s.highlight_opacity, emit_file=False)
        calyx_grad = (s.calyx, s.calyx2) if s.gradient else None
        c.add_layer("calyx", self.calyx_geom, s.calyx, gradient=calyx_grad)
        return c

    def canvas(self):
        return self._canvas()

    def render(self, path):
        self._canvas().render(path)

    def emit(self, base):
        self._canvas().emit(base)                   # bg/body/calyx layers + composite


# The candidate family. Variants differ in background + flat-vs-gradient body, so
# a human can pick (gradient is generally nicer; flat is the safe fallback).
VARIANTS = {
    # primary: subtle gradient body + calyx on the fastverk ink rounded-square
    "inkbg":          Spec(background="ink", gradient=True),
    # flat (no gradient, no highlight) on ink — the conservative org-avatar option
    "inkbg_flat":     Spec(background="ink", gradient=False, show_highlight=False),
    # transparent (no background) gradient mark — for placing on any surface
    "transparent":    Spec(background="none", gradient=True),
    # white rounded-square background gradient mark — light-context avatar
    "whitebg":        Spec(background="white", gradient=True),
}

# Every layer file emit() can produce (for Bazel `outs` declaration).
LAYERS = ["svg", "bg.svg", "body.svg", "calyx.svg"]


def main(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    for name, spec in VARIANTS.items():
        Tomato(spec).emit(os.path.join(out_dir, f"tomato_{name}"))
        print(f"emit tomato_{name} -> {out_dir}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ".")
