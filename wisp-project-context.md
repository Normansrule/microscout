# Wisp: The Pocket Follow Drone
Project context for Claude. Read fully before every task.

## Mission
Wisp is the smallest, fastest-to-build open-source drone that knows where it is, tracks a target, avoids crashes and follows me while filming a vlog. Build time is measured in an afternoon per tier, not months, so buy proven parts and spend the effort on flight software, control theory and follow-me. It comes with a ground-control app (web, desktop and phone) and a GitHub Pages site that teaches every algorithm visually.

## Honest trade-offs (state them, don't hide them)
- "Smallest" and "films good vlog footage while following" pull against each other. Camera quality, onboard tracking compute and wind resistance all need mass. So Wisp has two airframes sharing one software stack.
- Fastest build means off-the-shelf flight controllers, frames, motors and sensors. Custom printed circuit boards (PCBs) come later, only if they beat the off-the-shelf parts.
- GPS follow-me is reliable outdoors. Vision follow-me works anywhere but is harder; build GPS first, vision second.

## Airframes
1. Wisp Nano (indoor and learning, about 30–40 g): a Crazyflie-class kit (Bitcraze) with optical-flow and time-of-flight (ToF) positioning, a multi-direction ranger for obstacle sensing, and an AI camera deck for simple tracking. It flies the same day and is ideal for control-theory experiments, but it's not for vlog footage.
2. Wisp Follow (vlog, under 250 g with battery): a ducted 3–3.5 inch frame with prop guards for flying near people; a small H7-class flight controller running ArduPilot; M10 GPS + compass; downward optical flow + ToF; forward and side ToF sensors for avoidance; ExpressLRS radio with Micro Air Vehicle Link (MAVLink) telemetry; a lightweight companion computer (Raspberry Pi Zero 2 W class) for vision tracking; and a stabilized small camera. Claude proposes the exact parts with a weight budget, cost and suppliers, and checks they're in stock.

## Positioning and tracking
- State estimation: an Extended Kalman Filter (EKF) fusing the inertial measurement unit (IMU), barometer, GPS, compass, optical flow and rangefinders. Show innovations and covariances live in the app.
- Indoor: optical flow + ToF hover hold; optional ultra-wideband (UWB) or lighthouse positioning on Nano.
- Tracking: real-time position and track history in the app, Remote ID broadcast where required, and a "find my drone" last-known position after a crash.

## Control theory (core of the project)
- Cascaded PID (proportional-integral-derivative) control for rate, attitude, velocity and position, derived and tuned step by step with Bode plots, step responses and disturbance tests.
- Advanced tracks: Linear Quadratic Regulator (LQR), Model Predictive Control (MPC) for trajectory following, and feed-forward plus jerk-limited trajectories for smooth cinematic motion.
- System identification: estimate thrust curves, motor time constants and drag from logs, then fit a model and validate it in simulation.
- Everything is developed in Software-In-The-Loop (SITL) simulation (ArduPilot SITL + Gazebo; the Crazyflie simulator for Nano) before it flies.

## Safety autopilot
- Crash avoidance: rangefinder-based obstacle avoidance (stop or path-bend), a minimum altitude above ground, geofences (cylinder + altitude ceiling), speed limits near the target, and predictive collision checks along the planned path.
- Crash detection: impact and attitude-loss detection, an instant motor cut, a logged crash event and a post-crash beacon.
- Failsafes: link loss, low battery, GPS loss and lost target each fall back to hover-hold, then return or land.
- Every safety feature has a SITL test case and a tethered or netted real-flight test before free flight.

## Follow-me
- Modes: follow (behind at a set distance and height), orbit, lead (fly ahead facing me), side track and cinematic dolly, with smooth framing and speed limits.
- Target sources: the phone's GPS through the app first, then vision tracking (person detection + a tracker on the companion computer) with automatic switching and confidence shown.
- Behavior: smooth, predictive following (filtered target velocity), obstacle checks first, and an instant stop and hover when the target is lost or I tap "stop".

## Law, safety and privacy
- Follow current Federal Aviation Administration (FAA) recreational rules: pass The Recreational UAS Safety Test (TRUST), keep visual line of sight (follow-me doesn't change that), get Low Altitude Authorization and Notification Capability (LAANC) approval in controlled airspace (much of the LA area), and handle registration and Remote ID based on weight and use. Verify the current rules before the first flight and link the sources in the docs.
- Don't fly over people who aren't participating; respect privacy when filming others; lithium polymer (LiPo) battery safety for charging and storage.

## Ground-control app and website
- One app for web, desktop (Tauri) and phone: live 3D flight view with the trajectory, a telemetry dashboard, a follow-me control screen, a pre-flight checklist and log replay.
- Control Lab: every controller and filter shown as an animated block diagram, with the equations live (values substituted as they change), plus tunable gains in SITL.
- GitHub Pages site: a scroll-driven story where the drone assembles part by part, lifts off, dodges an obstacle and locks onto a moving person, with the math visible on hover. Build guides with photos and GIFs.

## Design language
Premium, award-level, unmistakably original; never templated or generic AI-looking. References (borrow techniques, never copy layouts, assets or branding):
- apple.com and apple.com/airpods-pro: restraint, huge type, scroll-driven exploded-product storytelling
- rive.app: state-machine animation, UI that reacts to the cursor
- igloo.inc and dogstudio.co: cinematic WebGL
- bruno-simon.com: explorable 3D
- 1minus1.com: study what makes it distinctive
App feel: calm and glanceable, safety-critical information always visible, and one signature accent color for the drone and its path.
Use emil-design-eng, Impeccable and taste-skill for all UI work; run Impeccable's audit before calling it done.
Non-negotiable:
- 60 frames per second (fps) 3D views
- telemetry latency shown
- Web Content Accessibility Guidelines (WCAG) AA contrast
- reduced-motion fallback

## How to work
- Phases with review gates. Stop at each with photos or recordings, a summary and open questions.
- Simulation before hardware, tether before free flight. Never skip a safety test.
- Pick proven open stacks (ArduPilot, Crazyflie firmware) and extend them; don't rewrite a flight controller.
- If unsure about a part, a rule or a limit, say so and check. Provide Ubuntu terminal commands for every setup step.
- Spell out each acronym, with the acronym in parentheses, on first use per page. Replies to me concise and direct.

## Roadmap
0. Research, parts and weight budget for both airframes, architecture, 3 visual concepts
1. SITL simulation stack + Control Lab basics
2. Wisp Nano built and flying, with positioning and avoidance
3. Wisp Follow built, tuned and flying with GPS hold
4. Safety autopilot: avoidance, crash detection, failsafes
5. GPS follow-me, then vision follow-me
6. Advanced control (LQR, MPC, system identification)
7. App polish, website, release