**English** | [Français](README.fr.md)

# Rétro-ingénierie boîtiers (camera reverse engineering)

**Give old digital cameras a second life: make a Nikon D40, D200, D750 or a Pentax 645D shoot film-look JPEGs straight out of the camera (Classic Chrome, Tri-X, Portra, Kodachrome, Hasselblad, Ricoh Positive), by modifying the firmware or loading custom looks over USB (Nikon Picture Control, Pentax Custom Image).**

Classic Chrome, Tri-X, HP5, Portra, Kodachrome, the Hasselblad look, the Ricoh Positive... Usually you have to buy the camera that has them, or run every photo through Lightroom. This repository shows how I recreated them in three old Nikons and a Pentax 645D, and gives the method to do the same on another camera:

- **Nikon D40** (2006): its firmware was mapped, emulated on the Mac, then modified. Five looks replace the Optimize Image presets, with a Pip-Boy style menu ([emulator screenshots](d40/README.md#le-menu-pip-boy)) and real exposure programs. This is **V5**, flashed and used on my own camera.
- **Nikon D200** (2005): same approach as the D40, with a firmware modified through data only. Five Optimize Image entries become Chrome, Positive, FP4, HP5 and Tri-X, with French menus; its 16-sector color stage was decoded by photographing a hue wheel. Flashed and validated on my own camera.
- **Nikon D750** (2014): the firmware is left alone. Nine Picture Controls are computed and loaded **over USB** into C-1 to C-9; the computer drives the camera during the test sessions (write a setting, trigger the shutter, fetch NEF and JPEG, measure).
- **Pentax 645D** (2010): medium format, firmware only read, never modified. Four looks (Classic Chrome, Portra 400, Tri-X, HP5) are loaded **over USB** into its Custom Image, through a manufacturer command nobody had driven before.

The principle is the same every time: measure the target look, measure what the camera can do, then compute the closest setting and check it on real photos. The measure is a perceived color difference, ΔE2000.

<img src="vues/comparaison/classic-chrome-4-appareils.jpg" width="800" alt="The same spring rocking horse photographed by four cameras set to Classic Chrome">

*Four cameras aiming at Classic Chrome: I dare you to tell which photo comes from which camera. Straight-out-of-camera JPEGs, exposure and white balance matched on the horse's gray to compensate for the sunny spells during the shoot.*

The repository is meant to be **handed to an AI** (Claude Code, Codex, Cursor...) with the instruction "reproduce this on my camera": see [`AGENTS.md`](AGENTS.md) and [`METHODE.md`](METHODE.md).

> Author: Thomas Hammoudi, photographer. Work done with Claude Code, in October 2026. The texts are in French.

## Download

- **D40, V5 ready to flash** (modified Nikon firmware, provided for convenience, no warranty; Nikon's rights reserved): [`d40-v5.zip`](https://github.com/ThomasHMD/retro-ingenierie-boitiers/releases/download/d40-v5/d40-v5.zip) (modified A 1.12 and B 1.11, checksums in `SHA256SUMS.txt`). Or rebuild it yourself from the official firmware: [`d40/README.md`](d40/README.md).
- **D200, firmware ready to flash** (same warning): [`d200-v2.zip`](https://github.com/ThomasHMD/retro-ingenierie-boitiers/releases/download/d200-v2/d200-v2.zip) (modified B 2.01, checksum in `SHA256SUMS.txt`). Or rebuild it from the official firmware: [`d200/README.md`](d200/README.md).
- **D750, the nine Picture Controls**: in the repository, [`d750/recettes/d750-v1/`](d750/recettes/d750-v1/README.md), to load over USB: [`d750/README.md`](d750/README.md).
- **645D, the four recipes**: [`645d/recettes/`](645d/recettes/recettes-645d.json), to load over USB: [`645d/README.md`](645d/README.md).

## What it does

A camera records two files for every shot: the RAW, what the sensor saw, and the JPEG, the image it builds from the RAW according to its color recipe (the Picture Control, at Nikon). For each look, I compute from the RAW what the photo would look like with the film or camera being imitated: this is the **target**. I then search for the Picture Control settings that bring the JPEG closest to it, send them to the camera over USB, photograph the same scene and compare the **straight-out-of-camera JPEG** with the target, zone by zone (ΔE: under 2, the difference is only visible side by side and to a trained eye; above 5, it is no longer quite the same look). A Picture Control changes all the colors at once, with no way to touch a single one: some looks are easier to imitate than others.

Below, the D750 on two scenes shot in October 2026, each look at its own white balance. These are demonstration JPEGs, framed identically in each row.

### The library

Daylight and 5,600 K LED, 28 mm. The starting image, the D750 JPEG in Standard, no recipe:

<img src="vues/bibliotheque/depart-standard.jpg" width="600" alt="starting point: D750 JPEG in Standard, library">

| Look | Target, computed from the RAW | Straight-out-of-camera JPEG |
|---|---|---|
| **Kodachrome**<br>6,250 K<br>ΔE 3.4<br><sub>film modeling powered by spektrafilm</sub> | <img src="vues/bibliotheque/cible-kodachrome.jpg" width="300" alt="Kodachrome target"> | <img src="vues/bibliotheque/boitier-kodachrome.jpg" width="300" alt="camera JPEG, Kodachrome"> |
| **Classic Chrome**<br>5,600 K<br>ΔE 1.8 | <img src="vues/bibliotheque/cible-classic-chrome.jpg" width="300" alt="Classic Chrome target"> | <img src="vues/bibliotheque/boitier-classic-chrome.jpg" width="300" alt="camera JPEG, Classic Chrome"> |
| **Classic Neg**<br>5,600 K<br>ΔE 5.1 | <img src="vues/bibliotheque/cible-classic-neg.jpg" width="300" alt="Classic Neg target"> | <img src="vues/bibliotheque/boitier-classic-neg.jpg" width="300" alt="camera JPEG, Classic Neg"> |
| **Positive**<br>5,600 K<br>ΔE 2.9 | <img src="vues/bibliotheque/cible-positive.jpg" width="300" alt="Positive target"> | <img src="vues/bibliotheque/boitier-positive.jpg" width="300" alt="camera JPEG, Positive"> |
| **Portra 400**<br>5,600 K<br>ΔE 4.6<br><sub>based on a preset I bought and liked a lot</sub> | <img src="vues/bibliotheque/cible-portra-400.jpg" width="300" alt="Portra 400 target"> | <img src="vues/bibliotheque/boitier-portra-400.jpg" width="300" alt="camera JPEG, Portra 400"> |
| **Hasselblad**<br>5,600 K<br>ΔE 2.5 | <img src="vues/bibliotheque/cible-hasselblad.jpg" width="300" alt="Hasselblad target"> | <img src="vues/bibliotheque/boitier-hasselblad.jpg" width="300" alt="camera JPEG, Hasselblad"> |
| **Tri-X**<br>10,000 K<br>ΔE 1.2<br><sub>based on a preset I bought and liked a lot</sub> | <img src="vues/bibliotheque/cible-tri-x.jpg" width="300" alt="Tri-X target"> | <img src="vues/bibliotheque/boitier-tri-x.jpg" width="300" alt="camera JPEG, Tri-X"> |
| **HP5+**<br>5,600 K<br>ΔE 3.2 | <img src="vues/bibliotheque/cible-hp5.jpg" width="300" alt="HP5+ target"> | <img src="vues/bibliotheque/boitier-hp5.jpg" width="300" alt="camera JPEG, HP5+"> |
| **FP4+**<br>5,600 K<br>ΔE 2.6 | <img src="vues/bibliotheque/cible-fp4.jpg" width="300" alt="FP4+ target"> | <img src="vues/bibliotheque/boitier-fp4.jpg" width="300" alt="camera JPEG, FP4+"> |

### The view from the window

Building and sky, 50 mm on a tripod, exposure set on the sky. The first outdoor shots, handheld with auto white balance, gave a strange sky: up to ΔE 10 for Kodachrome. Redone by the book, each Picture Control at the white balance it was computed for, the scene holds up (Kodachrome at 4.1, black and white around 1), and the calculation predicts the camera JPEG to within 0.4 to 1.4, even in the sky. The strange sky came from the auto white balance, not from the recipes. Starting point:

<img src="vues/fenetre/depart-standard.jpg" width="300" alt="starting point: D750 JPEG in Standard, view from the window">

| Look | Target, computed from the RAW | Straight-out-of-camera JPEG |
|---|---|---|
| **Kodachrome**<br>6,250 K<br>ΔE 4.1<br><sub>film modeling powered by spektrafilm</sub> | <img src="vues/fenetre/cible-kodachrome.jpg" width="220" alt="Kodachrome target"> | <img src="vues/fenetre/boitier-kodachrome.jpg" width="220" alt="camera JPEG, Kodachrome"> |
| **Classic Chrome**<br>5,600 K<br>ΔE 3.4 | <img src="vues/fenetre/cible-classic-chrome.jpg" width="220" alt="Classic Chrome target"> | <img src="vues/fenetre/boitier-classic-chrome.jpg" width="220" alt="camera JPEG, Classic Chrome"> |
| **Classic Neg**<br>5,600 K<br>ΔE 6.3 | <img src="vues/fenetre/cible-classic-neg.jpg" width="220" alt="Classic Neg target"> | <img src="vues/fenetre/boitier-classic-neg.jpg" width="220" alt="camera JPEG, Classic Neg"> |
| **Positive**<br>5,600 K<br>ΔE 2.1 | <img src="vues/fenetre/cible-positive.jpg" width="220" alt="Positive target"> | <img src="vues/fenetre/boitier-positive.jpg" width="220" alt="camera JPEG, Positive"> |
| **Portra 400**<br>5,600 K<br>ΔE 3.0<br><sub>based on a preset I bought and liked a lot</sub> | <img src="vues/fenetre/cible-portra-400.jpg" width="220" alt="Portra 400 target"> | <img src="vues/fenetre/boitier-portra-400.jpg" width="220" alt="camera JPEG, Portra 400"> |
| **Hasselblad**<br>5,600 K<br>ΔE 3.1 | <img src="vues/fenetre/cible-hasselblad.jpg" width="220" alt="Hasselblad target"> | <img src="vues/fenetre/boitier-hasselblad.jpg" width="220" alt="camera JPEG, Hasselblad"> |
| **Tri-X**<br>10,000 K<br>ΔE 1.1<br><sub>based on a preset I bought and liked a lot</sub> | <img src="vues/fenetre/cible-tri-x.jpg" width="220" alt="Tri-X target"> | <img src="vues/fenetre/boitier-tri-x.jpg" width="220" alt="camera JPEG, Tri-X"> |
| **HP5+**<br>5,600 K<br>ΔE 1.0 | <img src="vues/fenetre/cible-hp5.jpg" width="220" alt="HP5+ target"> | <img src="vues/fenetre/boitier-hp5.jpg" width="220" alt="camera JPEG, HP5+"> |
| **FP4+**<br>5,600 K<br>ΔE 1.2 | <img src="vues/fenetre/cible-fp4.jpg" width="220" alt="FP4+ target"> | <img src="vues/fenetre/boitier-fp4.jpg" width="220" alt="camera JPEG, FP4+"> |

> **White balance is part of the recipe: always in Kelvin, never Auto.** Kodachrome **6,250 K**, Tri-X **10,000 K** (in black and white too: the white balance changes how colors mix into gray), all the others **5,600 K**. In Auto, the camera shifts the colors on every shot and the look no longer resembles its target.

Full figures (p90, predicted against measured, mixed light): [`d750/recherche/resultats-mesures.md`](d750/recherche/resultats-mesures.md); to redo the images: `d750/outils/figures_page_blog.py`.

### The Nikon D200, in simulation

Simulation: my D200 RAW photos, run through the tables of the modified firmware. This calculation lands back on the camera's JPEG, down to the measurement floor ([`d200/README.md`](d200/README.md)). The hue wheel shows the gap between Chrome and Positive best.

| Normal (Nikon, stock) | Chrome | Positive |
|---|---|---|
| <img src="vues/d200/normal-interieur.jpg" width="250" alt="D200, normal interior, simulation"> | <img src="vues/d200/chrome-interieur.jpg" width="250" alt="D200, chrome interior, simulation"> | <img src="vues/d200/positive-interieur.jpg" width="250" alt="D200, positive interior, simulation"> |
| <img src="vues/d200/normal-roue.jpg" width="250" alt="D200, normal wheel, simulation"> | <img src="vues/d200/chrome-roue.jpg" width="250" alt="D200, chrome wheel, simulation"> | <img src="vues/d200/positive-roue.jpg" width="250" alt="D200, positive wheel, simulation"> |

| Black and white (Nikon, stock) | Tri-X: hard paper | HP5: soft paper, matte blacks | FP4: medium contrast |
|---|---|---|---|
| <img src="vues/d200/nb-nikon-interieur.jpg" width="190" alt="D200, Nikon black and white interior, simulation"> | <img src="vues/d200/tri-x-interieur.jpg" width="190" alt="D200, Tri-X interior, simulation"> | <img src="vues/d200/hp5-interieur.jpg" width="190" alt="D200, HP5 interior, simulation"> | <img src="vues/d200/fp4-interieur.jpg" width="190" alt="D200, FP4 interior, simulation"> |

### The Pentax 645D, on the crankset

Same scene on a tripod (45 mm, Auto white balance), only the Custom Image changes from one shot to the next. The 645D stores in every PEF a full-size JPEG rendered with its settings: these are those JPEGs, scaled down. The color differences are measured against the D750 targets; in black and white, against the film curves.

| Look | Menu settings | Straight-out-of-camera JPEG |
|---|---|---|
| **Classic Chrome**<br>ΔE 1.9 | Natural, hue −2 | <img src="vues/pedalier/boitier-classic-chrome.jpg" width="300" alt="645D, Classic Chrome"> |
| **Portra 400**<br>ΔE 2.3<br><sub>based on a preset I bought and liked a lot</sub> | Bright, everything at 0; expose −⅓ to −½ EV (ΔE against the preset alone) | <img src="vues/pedalier/boitier-portra-400.jpg" width="300" alt="645D, Portra 400"> |
| **Tri-X 400**<br>gap 6.7 → 4.2 | Recipe: Monochrome, filter none, contrast +3. Shot: contrast +2 (only +2 and +4 were photographed) | <img src="vues/pedalier/boitier-tri-x-400.jpg" width="300" alt="645D, Tri-X 400, contrast +2"> |
| **HP5 Plus**<br>gap 9.8 → 3.3 | Recipe: Monochrome, cyan filter, contrast +4. Shot: cyan filter, contrast 0 | <img src="vues/pedalier/boitier-hp5-plus.jpg" width="300" alt="645D, HP5 Plus, cyan filter"> |

In black and white, the flaw of the stock Monochrome is its curve, which is too flat: the gap to the film, in gray levels out of 255, goes from 6.7 to 4.2 for Tri-X and from 9.8 to 3.3 for HP5 between contrast 0 and +4; the cyan filter brings HP5 closer. White balance, for its part, cannot be set over USB on this camera. Details: [`645d/README.md`](645d/README.md); to redo the images: `645d/outils/645d_vues_demo.py`.

## What is provided

| | Content |
|---|---|
| [`METHODE.md`](METHODE.md) | The general method, from one camera to another: choose the targets, measure, model the camera, compute, check in a loop of test shots |
| [`AGENTS.md`](AGENTS.md) ([`CLAUDE.md`](CLAUDE.md)) | The instructions for an AI: "reproduce this on your camera", with the safeguards |
| [`d40/`](d40/README.md) | How we did it (firmware map, emulator, color-table patches), `patch.py` and the patches, `fabriquer_v5.py`, which rebuilds V5 from Nikon's official firmware, the flashing procedure and its limits |
| [`d200/`](d200/README.md) | The simulator and the rendering-table patches, the decoded 16-sector color stage, the image-engine emulator, V2 to rebuild from the official firmware, the flashing and rollback procedure |
| [`d750/`](d750/README.md) | The USB control tools (read, write, erase a Picture Control; automatic test sessions), the analysis and measurement scripts, the nine loaded recipes (`.json` and blocks), the procedure (sessions, white balance, presets d-1 to d-6) |
| [`645d/`](645d/README.md) | USB control of the Custom Image (manufacturer handshake, write, trigger, fetch), measurement of filters and curves, the four recipes and their loading plans, the firmware reading tools |
| Releases [`d40-v5`](https://github.com/ThomasHMD/retro-ingenierie-boitiers/releases) and `d200-v2` | The files of D40 V5 (modified A 1.12 and B 1.11) and D200 V2 (modified B 2.01), ready to flash, for those who do not want to build them |

## The looks

| Look | D40 (V5, preset) | D750 (Picture Control) | Target |
|---|---|---|---|
| Kodachrome | | C-1, at 6,250 K | spectral simulation of Kodachrome 64 (spektrafilm), chroma × 1.2 |
| Classic Chrome | Vivid | C-2 | JPEG from a Fujifilm X-T4 (D40), official Fujifilm LUT (D750) |
| Classic Neg | | C-3 | official Fujifilm LUT |
| Positive | More Vivid | C-4 | RAW + JPEG pairs from a Ricoh GR III |
| Portra 400 | | C-5 | "Portra spirit": between my Portra 400 scans and a preset I bought and liked a lot |
| Hasselblad | Soft | C-6 | RAW + JPEG pairs from a Hasselblad X2D (HNCS) |
| Tri-X | Portrait | C-7, at 10,000 K | based on a preset I bought and liked a lot, checked against the Kodak datasheet |
| HP5+ | Black And White | C-8 | Ilford datasheet (spectral sensitivity, grade 2 print) |
| FP4+ | | C-9 | Ilford datasheet |

The targets are looks I like, not truths: an HP5 changes with the scan, the development and the processing. The method lets you aim at your own.

## Measured gaps

ΔE2000 between the straight-out-of-camera JPEG and the look's target, on the uniform zones of the image (the scene being read from the NEF of the same photo). **Median**: the gap of the typical zone; **p90**: that of the 10% most difficult zones. Landmarks: under 2, only visible side by side to a trained eye; 2 to 3, visible side by side; above 5, it is no longer quite the same look.

| Look | Camera | Median | p90 | Views measured |
|---|---|---|---|---|
| Classic Chrome | D40 | 1.4 | 2.7 | 1 (X-T4 target; 3.6 against the Fujifilm LUT) |
| Positive | D40 | 1.6 | 2.8 | 3 |
| Hasselblad | D40 | 2.7 | 3.8 | 1 |
| Tri-X | D40 | 0.5 | 2.8 | 4 |
| HP5+ | D40 | 2.7 | 4.6 | 11 |
| Kodachrome | D750 | 3.4 | 6.2 | 1 scene (spektrafilm Kodachrome 64 target, at 6,250 K) |
| Classic Chrome | D750 | 1.8 | 3.0 | 1 scene (target: Fujifilm LUT) |
| Classic Neg | D750 | 5.1 | 6.9 | 1 scene (target: Fujifilm LUT) |
| Positive | D750 | 2.9 | 4.8 | 1 scene |
| Portra 400 | D750 | 4.6 | 6.3 | 1 scene (target: "Portra spirit", the tuned Portra preset) |
| Hasselblad | D750 | 2.5 | 4.0 | 1 scene |
| Tri-X | D750 | 1.2 | 1.7 | 1 scene (Tri-X v2, at 10,000 K) |
| HP5+ | D750 | 3.2 | 6.7 | 1 scene |
| FP4+ | D750 | 2.6 | 7.4 | 1 scene |

**Of the 14 looks measured, 10 have a median under 3, and none exceeds 5.1.** On the D750, these are the nine Picture Controls as they sit in the camera (Tri-X v2 included), photographed in October 2026 on one scene, a library, under a single light (daylight and 5,600 K LED), and measured on the same 4,675 zones for all the looks. The camera does what the model predicts (model against JPEG: 0.9 to 1.9, Portra 2.5): the remaining gaps come from the recipes and the format. Under mixed light (daylight and warm lamp), HP5 and FP4 rise to 5.2 and 5.4. A second scene, the view through a window (building and sky, on a tripod), gives from 1.0 (HP5+) to 6.3 (Classic Neg): images above, "What it does". The 645D (Classic Chrome 1.9, Portra 2.3, on a weakly colored crankset) is a case apart: [`645d/README.md`](645d/README.md). The D40 figures apply to the published V5 (same tables as the photographed version, verified to the byte).

Caveats, to keep in mind:
- few views: one to eleven per look on the D40, two scenes on the D750, a library (the table figures) and the view through a window (Classic Neg and Portra depend heavily on the scene content, HP5 and FP4 on the light);
- the "target" is the reference look chosen for each look; for Classic Chrome, the X-T4 JPEG and Fujifilm's LUT are themselves 3.9 apart;
- only uniform zones count: no texture, no sharpness, no grain;
- p90 follows the most vivid colors: on the D750, it goes from 1.7 (Tri-X) to 7.4 (FP4).

What does not come down, and why: a D750 Picture Control only has global settings (one base, one gain and one color rotation for all hues at once, one curve on the luminance). It cannot change one color without touching the others: Classic Neg, Positive and Portra hit that wall. The D40, for its part, has matrices, curves and a hue-sector correction in its firmware: its remaining gaps are settings, and can be corrected. Details: [`d750/recherche/resultats-mesures.md`](d750/recherche/resultats-mesures.md).

## Getting started

- **I have a D40**: [`d40/README.md`](d40/README.md). Download the two official firmwares from Nikon, `python3 d40/fabriquer_v5.py <A 1.12> <B 1.11>`, check the checksums, flash A then B. Or take the files from the release.
- **I have a D200**: [`d200/README.md`](d200/README.md). Download the 2.01 update from Nikon, `python3 d40/patch.py d200/patchs/d200-v2.json`, check the checksum, prepare a rollback card, flash B. Or take the file from the release.
- **I have a D750**: [`d750/README.md`](d750/README.md). The nine recipes load over USB from a Mac (`picture_control.py bloc` then `d750_ecrire.swift`, simulation by default).
- **I have a 645D**: [`645d/README.md`](645d/README.md). The four recipes load over USB from a Mac (`645d_seance.swift`, state saved beforehand, restored on request).
- **I have another camera**: give this repository to your AI with [`AGENTS.md`](AGENTS.md). Most recent cameras have an equivalent of the Picture Control (Fujifilm recipes, Pentax Custom Image, Ricoh Image Control...); some old cameras have a firmware open to study, like the D40.

Requirements: Python 3.10 or later (`pip install -r requirements.txt`); for the D750, a Mac (the USB tools are in Swift, with ImageCaptureCore); for the D40 emulator, a JDK 17 or later and `git`.

## Legal notes

- **The git repository contains no byte of Nikon's firmware.** Everyone downloads the official firmware from Nikon, and the patch applies to it. The D40 and D200 patches do not contain the original bytes, only their sha256 checksum (to verify you start from the right file) and our replacements; some replacements do, however, reuse, modified, elements from Nikon: the French menu and help tables, rebuilt elsewhere in the file with our texts added (about 32 KB), a character sheet copied with 13 glyphs added to the original 21, and the headers of the info-screen background JPEG (replaced by a black background). The file `d40/recettes/v1/nikon.json` (copied into `d750/recettes/v1/`) contains the decoded factory color tables of the D40 (6 matrices, one curve, the sectors), which serve as the reference for the calculations: this is Nikon data, kept because the calculations need it, and Nikon's rights on these tables remain with Nikon too. The decompiled pseudo-code is not published: `d40/desassemblage/regenerer.sh` rebuilds it locally.
- **The releases also offer, for convenience, D40 V5 and the D200 firmware already patched**, for cameras nearly twenty years old, with no warranty whatsoever. This is modified Nikon firmware: Nikon's rights on this file remain with Nikon.
- **The looks are analyzed, then carried over to other cameras, without reusing the manufacturers' code.** No third-party table, LUT or profile is redistributed (Fujifilm LUT, Lightroom presets, spektrafilm tables): they are measured, and I publish the setting computed for another camera. For Tri-X and Portra, the target is a preset I bought and liked a lot ("the Tri-X preset", "the Portra preset" in the notes): its look is imitated for a very specific use, the straight-out-of-camera JPEG; no file or code from this preset is redistributed. Where to find each source, and under which license: [`LICENCES-TIERS.md`](LICENCES-TIERS.md).
- **The D750 is never modified**: the Picture Controls are written through the USB command Nikon provides for its own software, into the user's slots.
- Flashing a modified firmware is done **at your own risk**: it can render a camera unusable, and it probably voids the warranty (a D40 has long been out of warranty). Read [`d40/README.md`](d40/README.md) or [`d200/README.md`](d200/README.md) first.

## License

My work (texts, tools, recipes, patches) is under **[CC BY-NC-SA 4.0](LICENSE)**: you may reuse and modify it by crediting the author, without commercial use, and by sharing your versions under the same terms. Exceptions, which keep the license of their origin: the D40 emulator (`d40/emulateur/java/` and the disassembler configuration), built on nikon-firmware-tools, is under GPL-3.0; a Ghidra script taken from ghidra-fr60 is under Apache 2.0. Details: [`LICENCES-TIERS.md`](LICENCES-TIERS.md).

The photos (the views in `vues/` and the repository's preview image) are not under this license: © Thomas Hammoudi, all rights reserved. The D40 emulator screenshots and the analyses (measurements, tables, curves) remain under CC BY-NC-SA 4.0.

Nikon, D40, D750, Picture Control, Fujifilm, Classic Chrome, Kodak, Kodachrome, Tri-X, Portra, Ilford, HP5, FP4, Hasselblad and Ricoh are trademarks of their respective owners. This project is not affiliated with any of them.
