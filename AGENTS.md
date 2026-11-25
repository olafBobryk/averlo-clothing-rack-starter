# Agent instructions

You are setting up a 3D clothing rack for the person you're working with: their own shirts hang on a rail, swivel to
face the viewer, and open into a detail view where they can flip each shirt front/back and change its fabric colour.
Keep it simple and local. Ask before anything that costs money, uses credits, or puts something online.

## 1. Ask first

- Where their shirt photos are. Each shirt needs two photos of the same shirt: `front` and `back`. Put them in
  `shirts/<shirt-name>/front.jpg` and `shirts/<shirt-name>/back.jpg` (see [shirts/README.md](shirts/README.md)).
- What each shirt is called, and whether they want one shirt first or the whole collection.
- Three fabric colours per shirt, or let you suggest them.

## 2. Set up the app

1. This folder isn't empty, so `create-next-app` refuses it. Scaffold in a sibling folder:
   `npx create-next-app@latest ../rack-tmp --ts --app --tailwind --eslint --no-src-dir --use-npm --yes`. Move
   everything except `.git`, `AGENTS.md`, `CLAUDE.md` and `README.md` into this folder, append its `.gitignore` to
   ours, then delete `../rack-tmp`. In `next.config.ts` set `agentRules: false`, or `next dev` rewrites this file.
2. `npx shadcn@latest init --defaults`, then install the free Clothes Rack component from DiMaac UI:
   `npx shadcn@latest add @dimaac/clothes-rack` (fallback: `npx shadcn@latest add https://ui.dimaac.com/r/clothes-rack.json`).
   It adds `components/dimaac/` and `three`; add the types yourself: `npm i -D @types/three`.
   Its licence lets them use it in their own and client projects. `components/dimaac/` is gitignored: never commit it
   here or to any public repo, and never paste its source anywhere else.
3. Keep the page light: put `data-theme="light"` on `<html>` (the rack follows the page theme) and a white body.
   Import [rack-ui.css](rack-ui.css) in `app/layout.tsx`.

## 3. Cut the prints out (free, local)

1. The **shirt panel** is the flat body piece the component draws a print on, the same box for front and back: from
   just above where the collar meets the shoulders down to just below the hem, and across the shoulders plus a hair
   either side (sleeves excluded). A tee's panel is 0.67 times as wide as it is tall, so when the hem is out of the
   photo, take the height as width / 0.67.
2. Run `python3 scripts/cut-print.py PHOTO public/prints/<shirt-name>-front.png --torso X0 Y0 X1 Y1 --panel L T W H`
   for each photo (needs numpy, pillow, scipy). `--torso` is a pixel box over the body below the collar and hanger;
   `--panel` is the panel above in photo pixels. It prints the fabric hex and the print's `[x, y, width, height]`
   fractions of the panel. Cut the back photo as it is, without mirroring it.
3. Look at each PNG on a dark background. Background or shirt edge showing: raise `--edge`. Bits of print missing
   at the sides are usually the other side's print wrapping round, so it's right to drop them.
4. The script handles one ink colour. For a multi-colour print, or a photo that's too messy, AI cleanup (for example
   with Higgsfield) costs credits: quote them and wait for a yes before generating anything.

## 4. Fill rack.json

Copy [rack-starter.json](rack-starter.json) to `rack.json` and add one entry per shirt: `name`, `kind` (`tee`),
`colour` (the fabric hex the script printed), `prints.front` / `prints.back` (`[file, x, y, width, height]`, fractions
of the panel from its top left, so `0.2, 0.25, 0.6, 0.3` is a centred chest print), and three `swatches`
(`[name, fabric hex, label text hex]`).

## 5. Extend the component

The component draws a print image over the front only, by swapping out the whole fabric texture. It can't flip a
shirt, re-dye one without rebuilding the scene, or take your own controls in the detail view. Edit the installed files.
They're the reader's own local copy.

In `components/dimaac/clothes-rack/garment.ts`:

1. `GarmentSpec`: keep `image` but make it a transparent PNG the size of the whole front panel. Add `backImage`, the
   same for the back, as seen from behind.
2. Export `panelAspect(kind)`: run `boxFor` on that kind's pattern from `DRAPES` and return the box's width / height.
3. In the `garment` builder, delete the block that loads `spec.image` into the front material's map. Add a print
   layer instead: load the image with `THREE.TextureLoader` (sRGB, anisotropy 8), make a material with the existing
   `cloth` helper (white colour), set it transparent with alphaTest 0.02, polygon offset factor -1 and units -4, and
   give it the same `addFlow` call as the body panels (same flow uniforms and folds), so it bends with the cloth. Put
   it on a new mesh that reuses the panel geometry (the kind's `front`, or `back` for `backImage`), with renderOrder 1,
   and add it to `turn`. For the back, mirror the texture: repeat x -1, offset x 1. Push the texture and material
   onto the garment's dispose list and its `materials` list (so fades include them), skip everything if the garment
   is already gone, then call a new `onLoad` option. Add `onLoad?: () => void` to the builder's options and to
   `Wardrobe.garment`'s type.
4. Add `setColour(hex)` to the `Garment` type. In the builder, after the `materials` list is made, record every
   fabric material on `turn` (any with a map, plus the collar's material, never the hanger's) together with a copy of
   its colour. `setColour` sets each one to its recorded colour times new / original (per channel, in three's linear
   colour, floor the original at 0.004). Set its sheen colour to the new colour lerped toward white (0.1 if `lum` is
   under 0.12, else 0.3), and update the flow's `uAO` and `uInside` with the same thresholds the builder uses. The
   textures were painted in the original colour, so this re-dyes body, sleeves, collar and seams but not the prints.
5. In `setCloth`, the sleeves hang when the turn angle is far from facing. Measure that angle against the nearest of
   front (0) or back (PI), after wrapping it, so a shirt turned to show its back keeps its sleeves open.

In `components/dimaac/clothes-rack.tsx`:

6. Props: add `renderDetail?: (index) => ReactNode` and `controlRef?: { current: ClothesRackControl | null }`. Export
   `ClothesRackControl` with `flip(side: "front" | "back")` and `setColour(index, hex)`. Keep `controlRef` in a ref so
   the engine effect doesn't depend on it.
7. Dye state, right after `entries` in the engine effect: two arrays of `THREE.Color` per item (now and goal), both
   starting at the item's colour. Add a `stepDye(dt)` that eases each "now" toward its goal (factor 1 - exp(-dt / 0.09),
   snapping when close). It calls `setColour` on the rail garment in `entries`, on any detail garment of that index
   (shown or in `ready`), and sets `rackDirty`. Call it in `tick`, and keep the loop running while it's busy. Every
   newly built garment, on the rail (`buildSome`) or in the detail view (`makeDetailGarment`), gets its current dye
   at once. Pass `onLoad` to both: the rail's sets `rackDirty` and calls `wake`; the detail's calls `wake`.
8. Flip: give each `Shown` `flip`, `flipVelocity`, `flipGoal`, `lastFlipVelocity` (all 0) and its item `index`.
   `poseShown` adds `flip` to the turn's rotation. `stepStage` springs `flip` toward `flipGoal` with the same
   `spring` helper (time constant 0.6 s, 0.12 with reduced motion), counts it in its settled check, and adds the flip's
   change in velocity to the cloth's turn input, so the hem swings.
9. Where `engineRef.current` is set, fill `controlRef.current`. `flip` sets `flipGoal` (PI for back, 0 for front)
   on every shown garment that isn't leaving, then calls `wake`. `setColour` sets that index's dye goal, then calls
   `wake`. Null it in the effect's cleanup.
10. In the dialog, render `renderDetail(detailIndex)` in place of the caption block (counter, name, pill) when given.
   It sits inside the dialog, so `rack-ui.css` can use the `--half` the component already sets there.

## 6. The page

A client component reads `rack.json`. For each print it draws the cut-out PNG on a transparent canvas, 1536 px wide
and `1536 / panelAspect(kind)` tall, at its fractions, and passes the data URL as `image` / `backImage`. Build
all items before the first render: a changed `items` rebuilds the scene. Render `<ClothesRack items detail controlRef
renderDetail />` full screen. `renderDetail` returns a `.rack-tags` group (one `.rack-tag` button per swatch:
`--tag` = fabric, `--index` = position, label colour on its `span`, `aria-pressed` on the picked one, click calls
`setColour`). It also returns a `.rack-detail-info` block holding an `h3` name and a `.rack-sides` pair of FRONT / BACK
buttons (`aria-pressed`, click calls `flip`). Reset the side to front when the index changes.

## 7. Check, then hand back

- Run `npm run build`, then the dev server, and give them the local URL. Open every shirt, flip it, click every tag,
  and check both prints land where they should and aren't stretched or cut off. Nudge the numbers in `rack.json`
  until they do.
- Then offer to add the rest of their collection. Stop the dev server when you're done.
- Never deploy, publish, push to a public repo, or commit their photos without asking first.
