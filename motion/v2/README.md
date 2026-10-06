# GenLayer × Rally — motion graphic v2 (1920×1080 · 60 fps · 35 s)

Final video: [`../genlayer-rally-v2-60fps.mp4`](../genlayer-rally-v2-60fps.mp4) — H.264 High, yuv420p, 60 fps, AAC 48 kHz, ready for an X/Twitter post.

## Storyboard (synced to a 120 BPM soundtrack)
| Time | Scene |
|---|---|
| 0–4s | Cold open: laser line, the GenLayer mark is drawn as a vector outline, pieces fly in, fill, shockwave, `GENLAYER` decodes |
| 4–8s | "There's a GenLayer campaign **LIVE** on **@RallyOnChain**" — slam type, outline marquee |
| 8–12s | Slot-machine counter rolls to **100,000** → **GLP PRIZE POOL** with burst, HUD rings, synth grid |
| 12–16s | "Open to **ANYONE** who wants to create **REAL CONTENT.**" over a node network |
| 16–22s | "It's simple." — 3 glass cards: **01 JOIN** the campaign on Rally · **02 QUOTE** the post below · **03 SHARE** your own take on GenLayer |
| 22–26s | **NO FARMING** / **NO COPY-PASTE** get struck through → "just what you **ACTUALLY UNDERSTAND** about it." |
| 26–30.5s | Pigeon avatar: "I already joined and posted mine." → Robin-Hood arrow hits the target → **@MoStory8 — YOU'RE NEXT.** |
| 30.5–35s | Outro: GenLayer mark, 100,000 GLP prize pool, join on @RallyOnChain, **DON'T MISS IT** |

Palette: `#ff87ff`, `#dc00ff`, purple, white.

## How it's made
- `index.html` — the whole animation, deterministic `render(t)`. 2D canvas for scene content, then a WebGL pass composites a procedural nebula / synth-grid / god-ray background with bloom, anamorphic streaks, chromatic aberration, glitch slices, zoom blur, film grain and vignette. Open it in a browser for a live preview (click to play audio; `#t=12.5` shows one frame).
- `soundtrack.py` — synthesizes the music + SFX (numpy only), hit-synced to the visual timeline.
- `render.mjs` — renders every frame in headless Chromium across parallel workers and encodes with ffmpeg.

```bash
python3 soundtrack.py          # -> soundtrack.wav
node render.mjs video 4        # -> out/genlayer-rally-v2-60fps.mp4
node render.mjs stills 9.9 29  # -> out/still-*.png
```
