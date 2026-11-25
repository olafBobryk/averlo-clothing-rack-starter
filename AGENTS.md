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

1. Create a Next.js app with TypeScript (or use theirs if they already have one): `npx create-next-app@latest`.
2. Install the free Clothes Rack component from DiMaac UI: `npx shadcn@latest add @dimaac/clothes-rack`
   (fallback: `npx shadcn@latest add https://ui.dimaac.com/r/clothes-rack.json`). It installs its files and `three`.
   Its licence lets them use it in their own and client projects; don't copy its source into this repo or any public one.
3. Render `<ClothesRack items={...} detail />` on the home page, full screen, white background.

## 3. Fill it in

1. For every photo, cut the print out onto a transparent PNG (crop to the print, remove the shirt and background) and
   save it as `public/prints/<shirt-name>-front.png` / `-back.png`. Do it locally. If the photos need AI cleanup
   (for example with Higgsfield), quote the credits and wait for a yes before generating anything.
2. Copy [rack-starter.json](rack-starter.json) to `rack.json` and add one entry per shirt: `name`, `kind` (`tee`),
   `colour` (the fabric colour sampled from the photo), `prints.front` / `prints.back` (`[file, x, y, width, height]`,
   fractions of the shirt panel, so `0.2, 0.25, 0.6, 0.3` is a centred chest print), and three `swatches`
   (`[name, fabric hex, label text hex]`).
3. Map each entry to a `ClothesRackItem`: `name`, `kind`, `colour`, and `image` for the front print.
4. Add the two controls the component doesn't have, styled with [rack-ui.css](rack-ui.css):
   - a FRONT / BACK toggle under the open shirt that turns it 180 degrees and shows the back print (mirror the back
     panel so it reads correctly);
   - three hanging colour tags beside the open shirt that fade the fabric to that swatch.

## 4. Check, then hand back

- Run the dev server and give them the local URL. Open every shirt, flip it, and check both prints land where they
  should and aren't stretched or cut off. Nudge the numbers in `rack.json` until they do.
- Then offer to add the rest of their collection.
- Never deploy, publish, push to a public repo, or commit their photos without asking first.
