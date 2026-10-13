# Visual style guide

The default visual language (everything is configurable under `theme:` in `story.yaml`).

## Principles

1. **A single visualization that transforms.** One continuous map: the camera flies, zooms, dives into a satellite
   image and comes back. No cuts to slides.
2. **One idea per scene.** One big number, one short line. If it needs explaining, it is another scene.
3. **The data is the light.** Near-black background; the only bright thing is the data (points, areas, the number). Everything else is muted context.
4. **Human scale and baselines.** "twice as much as ten years ago", "3 in 10": comparisons that make sense without axes.
5. **Readable on a phone**, on first viewing, without pausing (the harness rules guarantee it).

## Color

| Role | Palette key | Default value | Use |
|---|---|---|---|
| Background | `bg` | `#060609` | the whole background |
| Land | `land` | `#141316` | map regions |
| Neighbours | `neighbour` | `#0D0D11` | context outside the area |
| Borders | `border` | `#3E3C40` | boundaries, thin |
| Text | `text` | `#F2F0EC` | headlines, neutral numbers |
| Secondary text | `muted` | `#BEB6AC` | legends, sources |
| Accent | `accent` | `#FF6E1E` | the key word, the title's second line |
| Accent 2 | `accent2` | `#FFB03C` | mono headers, highlighted outlines, sublines |
| Hot | `hot` | `#FFE2A0` | the hero number, glowing outlines |
| Red | `red` | `#FF4028` | the most severe / most recent |
| Ash | `ash` | `#968E86` | affected areas, what already happened |

Data ramp (`lut`): black → maroon → orange → amber → warm white. Points and choropleths use that ramp;
the more data, the whiter. For other topics (water, cold), switch `accent*` and `lut` to blues, keeping the contrast.

## Typography

| Role | Font (OFL, included) | Size (px at 1080p) |
|---|---|---|
| Headline / numbers | **Anton** (condensed, uppercase) | number 150 · headline 116–132 · closing 110–124 · subline 66 · unit 80 |
| Scene headers | **JetBrains Mono** 800 | 52 |
| Legends, sources, labels | **Inter** 500–600 | 48 (absolute minimum) |

- Everything in the left third (x = 110 px); the map lives on the right. A soft shadow darkens the text area.
- Uppercase for headlines and numbers; sentence case for sources and legends.
- Numbers in local format (`es`: 12.345 · 12,5).

## Motion

- **Slam**: text enters large (×1.45) and drops to its size in ~0.28 s with a glow flash; it exits with a fade and a slight rise.
- **Counting numbers** (`count_to`) land exactly on the rounded value.
- **Camera**: `zoomto` to approach a region, `fly` between regions (zooms out just enough for both ends to be visible), `ease` for gentle adjustments.
- **Flash + hit** on each important reveal; shake (`shake`) only at 2–3 moments.
- **Glow/bloom** on data and key titles; fixed vignette and film grain.

## Sound

Low drone + looping pads, hits (boom/taiko/braam) on each reveal, a whoosh on each camera move, ticks per
year/region, a short silence before the closing line. −14 LUFS.

## What to avoid

- More than ~12 words on screen at once, text < 48 px, text that stays on screen less time than it takes to read.
- Legends that do not explain themselves («1 punto = 1 sismo» / "1 dot = 1 earthquake" yes; an unexplained dot no).
- Stock photos, decorative icons, AI-generated images.
