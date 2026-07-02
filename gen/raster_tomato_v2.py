#!/usr/bin/env python3
"""Rasterize the ANGULAR tomato v2 — hermetic, via brando's marklib raster.

Mirrors gen_tomato_v2.py's canvas construction: draws the body facet tone-groups
back-to-front (dark -> base -> light), then the angular green calyx blade
tone-groups. Every fill is FLAT (no gradients) so the faceting reads as crisp,
designed planes. Antialiasing is by rendering at 4x and downsampling.

CLI: raster_tomato_v2.py <out-dir>
"""
import os
import sys

from PIL import Image
from shapely.geometry import Polygon
from shapely.ops import unary_union

from gen_tomato_v2 import Spec, TomatoV2, VARIANTS
from marklib import raster as mraster

PNG_SIZES = [512, 1024]
SS = 4  # supersample factor for antialiasing


def raster(spec, size):
    big = size * SS
    s = Spec(**{**spec.__dict__, "canvas": big})
    t = TomatoV2(s)
    tf = t._tf()
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    if s.background != "none":
        bg = s.bg if s.background == "ink" else "#FFFFFF"
        mraster.background_rect(img, big, bg, s.bg_round)
    # body facet tone-groups, back-to-front (flat fills)
    for tone in ("dark", "base", "light"):
        geoms = [Polygon(f.pts).buffer(0) for f in t.facets if f.tone == tone]
        if geoms:
            mraster.paste_geom(img, big, tf, unary_union(geoms), t._tone(tone))
    # calyx blade tone-groups (flat green facets)
    for tone in ("dark", "base", "light"):
        geoms = [g for g, gt in t.calyx_parts if gt == tone]
        if geoms:
            mraster.paste_geom(img, big, tf, unary_union(geoms), t._green(tone))
    return img.resize((size, size), Image.LANCZOS)


def emit(out_dir, name, spec):
    for sz in PNG_SIZES:
        raster(spec, sz).save(os.path.join(out_dir, f"tomato_v2_{name}_{sz}.png"))
    print(f"icons tomato_v2_{name}")


def main(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    for variant, spec in VARIANTS.items():
        emit(out_dir, variant, spec)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ".")
