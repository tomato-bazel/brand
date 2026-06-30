# tomato-brand

The tomato-bazel visual identity — tomato CONTENT (the parametric tomato mark +
palette) consuming the reusable brand pipeline from [`brando`](../brando).

tomato-bazel is a curated fork / distribution of Bazel (a "Bazel distro"). Its
mark is its OWN brand: a clean, modern, friendly tomato. The green calyx on top
is a deliberate nod to Bazel's green-leaf logo — the bridge between the brands.

## Build

Everything is hermetic — the generator runs in-build (shapely/svgwrite/pillow
wheels), importing `@brando//marklib`:

```sh
bazel build //gen:tomato_svgs   # canonical layered SVGs, every variant
bazel build //icons:tomato_icons   # org-avatar PNGs (512 + 1024)
bazel build //...
```

## Variants

| variant       | background | body        |
|---------------|------------|-------------|
| `inkbg`       | ink rounded-square | gradient |
| `inkbg_flat`  | ink rounded-square | flat (no gradient/highlight) |
| `transparent` | none       | gradient |
| `whitebg`     | white rounded-square | gradient |

## Architecture

The reusable machinery — the shapely→layered-SVG/composite emission, the Pillow
rasterizer, the layered/Icon-Composer output convention — lives in `brando`. This
repo holds only the tomato geometry (`gen/gen_tomato.py`) and palette. During
development `brando` is bridged via `local_path_override`; flip to the published
registry version once it lands.
