# Hamsa Nomads Caption Style Guide

All styles now follow the Hamsa Nomads brand system in `brand/hamsa_nomads_brand.json`.
They use warm cream/parchment surfaces, ink text, clay and olive accents, and route/passport/map-inspired details.

The styles are still plain ASS subtitles rendered by FFmpeg, so they work on Windows without Adobe, Premiere, After Effects, paid APIs, or cloud design tools.

## Shared brand language

- **Colors:** warm cream, ivory parchment, sand, clay, olive/sage, ink black.
- **Typography:** Playfair Display for headline moments, Montserrat for readable body captions, Caveat for handwritten accents when available. The brand file includes Windows-safe fallbacks for PCs without those fonts.
- **Visual signature:** imperfect line, route mark, map path, passport note, travel-document texture.
- **Avoid:** neon arcade colors, glossy corporate cards, childish effects, cheap CapCut-style flashes.

## `hamsa-clean`

**Visual feel:** elegant documentary lower-third.

- Cream/parchment caption box.
- Ink black text.
- Subtle olive outline and clay route mark.
- Best for: general Hamsa Nomads storytelling, clean travel notes, grounded talking-head captions.

**Example look:**

```text
⌁
We found a quiet street
behind the main square.
```

## `paris-tip`

**Visual feel:** passport stamp / travel note.

- Small `PARIS TIP` label.
- Parchment box with sand/clay accents.
- Clean lower-third placement.
- Best for: Paris tips, kosher food notes, neighborhood advice, museum/cafe/hotel recommendations.

**Example look:**

```text
PARIS TIP
Ask before you order — the quiet places
usually know the best shortcuts.
```

## `game`

**Visual feel:** warm travel quest, not neon arcade.

- Labels alternate between `QUEST UNLOCKED` and `LOCAL TIP`.
- Cream box, ink text, clay/olive accents.
- Looks like a premium travel adventure card rather than a loud gaming overlay.
- Best for: route discoveries, hidden spots, itinerary wins, “we found it” moments.

**Example look:**

```text
QUEST UNLOCKED
route note •
Find the side street before sunset.
```

## `wrong-vs-right`

**Visual feel:** calm correction card.

- Wrong line uses clay.
- Correct line uses olive/sage.
- Parchment box keeps the layout readable and warm.
- Best for: travel mistakes, kosher phrasing, etiquette, what to ask for.

**Example look:**

```text
ASK IT BETTER
❌ Don’t ask: Cholov Yisroel
✅ Ask: Chamour
```

## `video-game-dialogue`

**Visual feel:** premium story/adventure dialogue box.

- Cream box.
- Black text.
- Clay speaker label and olive border.
- Map-path detail instead of pixel/neon effects.
- Best for: story narration, “traveler says...” commentary, guided journey clips.

**Example look:**

```text
HAMSA NOMADS
— map path —
Traveler: We should take the side road.
```

## Style selection in the batch file

Double click `run_hamsa.bat`, then choose:

```text
1 game
2 paris-tip
3 hamsa-clean
4 wrong-vs-right
5 video-game-dialogue
```

For weak Windows PCs with Intel graphics, start with `hamsa-clean` or `paris-tip` while testing because they are clean, lightweight, and readable on most footage.
