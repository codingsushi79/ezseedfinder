# EZ Seed Finder

Fast, GUI-based Minecraft Java Edition seed finder with an extensive `.ezsf` criteria language.

Powered by [cubiomes](https://github.com/Cubitect/cubiomes) via a vendored [cubiomespi-fork](https://pypi.org/project/cubiomespi-fork/) build for accurate structure and biome generation.

## Features

- **GUI** — set version, structure distances, stronghold options, and spawn filters
- **`.ezsf` files** — expressive criteria syntax for complex multi-dimension searches
- **Multi-threaded** — uses all CPU cores for fast random/sequential scanning
- **Structures** — villages, temples, mansions, monuments, ruined portals, ancient cities, trial chambers, and more
- **Dimensions** — overworld, nether, and end criteria in one search
- **Strongholds** — nearest distance, ring selection, max angle from spawn, under-spawn and full stronghold (heuristic — see Notes)
- **Biomes** — point checks, region percentages, spawn biome
- **Bastions** — variant filtering (treasure, housing, stables, bridge)
- **Distance rules** — e.g. village and ruined portal within 200 blocks of each other
- **Terrain / mobs / loot** — terrain heuristics (experimental), mob biome proxies, version-aware chest loot

## Quick Start

### Install from PyPI

```bash
pip install ezseedfinder
ezsf -gui                  # graphical interface (requires tkinter)
ezsf -f criteria.ezsf      # headless CLI search
ezsf --village 500 -n 10   # quick village filter
```

**GUI requires tkinter.** On Debian/Ubuntu: `sudo apt install python3-tk`

**Windows:** pip builds a native cubiomes library during install (requires [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) with the “Desktop development with C++” workload). If pip selects a wheel built for another OS, it falls back to the source package and compiles locally.

### Development

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
ezsf -gui
ezsf -f examples/speedrun.ezsf -n 5
```

## GUI Usage

1. Pick a **Minecraft version** (1.12.2 – 26.2, default **26.2**)
2. Set **structure distances** in blocks (0 = ignore)
3. Enable **stronghold** options if needed
4. Optionally edit the **`.ezsf`** panel for advanced criteria
5. Click **Start Search** — results appear in the table (double-click to copy seed)

## `.ezsf` Syntax Reference

```ezsf
version 26.2
threads 8
max_results 10
random                    # or: sequential
seed_range start 0 end 1000000

spawn within 2000 of origin
spawn biome plains | forest

stronghold nearest within 1500 of spawn
stronghold under spawn
stronghold full
stronghold ring 1
stronghold max_angle 90

dimension overworld {
  biome at 0, 64, 0 plains | meadow
  biome region -512, -512 to 512, 512 y 64 contains desert >= 10%
  structure village within 500 of spawn viable
  structure between village and desert_pyramid within 800 of spawn viable
  ruined_portal within 300 of spawn viable giant false top_missing 1 chest item obsidian min 1 chest item flint_and_steel min 1
  terrain at 0, 0 flat radius 128
}

dimension nether {
  structure fortress within 400 of 0,0 viable
  bastion variant treasure within 600 of spawn viable
}

dimension end {
  structure end_city within 1000 of 0,0 viable
}

distance village ruined_portal <= 200 in overworld
mob witch within 200 of spawn in overworld biome swamp
loot at ruined_portal item obsidian min 1 within 500 of spawn in overworld
```

### Structure variants

Ruined portals support cubiomes variant flags plus frame/loot simulation (1.16.1+):

- `giant true|false` — giant portal template
- `underground true|false`, `airpocket true|false`, `template 3` — placement variant
- `top_missing N` — obsidian holes on the top row of the portal frame (after crying-obsidian RNG)
- `frame_missing N` — total frame holes (optional; templates usually need 3+ blocks to complete)
- `chest item <name> min N` — ruined portal chest loot (obsidian, flint_and_steel, gold_ingot, etc.)

Bastions: `bastion variant treasure|housing|stables|bridge within 600 of spawn`

### Point references

- `spawn` — world spawn
- `origin` or `0,0` — world origin
- `x, z` — explicit coordinates

### Structures

`village`, `desert_pyramid`, `jungle_temple`, `swamp_hut`, `igloo`, `ocean_ruin`, `shipwreck`, `monument`, `mansion`, `outpost`, `ruined_portal`, `ancient_city`, `treasure`, `mineshaft`, `fortress`, `bastion`, `end_city`, `trail_ruin`, `trial_chambers`, and more.

### Notes

- **Full stronghold** — cubiomes does not simulate portal room layout; `stronghold full` uses a ring-1 proximity heuristic.
- **Under spawn** — nearest stronghold within ~250 blocks of spawn (approximate).
- **Stronghold angle** — `max_angle N` checks ring-1 stronghold angular distance from +Z at spawn (exact position from cubiomes).
- **Chest loot** — version-aware vanilla loot tables for ruined portal, buried treasure, shipwreck, desert/jungle temple, bastion treasure, ancient city, and trail ruins (1.21+). Uses structure variant Y when cubiomes provides it.
- **Ruined portal frame** — overworld and nether; extracted vanilla templates with crying-obsidian RNG.
- **Terrain / height** — experimental biome-based proxies in the GUI; not true surface noise.
- **Mob rules** — biome suitability proxy; expanded mob list in GUI.
- **Seed map preview** — planned; see `ROADMAP.md`.

## Examples

See bundled examples (``ezseedfinder/examples/`` after install, or ``examples/`` in the repo):

- `ruined_portal_speedrun.ezsf` — **1.16.1** portal_6 frame + chest loot speedrun
- `speedrun.ezsf` — **1.16.1** village + portal + stronghold + nether
- `advanced.ezsf` — biomes, terrain, mobs, all dimensions

## License

MIT
