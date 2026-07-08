# Roadmap / future work

## Seed map preview (not started)

2D biome and structure overlay for a found seed — high UX value, large effort.

**Scope sketch:**
- Render overworld biome map (and optional structure icons) for a seed at a chosen radius
- Click result row → show map centered on spawn or selected structure
- Optional nether/end tabs
- Likely needs: biome sampling via cubiomes, canvas or embedded image in tkinter, chunk-aligned grid

**Dependencies:** stable result detail coords from checker; performance budget for 512×512+ previews.

**Status:** TODO only — do not implement until dedicated milestone.
