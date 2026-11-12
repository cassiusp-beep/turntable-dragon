# Turntable dragon (the new build)

Your printed dragon curls on a spinning platter. The platter has a gear ring **on the inside** underneath, and the motor's little gear drives it. Scream and it spins faster.

```
XX_2_3D_PRINT/   (Bambu: open, keep positions, no supports, 15% infill, brim on)
    XX_ONE_PLATE_turntable_dragon_all_parts.3mf   -> EVERYTHING on one 256 plate:
        150 mm platter with ring gear (prints upside down), compact base with centre post,
        3 legs, motor carriage, 4 motor gears                                    ~3-4 h total
    XX_EGGS_30_small_dragon_eggs.3mf               -> 30 little eggs (10/12/14 mm wide; scales, spiral, studs). No supports, flat bottoms. ~1-1.5 h
XX_3_CODE/
    dragon_motor/dragon_motor.ino            -> same Uno code as before (no changes needed)
    scream_dragon.py                         -> same scream detector
```
**Running the code:** use the old folder, because its Python setup (`.venv`) is there:
`cd "…/Nov 9/Dragon_Automaton_Files/XX_3_CODE"` then `.venv/bin/python scream_dragon.py`

## The motor gears (pick 1 of the 4)
| Gear | Turntable speed | Dimples on top | Bore |
|---|---|---|---|
| 28 teeth (big) | faster: 1 platter turn per 2.9 motor turns | 1 = tight, 2 = loose | dual-D for the 5 mm shaft, 4 mm flats |
| 17 teeth (small) | slower: 1 platter turn per 4.7 motor turns | 1 = tight, 2 = loose | same |

- **Start with the 28-tooth gear**, because the Mini-300 motor is already slow (about 5–20 rpm).
- **Use the snuggest one that slides onto the shaft.** The two flats turn the gear, so **no glue is needed**. With the shaft pointing up, the gear just sits on the motor's collar.
- **If it wiggles, you have two no-glue options:**
  - **A screw down the middle.** The top has a 3.2 mm hole and a recess for the head. If your shaft has a threaded hole in its end, screw in from the top.
  - **A set screw from the side.** There's a 2.6 mm hole between two teeth. An M3 grub screw self-taps into it and presses on a flat. A grub screw has no head, so it won't hit the ring.

## Assembly
1. **Legs:** push the 3 leg pegs up into the holes under the base. 3 legs never rock. It's a snug fit; add a dot of tacky glue if one is loose.
2. **Motor:**
   - Drop the motor into the carriage tube, shaft up and can down.
   - Rest its two ears on the rim, between the little prongs. The prongs stop it twisting.
   - Feed the wires down through the hole in the floor.
3. **Carriage:**
   - Set it between the two rails on the deck, with the wires going down through the deck slot.
   - Slide it until its **outer edge lines up with a groove** on the rails: the **inner groove for the 28-tooth gear**, the **outer groove for the 17-tooth gear**.
4. **Gear:** slide your chosen gear onto the shaft.
5. **Platter:**
   - Lower it onto the centre post, with the gear ring facing down.
   - Turn it slowly by hand while sliding the carriage a hair in or out, until the teeth mesh with a tiny bit of play.
   - Then put a few dots of CA or tacky glue under the carriage edge to lock it.
6. **Dragon:**
   - Curl it on top along the thin guide circle, chasing its tail. The ring is about 380 mm around, which matches the dragon's length.
   - Use **tacky glue** if you want to be able to peel it off later, or CA for permanent.
7. **Electronics:**
   - Lay the Uno and H-bridge on the table under the deck, between the legs.
   - Wire them the same as before: D9 to ENA, D7 to IN1, D8 to IN2, GND to GND, OUT1 and OUT2 to the motor, and power from the Uno's 5V (or the adapter).
   - The USB cable goes out between two legs.

## Tolerances built in
- **Gears:** 0.6 mm of total tooth play. The groove marks sit 0.15 mm closer to the centre, which opens up an inner ring gear.
  - Rhino check, at both gear sizes: the teeth never touch through the turn.
  - Smallest gap 0.33 mm at the marks. Still clear if the carriage sits 0.35 mm off in either direction (0.17 mm at worst).
- **Post:** 16.0 mm post in a 16.8 mm hub. The platter rides on a rounded tip, a single point, so friction is low.
- **Motor tube:** 32.6 mm for the 32 mm gearbox.
- **Rails:** the carriage has 0.3 mm of side play between them.
- **Legs:** 8.0 mm pegs in 8.4 mm holes.
- **Size:** the platter is 150 mm across and the gear teeth are module 1.5. Your dragon's curl, about 120 mm across, fits right on it.
- **Vertical:**
  - The ring teeth are 12.5 mm tall for a 9 mm gear, so the gear still meshes if the motor sits a couple of mm higher or lower than expected.
  - 2.5 mm between the gearbox top and the ring.
  - 4.5 mm between the top of the gear and the platter.
- **Assumption:** the motor's ears are at the shaft end of the gearbox. If they aren't, tell me before printing C and I'll change the tube height.

_The dragon is D3Craft's Flexi Dragon: personal use only, don't share it._

## Dragon eggs
- 30 small eggs in 3 textures (scales, spiral ridges and studs) and 3 sizes (10, 12 and 14 mm wide).
- Each has a flat bottom, so it prints standing up with no supports and sits flat on the platter.
- **Printing:** use a brim; they're small. 15% infill or more. **Use a 0.12–0.16 mm layer height** so the textures show.
- **On the platter:** scatter them inside the dragon's curl and around it. Add a dot of tacky glue under each, so they stay put while it spins and you can still peel them off.
