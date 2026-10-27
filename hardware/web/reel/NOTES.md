# Reel notes

Learnings from making 3D room reels. These notes are the draft for a future `gtm-reel` skill in the copilot repo.
Add to them after each reel.

## Pipeline (works)

- **Scene page:** a three.js page exposes `window.seek(t)`. Each call sets every object, the camera and the captions
  for time `t`, then renders. There is no real-time clock, so every frame is deterministic.
- **Render:** `render_reel.js` steps through `t = f / 30` in Playwright, screenshots each frame as JPEG and pipes it
  into ffmpeg (`image2pipe`, x264, CRF 18, yuv420p, faststart).
  - A 15 s, 1080×1920 reel is 450 frames and takes about 3 minutes on SwiftShader.
- **Sandbox:** the jsDelivr CDN is blocked. `npm i three@<version>` in the scratchpad, then pass `--three`; the
  renderer serves that file to the page in place of the CDN copy.
- **Preview before the full render:**
  - Render 5–10 stills at key times (`--preview t1,t2,...`) and tile them with ffmpeg `hstack`.
  - Read the contact sheet, fix, repeat. v1 needed 4 preview rounds.
- **Final check:** after the full render, tile one frame per second (`fps=1,tile=8x2`).

## Shots and camera

- **Vertical frame:** 9:16 makes the horizontal FOV narrow (about 29° at a vertical FOV of 50).
  - A 1.8 m board can't fit head-on in a 3.3 m room.
  - Use FOV 62–68 for hero shots, or angle the camera along the wall.
- **Walls:** make them single-sided planes facing inward. The camera can then sit outside the room and the near
  walls vanish.
- **Line of sight:** tall boxes (wardrobes, lofts) still block the view. Check every keyframe for this.
  - Wide shots work from above the open side, at y ≥ 4.5 m.
  - Move between keyframes over furniture, never through it. v1 flew through a wardrobe at 2.6 s.
- **Easing:**
  - ease-in-out cubic for moves
  - quintic for the one whip
  - ease-out on the hero push-in
  - back-ease (overshoot) for objects dropping in
- **Structure:**
  - hook in the first second (walls rising, a counter ticking)
  - a hero beat around 4–9 s
  - "next" teasers as glowing outlines
  - the end camera equals the start camera, so the reel loops
- **Contrast:** a dark hero object needs a light wall behind it. The black board vanished on a dark teal wall C.
- **Teaser outlines:** a 1 px line is too faint at 1080 px. Use a fill opacity of 0.3 or more, with a slow pulse.

## Captions

- **Safe zone:** keep text in the top third, below the platform UI. Keep it out of the bottom ~400 px, which the reel
  buttons and caption cover.
- **Scrim:** a dark top gradient keeps captions legible over a bright floor.
- **Length:** a caption needs at least 1.8 s on screen. Keep one big line plus one mono sub-line.

## Content truth

- **Source:** the reel's object list comes from Harbor Now, so every mistake in Now shows up in the reel. v1 had a
  "trestle table" that was really the UTESPELARE desk, and a light stand that isn't there.
- **Before rendering:** confirm every unconfirmed (`check`) item with Allwin.
- **Tidy, never invent:** leaving things out for looks (like the sawhorses) is fine. Adding things that aren't real
  is not; those go in as teaser outlines labelled "next".

## Next ideas

- **Textures:** wood grain on the floor and the ply edges, a pegboard hole pattern on the SKÅDIS, a matte black board.
- **Tighter script:** beats on a fixed BPM, so each object lands on a beat. Pick the track first, then time to it.
- **Audio:** the renderer has no sound yet. ffmpeg could mux a track (`-i track.mp3 -shortest`).
