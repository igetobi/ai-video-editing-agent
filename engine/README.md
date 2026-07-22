# engine/ — the HyperFrames boundary

This is where the pipeline meets the [HyperFrames](https://github.com/heygen-com/hyperframes)
video engine. Two small modules and one config file:

- **`composition.py`** — turns a `plan.json` beat into HyperFrames-native HTML (a
  `#stage` with `data-*` timing attributes and a `.clip`). Animations are seek-safe CSS
  keyframes. Compositions render on a transparent background so each beat is an alpha
  overlay.
- **`hyperframes_adapter.py`** — renders a composition to a clip by shelling out to the
  HyperFrames CLI.
- **`engine.json`** — the render invocation. **This is the one place to adjust for your
  installed HyperFrames version.** Verify flags with `npx hyperframes render --help`.

## Rules

1. **Never hand-edit a generated composition.** They live in
   `projects/<job>/graphics/compositions/` and are rebuilt from `plan.json`. Change the
   plan, rebuild.
2. **Never hand-edit engine internals.** The engine + agent skills are pinned in
   `../skills-lock.json`. Update with `npm run engine:install`.
3. If a render flag is wrong for your version, fix it **in `engine.json`**, not in code.

## Install / update

```bash
npm install                 # hyperframes package (../package.json)
npm run engine:install      # npx skills add heygen-com/hyperframes --full-depth
npm run engine:preview      # live preview a composition while iterating
npm run engine:lint         # validate composition structure
```

## Why HyperFrames

It renders plain HTML/CSS to deterministic MP4 by seeking frame-by-frame in headless
Chrome. LLMs write HTML fluently, so an agent can author rich, on-brand motion
graphics without a proprietary timeline format — which is exactly what stage 3 needs.
