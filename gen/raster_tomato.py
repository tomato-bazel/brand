#!/usr/bin/env python3
"""Rasterize the tomato — hermetic, via brando's marklib raster helpers.

Mirrors the fastverk rasterizer: draws the shapely polygons directly (exterior
filled, holes punched), composites bg / body / highlight / calyx, and renders body
and calyx as vertical gradients when the spec sets gradient=True. Antialiasing is
done by rendering at 4x and downsampling (Pillow's polygon fill is hard-edged).

tomato CONTENT: the per-variant palette + the avatar sizes. The Pillow plumbing
lives in @brando//marklib:raster.

CLI: raster_tomato.py <out-dir>
"""
import os
import sys

from PIL import Image

from gen_tomato import Spec, Tomato, VARIANTS
from marklib import raster as mraster

PNG_SIZES = [512, 1024]
SS = 4  # supersample factor for antialiasing


def raster(spec, size):
    big = size * SS
    s = Spec(**{**spec.__dict__, "canvas": big})
    t = Tomato(s)
    tf = t._tf()
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    # background rounded-square (ink or white); transparent when background == "none"
    if s.background != "none":
        bg = s.bg if s.background == "ink" else "#FFFFFF"
        mraster.background_rect(img, big, bg, s.bg_round)
    # body
    mraster.paste_geom(img, big, tf, t.body_geom, s.body, s.body2, gradient=s.gradient)
    # soft specular highlight on the body
    if s.show_highlight:
        hl = t._highlight_geom()
        mraster.paste_geom(img, big, tf, hl, s.highlight,
                           opacity=int(s.highlight_opacity * 255))
    # calyx (green star) on top
    mraster.paste_geom(img, big, tf, t.calyx_geom, s.calyx, s.calyx2, gradient=s.gradient)
    return img.resize((size, size), Image.LANCZOS)


def emit(out_dir, name, spec):
    for sz in PNG_SIZES:
        raster(spec, sz).save(os.path.join(out_dir, f"tomato_{name}_{sz}.png"))
    print(f"icons tomato_{name}")


def main(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    for variant, spec in VARIANTS.items():
        emit(out_dir, variant, spec)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ".")
