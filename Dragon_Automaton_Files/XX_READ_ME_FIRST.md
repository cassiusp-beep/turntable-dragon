# Dragon automaton files

**Only use files that start with XX.** Ignore everything in `IGNORE_backup_files`.

```
XX_1_LASER_CUT/
    XX_A_plywood_box_finger_joints_30x18in_HORIZONTAL.ai -> 1/8" plywood, 30" wide x 18" tall (all 12 box pieces)
    XX_B_acrylic_front_window_32x16in_HORIZONTAL.ai      -> 1/16" clear acrylic, 32" x 16" (optional window)

XX_2_3D_PRINT/
    DONE_1_dragon_125pct_PERSONAL_USE.stl    -> printed
    DONE_2_mechanism_plate.3mf               -> printed (its rods + pins are replaced by XX_6)
    XX_3_wings_and_mounts_plate.3mf          -> printing now
    XX_4_head_cams_plate.3mf                 -> snail + R4 cams, head rod + foot, sleeve   ~1.5-2 h  (fixed hole)
    XX_5_shafts_set_100pct_INFILL.3mf        -> the 2 shaft pieces: 100% infill            ~1 h  (long piece now 231.6 mm)
    XX_6_REPRINT_rods_and_pins_fix.3mf       -> 4 body rods, wing T, 12 hinge pins         ~1-1.5 h
    XX_7_motor_bracket_cover_couplers.3mf    -> motor bracket, cover, 4 couplers           ~3-4 h
    XX_8_rod_guide_bar_PRINTED_diagonal.3mf  -> one-piece printed guide bar (replaces the laser-cut one)  ~2 h
XX_3_CODE/
    XX_HOW_TO_RUN.md                         -> upload the Arduino code, run the scream detector
    dragon_motor/dragon_motor.ino            -> Uno code (set SUPPLY_V first)
    scream_dragon.py                         -> camera + mic scream detector (Mac)
```

## Laser cutting
- Open the **.ai** files in Illustrator. Each artboard is the full sheet, **horizontal**, at true size. Don't scale.
- **Red lines = vector cut**: RGB red, 0.001 pt hairline.
- **Blue text = labels.** Raster-engrave them lightly or delete them.
- The box has **finger joints**: floor, back, both end walls and top plate all interlock. The fingers are drawn 0.075 mm wider each side, so after the laser's cut width they fit snugly with glue.
- **Pieces cut twice (labelled 1/2 and 2/2):** top plate, both end walls, guide bar and A-frame. Glue each pair face to face first, with the fingers and holes lined up, so it's 1/4" thick. Push a printed rod through the holes while the glue sets.
- The floor and back panel are one layer.
- The fingers assume 1/8" (3.18 mm) plywood. If your sheet runs a little thin or thick, the fingers will sit a hair proud or recessed. Sand them flush after gluing.

## Box assembly (wood glue in the fingers)
1. Glue the doubled pairs (top, end walls, guide bar, A-frame). Let them dry flat under a weight.
2. Glue the end walls and the back panel into the floor's fingers. Check it's square.
3. Glue the printed guide blocks inside the end walls, with their tops **95 mm above the bottom of the box**.
4. Slide the shaft in through the end walls. Stand the A-frame on the floor with the shaft through its hole, 137 mm from the outside of the left (motor) end wall, then glue it.
5. Rest the guide bar on the blocks. Line its holes up with the top plate using a rod, then glue it.
6. Top plate last: its fingers drop into the end walls and back. Glue it, or leave it dry so you can lift it off.
7. Clear acrylic window: glue or double-sided tape it inside the open front.

## 3D printing (Bambu Studio)
- Open each file and print it. If Bambu asks whether to keep the file's positions, say **yes**.
- No supports. Don't rotate anything. Brim on. Leave X-Y hole compensation at 0.
- **XX_5 (shafts): 100% infill** for the whole plate. Use normal infill (15–20%) on everything else.
- On the wings plate, each wing has two parts (membrane and bones). Give them two colours, or leave them both one colour.

**If a fit is off:** a tight cam on the shaft or rod in a foot gets a little sanding. A loose one gets a drop of CA glue.

## Head foot fix (jam found Nov 11)
- **The head stick's foot jams against the right guide block.** It's 4 mm too wide on the wall side. Cut or sand **5 mm off the foot's side that faces the right wall** so it stops short of the block. It still covers the whole snail cam.
- At the top of its lift, the head foot also rises 2 mm into the bottom of a flat guide bar. **XX_8 now has a pocket under the head hole for it** (1.5 mm clearance). With the laser-cut bar, sand a 3 mm dip under the head hole instead.

## Printed rod guide bar (XX_8, replaces the laser-cut guide bar)
- **One piece, 287.4 mm long.** It's laid **diagonally** on the bed so it fits. Don't rotate it. It prints upside down (ribs up). No supports, normal infill.
- **Install:** before the sticks go in, tilt it in through the open front and rest its ends on the two guide blocks, **ribs pointing down**. Line its holes up under the top-plate holes by pushing a stick through both, then put a drop of glue on each block.
- **Holes:** the 6 stick holes are drawn 7.0 mm, so they print about 6.8 and the sticks slide. The 2 shoulder-post holes (the pair close together in the middle) are drawn 6.5 mm, so they print snug for CA.
- It's 8 mm thick with two edge ribs, so it won't sag in the middle like a two-piece bar. Rhino check: it doesn't touch any cam, foot or stick at any shaft angle.

## Pins: what changed (Nov 11)
- **Rod and crossbar holes:** your printer shrinks small holes about 0.6 mm, so XX_6 now draws them at 2.8 and 3.1 mm.
- **Rod-top pins are optional.** Each cradle can just sit over its rod top, held down by the dragon's weight. If one hops off, pin it with a straightened paperclip.
- **Crossbar holes still need the filament links,** so they get the bigger size.
- **Hinge pins** come in 4 sizes, 3 of each. You can tell the size by the length:

  | Length | Diameter |
  |---|---|
  | 16 mm | 2.5 mm |
  | 17 mm | 2.6 mm |
  | 18 mm | 2.7 mm |
  | 19 mm | 2.8 mm |

  Use the fattest one that pushes through the chest-mount ears. It should turn freely in the wing knuckle.
- The old rods from DONE_2 still work for everything except the pin hole. Use the reprinted ones from XX_6.

## Motor, cover and electronics (JS-30 motor, 5 V 2 A adapter)
- **Bracket:** glue its two long arms flat against the outside of the left (motor) end wall, centred on the shaft hole. The camshaft now sticks out 30 mm.
- **Coupler:** slide it onto the camshaft, D-bore end first. Then try the 4 couplers on the motor shaft (1 ring = 3.5 mm bore, 2 = 4.5, 3 = 5.5, 4 = 6.5). Use the snuggest one that still slides on, and glue it to the motor shaft with CA.
- **Motor:** push the motor onto the coupler, with its face and ears flat on the bracket plate and the ears level (left and right, not up and down). Turn the hand crank once to check nothing binds, then CA the ears to the plate.
- **Electronics:** set the Uno flat on the table under the motor, front half, with its USB end facing out. Set the H-bridge flat in the back half.
- **Cover:** drop it over everything. It has an open bottom and an open side against the wall. The USB cable comes out of the slot in the outer end, and the adapter cable out of the notch in the back.

**Wiring for the 5 V adapter:**

| From | To | Note |
|---|---|---|
| Adapter + | H-bridge 12V terminal **and** H-bridge 5V terminal | Pull off the 5V-EN jumper |
| Adapter − | H-bridge GND | |
| H-bridge GND | Uno GND | Shared ground |
| Uno D9, D7, D8 | ENA, IN1, IN2 | Pull off the ENA jumper cap |
| OUT1, OUT2 | Motor | |

The Uno runs from the laptop USB cable. No VIN wire.

## Also needed (not printed)
- **1.75 mm filament** (what you print with), cut into short pieces:
  - pins through the top of each rod
  - two wing links, with L-hooks bent 29 mm apart
- To buy: a gearmotor (25 mm, 30–60 rpm), a barrel jack, a speed controller, CA glue and wood glue.

_The dragon is D3Craft's Flexi Dragon (MakerWorld). It's for your own use only, so don't share it or this folder._
