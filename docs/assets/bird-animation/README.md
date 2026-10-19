# Four-region bird path

A single bird travels continuously from left to right through four visible areas:

1. Normal / dry → CanFly true → flying.
2. Puddle / wet → CanFly false → walking.
3. Normal / dry conditions restored → CanFly true → flying.
4. Rain / wet → CanFly false → walking.

The animation loops automatically. There are no buttons, reference-label panels,
or explanatory captions. Only the landscape and animation are shown; region names are not displayed.
Reduced-motion settings display a static scene. Hidden tabs suspend animation.

| File | Edit to change |
| --- | --- |
| `component.html` | Four region layout, ground/puddle/weather art |
| `scene.svg` | Bird body, wings, separately animated legs |
| `scenes.json` | Per-region reference context, label, and explanation |
| `animation.css` | Flight height, ground height, walking/wing/rain motion, colors |
| `animation.js` | Horizontal motion, active region, loop timing (`cycleMs=24000`) |

The same v1 entity, bird_010, is retained throughout. Dry/wet labels correspond
to its dry_20m=true and wet_20m=false references. Puddles and walking are visual
metaphors, not additional dataset annotations. Each region independently applies
its context: the second normal region explicitly restores dry conditions. This
is not a physical simulation of drying or a temporal experiment.

CSS is scoped to `.bird-demo-section`. Asset loading resolves relative to the JS
file, including under the `/CDR-Dataset/` prefix. Use `bash shells/serve.sh` for
local HTTP preview. Small screens can scroll the landscape horizontally.

Wet regions apply `.is-wet`: the SVG shows a darker, clumped wing with sheen and
three dripping water drops. The same class is cleared in dry regions. Edit
`.bird-wet-*` / `.bird-water-drop` in the SVG/CSS to adjust this effect.

The puddle contains an illustrative fish. The bird stops briefly, dips toward the
fish, triggers a splash, and continues walking with wet wings. The fish resets
on each loop. It is scene artwork, not a claim about hummingbird diet or a v1
feature. Adjust `feedingMs`, `feedingX`, and the feeding CSS to edit this beat.

The fish sits 20% into the puddle region (30% of the full landscape). Feeding
lasts 650 ms; the fish disappears after 180 ms. The beak alignment uses the
landscape width so the approach stays near the puddle entrance on mobile too.

The puddle SVG crops its empty margins and fills 145% of its region width,
extending 40% of a region width leftward into the first Normal area. Wet plumage starts with the splash at 180 ms
after the bird stops, allowing the descent/dip to reach the water first.

Rain uses independently animated short SVG strokes with staggered negative delays
and slightly different durations. Drops fade before resetting, avoiding a jumping
grid. In reduced-motion mode their fallback positions remain scattered.

### Synchronized narration

Each region’s `caption` in `scenes.json` supplies the text below the landscape.
`animation.js` updates it from the same elapsed-time position as the bird; the
puddle sentence starts when the bird touches the water. Alice is the name used
for this illustrative animation, not a replacement for the dataset entity name.
The caption has a reserved space outside the illustration and follows reduced-motion preferences.
