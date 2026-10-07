> STATUS: DRAFT - UNVERIFIED - requires human review at Gate G6/G7 (written at G1 rev B; no hardware exists yet)

# Flying MicroScout

This is how MicroScout is **designed** to be flown. There is no hardware yet, so everything below can be tried today only in the simulator (see [program.md](program.md)), and every safety behaviour is checked on the bench with props off at Gate G6 before anyone flies.

## Three ways to control it

| You have | How you fly | Best for |
|---|---|---|
| An ExpressLRS radio (any ELRS 2.4 GHz transmitter) | Sticks, with a switch for the flight mode and one for arming | Real piloting, acro, flips |
| A phone or laptop on the drone's Wi-Fi | On-screen sticks or buttons (app arrives with M8) | Beginners, demos, camera view |
| Python | `drone.takeoff()`, `drone.flip("back")`, ... | Classes, research, automation |

## Flight modes

| Mode | Sticks mean | The drone does for you | Who it is for |
|---|---|---|---|
| **Beginner** | Speed: push forward = fly forward up to 2 m/s; let go = it stops and holds position | Holds height and position (optical flow + ToF), **stops ~40 cm short of walls**, limits tilt and height (3 m ceiling) | First flights, indoors, classrooms |
| **Sport** | Tilt angle (up to 35°); throttle = climb/descend | Levels itself when you let go, holds height | Faster flying with a safety net |
| **Acro** | Rotation rate (up to 1000 °/s); you own the throttle | Nothing - it holds the attitude you leave it at | Flips, rolls, freestyle |

Sticks follow the usual radio convention (Mode 2): right stick forward = nose down = fly forward; right stick right = roll right; left stick right = yaw clockwise; left stick up = more throttle.

**One-button flips:** in any mode, a flip button (or `drone.flip("back" | "front" | "left" | "right")`) climbs briefly, rotates 360° at about 1000 °/s and levels out again. It refuses below 1 m.

## Before every flight

1. Props and ducts undamaged; canopy and battery strap secure.
2. Battery charged (USB-C on the drone, or a 2S balance charger). **Never charge unattended.** The drone will not arm while USB power is connected.
3. Fly in an open space, away from people, with the prop guards (ducts) on.
4. Arm on a level surface. Arming is refused if the drone is tilted, the battery is low or it is not on the ground.

## Safety behaviour (designed, checked at G6)

| Situation | What MicroScout does |
|---|---|
| Kill switch / `emergency_stop()` | Motors off immediately (it will fall) |
| Radio or Wi-Fi link lost while flying from a program | Hovers in place, then lands after 3 s |
| Battery low (below 3.4 V per cell under load for 2 s) | Lands by itself |
| Above the altitude ceiling (3 m by default) | Comes back down to the ceiling |
| Wall ahead in beginner mode | Stops before it |
| Battery current above 30 A | Trims throttle to protect the XT30 connector and the pack |

**Unplug the battery after every flight.** The power button turns off the electronics, but the motor power stage stays connected to the battery, and there is no fuse and no reverse-polarity protection (D-035, D-036): a damaged ESC or a wrongly wired battery lead can only be stopped by unplugging. Use packs with factory-fitted XT30 plugs.

## When it crashes

The ducted frame is designed to be the bumper: it is printed in a tough nylon (PA11) and the electronics sit on rubber grommets inside it, so that knocks go into the frame rather than the boards (not yet tested). Props are the part designed to break first - carry spares. Frame, canopy, strap and props come off without soldering. The design target is to survive 26 drops from 1 m and head-on hits at 3 m/s; faster crashes may break props or a duct (requirement R-22, tested by the owner at G5).

## Rules

In the US, recreational pilots must pass the free FAA TRUST test ([FAA](https://www.faa.gov/uas/recreational_flyers)); drones under 250 g flown recreationally do not need registration ([FAA](https://www.faa.gov/uas/getting_started/register_drone)). Rules differ by country and change - check yours. Respect privacy when the camera is on. This is draft guidance, not legal advice.
