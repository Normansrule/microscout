> STATUS: DRAFT - UNVERIFIED - requires human review at the Phase 0 gate. Research notes compiled on 2026-10-26 from the sources listed at the end; items not checked against a primary source are marked UNCONFIRMED.

# Wisp: ArduPilot research report (follow-me, avoidance, failsafes, SITL/Gazebo, SysID)

Date compiled: 2026-10-26. Target firmware: **ArduCopter 4.7.2** (tag `Copter-4.7.2`).

## How this was researched (read first)

- **Primary source = ArduPilot source code at tag `Copter-4.7.2`** (cloned from github.com/ArduPilot/ardupilot), plus the **ArduPilot wiki source** (github.com/ArduPilot/ardupilot_wiki, master @ 23c3dcd, 2026-10-25), the **ardupilot_gazebo README** (main @ 80dc966) and the **gazebosim/docs** source. Parameter names below were all grepped from `@Param`/`AP_GROUPINFO` lines in the 4.7.2 source unless marked otherwise.
- **ardupilot.org, firmware.ardupilot.org and discuss.ardupilot.org were blocked by this session's network policy**, and the web-search budget ran out. So I read the wiki through its GitHub source, not the rendered site, and **nothing here comes from discuss.ardupilot.org**. Anything that depends on those sites is marked UNCONFIRMED.
- **Tested here:** I built ArduCopter 4.7.2 SITL on Ubuntu 24.04 (g++ 13.3) and ran a headless Follow-mode test with the pymavlink target script in section 7. Results are in section 7.4.

> **4.7 renamed many parameters.** Older guides and LLM answers use the old names. Examples: `WPNAV_SPEED` became `WP_SPD` (m/s), `LOIT_SPEED` became `LOIT_SPEED_MS`, `ANGLE_MAX` (cdeg) became `ATC_ANGLE_MAX` (deg), `PILOT_SPEED_UP` became `PILOT_SPD_UP` (m/s), `SYSID_THISMAV` became `MAV_SYSID`, `SYSID_MYGCS` became `MAV_GCS_SYSID`, `AVOID_ANGLE_MAX` became `AVOID_ANG_MAX`, `ARMING_CHECK` became `ARMING_SKIPCHK`, and `EK3_MAX_FLOW` became `EK3_FLOW_MAX`. Old values are converted automatically on first boot. Source: `ArduCopter/ReleaseNotes.txt`, 4.7.0-beta1 section "5) Parameter scaling and/or renaming".

---

## 1. Current stable ArduCopter

| Item | Value | Evidence |
|---|---|---|
| Stable version | **Copter 4.7.2** | `ArduCopter/version.h`: `THISFIRMWARE "ArduCopter V4.7.2"`, `FW_TYPE_OFFICIAL` |
| Release date | **11 Oct 2026** (4.7.2-beta1 on 29 Sep 2026) | `ArduCopter/ReleaseNotes.txt` line 3 |
| Tag commit | `fb773567896014da007bca58358704d4a0d8516f` ("Plane: version to 4.7.2", 2026-10-13 07:37 +0900) | `git ls-remote` |
| `ArduCopter-stable` tag | points to the **same commit** as `Copter-4.7.2` | `git ls-remote` |
| `ArduCopter-beta` tag | **also the same commit**, so no 4.8 beta is out yet | `git ls-remote` |
| Release branch | `ArduPilot-4.7` (newer branches use `ArduPilot-4.x` names; there is no `Copter-4.7` branch) | `git ls-remote --heads` |
| Previous releases | 4.7.1 (31 Aug 2026), 4.7.0 (21 Jul 2026), 4.6.3 (04 Nov 2025) | ReleaseNotes.txt |
| firmware.ardupilot.org/Copter/stable | **UNCONFIRMED** (host blocked). The `ArduCopter-stable` git tag is what the firmware server builds from. | n/a |

**Build SITL from:** `git checkout Copter-4.7.2`, which is what was tested here. Use `master` only if you want 4.8-dev; master already differs, for example 32-bit `FOLL_SYSID` conversion for "ArduPilot-4.8".

---

## 2. Follow mode (Copter mode 23)

### 2.1 How it works in 4.7.x (source: `libraries/AP_Follow/AP_Follow.cpp`, `ArduCopter/mode_follow.cpp`)

1. **Message intake.** `GCS_MAVLINK::raw_packetReceived()` passes every packet to `AP_Follow::handle_msg()`. This happens after routing but **before** `accept_packet()`, so `MAV_OPTIONS` bit 0 ("accept only from GCS sysid") does **not** block follow data.
2. **Filtering** (`should_handle_message`). The packet is dropped if `FOLL_ENABLE=0`, if its sysid is 0, if its sysid is the vehicle's own, or if its sysid is not `FOLL_SYSID`.
3. **Accepted messages.** Only these two are used:
   - `GLOBAL_POSITION_INT`: lat, lon, `alt` (AMSL, mm) or `relative_alt` (mm, chosen by `FOLL_ALT_TYPE`), vx/vy/vz (cm/s, NED), and hdg (cdeg). Valid if `hdg <= 36000`. If the heading is missing and `FOLL_OFS_TYPE=1`, the packet is rejected. Acceleration is set to zero. lat=lon=0 is rejected.
   - `FOLLOW_TARGET`: `est_capabilities` bit 0 (position) is **required**. Bit 1 adds velocity, bit 2 acceleration, and bit 3 attitude quaternion plus body rates (gives heading and heading rate). `alt` is always treated as **AMSL metres**. Once one `FOLLOW_TARGET` is received, `GLOBAL_POSITION_INT` from that sysid is ignored until about 10 s of silence.
   - **ADSB is not used.** No ADSB handling exists in `AP_Follow`, in 4.7.2 or in 4.6.3.
4. **Timestamps.** Both messages pass through `JitterCorrection::correct_offboard_timestamp_msec()`, so the sender's `time_boot_ms`/`timestamp` only needs to be monotonic.
5. **Estimator (new in 4.7, PR #30101 "Follow mode improvements for target estimation and control", plus later fixes).**
   - Prediction: the last fix is projected forward by dead reckoning, `p + v·dt + ½a·dt²`, and heading by heading rate.
   - Smoothing: a jerk-limited kinematic estimate is shaped toward that prediction using `FOLL_ACCEL_NE/JERK_NE`, `FOLL_ACCEL_D/JERK_D` and `FOLL_ACCEL_H/JERK_H` (shape_pos_vel_accel). This is the "prediction / velocity feed-forward".
   - Reset: if the estimate drifts too far from the target (thresholds derived from accel/jerk × `FOLL_TIMEOUT`), it is re-initialised.
   - Relative offsets: with `FOLL_OFS_TYPE=1`, the offset rotates with target heading, and ω×r plus α×r + ω×(ω×r) terms are added to the feed-forward velocity and acceleration.
6. **Validity.** The estimate is invalid if no update arrives within **`FOLL_TIMEOUT` (default 3 s)**, or if the target is farther than **`FOLL_DIST_MAX` (default 100 m on Copter, 0 = no limit)**. When invalid, Follow commands zero velocity and acceleration, so the copter brakes and holds. This was verified in SITL.
7. **Control.** `ModeFollow::run()` feeds target position, velocity and acceleration (with offset) into `pos_control->input_pos_vel_accel_NE_m()` and `input_pos_vel_accel_D_m()`. These are feed-forward inputs, not a P loop.
   - Speed/accel limits are set on mode entry from **`WP_SPD`, `WP_ACC`, `WP_SPD_UP`, `WP_SPD_DN`, `WP_ACC_Z`**.
   - Position-controller gains are the `PSC_*` gains.
8. **Offsets.** If all three `FOLL_OFS_*` are 0 when Follow starts, the **current 3-D offset is captured** ("N-E-D follow offset loaded" or "Relative follow offset loaded") and cleared again on mode exit.
9. **Yaw** (`FOLL_YAW_BEHAVE`). 0 = none, 1 = face lead (default), 2 = same heading as lead (uses heading rate), 3 = direction of flight.
10. **Gimbal.** `FOLL_OPTIONS` bit 0 makes the mount track the lead on mode entry.
11. **Logging.** The `FOLL` log message has target lat/lon/alt, VelN/E/D, and the estimated lat/lon/alt.

### 2.2 Breaking changes that matter for Wisp

- **4.7.2 removed automatic sysid detection** (PR #33937). In ≤4.7.1, `FOLL_SYSID=0` meant "follow the first sender and write its sysid". **In 4.7.2, 0 means no target, so you must set `FOLL_SYSID` explicitly.** Verified in SITL: with `FOLL_SYSID=0`, groundspeed stayed 0 while the target moved.
- **Changing `FOLL_SYSID` in flight discards the old target state** (PR #33891). The copter holds until the new sysid is heard. This is useful for switching from phone GPS to a vision-derived target published under another sysid.
- **Copter Follow no longer calls simple avoidance or fence velocity limiting.** In 4.6.3, `mode_follow.cpp` called `copter.avoid.limit_velocity_2D()` and `copter.avoid.adjust_velocity()`. In 4.7.2, `mode_follow.cpp` has **no avoidance calls**. Follow also does not use `wp_nav`, so **BendyRuler/Dijkstra are not used either**.
  - Consequence: ToF-based obstacle avoidance does **nothing** in Follow mode on 4.7.2. Fence *breach actions* still apply, because they are handled by the fence library, not by the mode.
  - Options: (a) do the follow logic in **Guided velocity control** from the companion (simple avoidance applies there; see 2.5), or (b) a Lua script that watches proximity and changes mode or offsets.
- **`FOLL_POS_P` is defined but not read by Copter 4.7.2.** Only `Rover/mode_follow.cpp` reads `get_pos_p()`. The wiki still says it "controls how aggressively this vehicle moves towards lead vehicle (limited by WP_SPD)". That is a doc/code mismatch; in Copter 4.7 tune with `PSC_*`, `WP_SPD`/`WP_ACC` and `FOLL_ACCEL_*`/`FOLL_JERK_*`.
- **Altitude trap, observed in SITL.** With `FOLL_OFS_Z=0` and a non-zero X offset, the copter descended from 10 m to the phone's height (1.5 m above home). **Always set `FOLL_OFS_Z` negative** (Z is down; for example `FOLL_OFS_Z=-8` means 8 m above the phone), or leave all offsets 0 so the entry offset is captured.

### 2.3 Every `FOLL_*` parameter in Copter 4.7.2 (index, default)

| Param | Default | Notes |
|---|---|---|
| `FOLL_ENABLE` | 0 | 0/1; enable flag (refresh params after setting) |
| `FOLL_SYSID` | 0 | target sysid; 0 = none (no auto-detect in 4.7.2); range 0–255 |
| `FOLL_DIST_MAX` | 100 m (Copter) | estimate invalid beyond this; 0 = no limit |
| `FOLL_OFS_TYPE` | 0 | 0 = NED, 1 = relative to lead heading |
| `FOLL_OFS_X` / `_Y` / `_Z` | 0 m | forward(N) / right(E) / **down**; range −100..100 |
| `FOLL_YAW_BEHAVE` | 1 | 0 None, 1 Face lead, 2 Same as lead, 3 Direction of flight |
| `FOLL_POS_P` | 0.1 | AC_P subgroup; **unused by Copter 4.7.2** (Rover only) |
| `FOLL_ALT_TYPE` | 1 (Copter) | 0 absolute (uses `alt`), 1 relative-to-home (uses `relative_alt`), 3 terrain (needs terrain data, else update discarded) |
| `FOLL_OPTIONS` | 0 | bit 0: mount follows lead on mode entry |
| `FOLL_ACCEL_NE` | 5.0 m/s² | estimator horizontal accel limit |
| `FOLL_JERK_NE` | 10.0 m/s³ | estimator horizontal jerk limit |
| `FOLL_ACCEL_D` | 5.0 m/s² | estimator vertical accel limit |
| `FOLL_JERK_D` | 10.0 m/s³ | estimator vertical jerk limit |
| `FOLL_ACCEL_H` | 360 deg/s² | estimator heading accel limit |
| `FOLL_JERK_H` | 720 deg/s³ | estimator heading jerk limit |
| `FOLL_TIMEOUT` | 3 s | no update for this long means hold position |

Not found in source: `FOLL_TYPE` and `FOLL_MARGIN` (indices 2 and 4 are "reserved"). The params `FOLL_ORB_RADIUS` and `FOLL_ORB_TIME` exist only when the example script `orbit_follow.lua` is loaded.

Other ways to set the target:
- `MAV_CMD_DO_FOLLOW` (param1 = sysid 1–255) sets `FOLL_SYSID` (`handle_command_do_follow`).
- Lua bindings: `follow:get_target_sysid()`, `have_target()`, `get_target_location_and_velocity()`, `get_target_location_and_velocity_ofs()`, `get_target_heading_deg()`, `get_last_update_ms()`, `get_target_dist_and_vel_NED_m()` (`libraries/AP_Scripting/docs/docs.lua`).

### 2.4 Lua and GCS follow material

| Item | Path / page | What it does |
|---|---|---|
| `follow-target-send.lua` | `libraries/AP_Scripting/applets/` | A lead *vehicle* publishes `FOLLOW_TARGET` at 10 Hz. Params `FOLT_ENABLE`, `FOLT_MAV_CHAN`. The wiki recommends FOLLOW_TARGET over GLOBAL_POSITION_INT. |
| `orbit_follow.lua` | `libraries/AP_Scripting/examples/` | Orbits the lead by rewriting `FOLL_OFS_X/Y` at 10 Hz. Adds `FOLL_ORB_RADIUS` (default 5 m) and `FOLL_ORB_TIME` (default 10 s). Good template for Wisp "orbit" shots. |
| `plane_follow.lua`, `plane_guided_follow.lua` | applets / examples | Plane-only references |
| Wiki "Follow Me Mode (GCS Enabled)" | `copter/source/docs/ac2_followme.rst` | Implemented **in the GCS**: Mission Planner reads a GPS dongle and sends Guided "fly to here" commands every 2 s. No `FOLL_*` involved. |
| MAVProxy `followtest` module | `MAVProxy/modules/mavproxy_followtest.py` | Circles a fake target around home (settings `radius` 100, `altitude` 50, `speed` 10, `type` guided/yaw) and sends **Guided `MISSION_ITEM_INT` (current=2)**, not GLOBAL_POSITION_INT. It tests the GCS-guided style, **not FOLLOW mode**. Load with `module load followtest`, then `followtest set speed 3`. |

### 2.5 Guided mode as the companion-computer alternative (orbit / lead / cinematic)

From `ArduCopter/GCS_MAVLink_Copter.cpp` and `mode_guided.cpp` (4.7.2):

`SET_POSITION_TARGET_LOCAL_NED` (frames LOCAL_NED, LOCAL_OFFSET_NED, BODY_NED, BODY_OFFSET_NED) and `SET_POSITION_TARGET_GLOBAL_INT` are dispatched by `type_mask`:

| Fields given | Function called | Run function | Simple avoidance (proximity/fence velocity limit)? | OA path planner? |
|---|---|---|---|---|
| pos + vel (+acc) | `set_pos_vel_accel_NED_m` | `posvelaccel_control_run` | No | No |
| vel (+acc) only | `set_vel_accel_NED_m` | `velaccel_control_run` | **Yes** (`copter.avoid.adjust_velocity_NED_m`) | No |
| acc only | `set_accel_NED_mss` | `accel_control_run` | No (only `velaccel_control_run` calls `adjust_velocity_NED_m`) | No |
| pos only | `set_pos_NED_m` / `set_destination` | `pos_control_run`, or `wp_control_run` if `GUID_OPTIONS` bit 6 | No | **Only if `GUID_OPTIONS` bit 6 (64) "Waypoint navigation used for position targets"** |

- `GUID_OPTIONS` bits: 0 Allow arming from TX, 2 Ignore pilot yaw, 3 SetAttitudeTarget thrust-as-thrust, 4 Do not stabilize PositionXY, 5 Do not stabilize VelocityXY, **6 WPNav for position targets**, 7 Allow weathervaning.
- `GUID_TIMEOUT` (default 3 s) applies to velocity, acceleration and angle streams: the vehicle stops if they stop.
- Recommendation for Wisp: the Pi computes the desired velocity (and yaw) from the phone fix or the vision track and streams velocity-only `SET_POSITION_TARGET_LOCAL_NED` at 10–20 Hz. This keeps **simple avoidance and fence limiting active**, unlike FOLLOW in 4.7.

---

## 3. Object avoidance

### 3.1 Simple avoidance (`libraries/AC_Avoidance/AC_Avoid.cpp`, group `AVOID_`)

| Param | Default | Meaning |
|---|---|---|
| `AVOID_ENABLE` | 3 (fence + proximity) | bitmask 0 UseFence, 1 UseProximitySensor, 2 UseBeaconFence (wiki suggests 7 = all) |
| `AVOID_MARGIN` | 2 m | standoff distance in GPS (position-controlled) modes |
| `AVOID_BEHAVE` | Copter: 0 Slide (Rover: Stop) | 0 Slide, 1 Stop |
| `AVOID_DIST_MAX` | 5 m | non-GPS (AltHold) lean-avoidance start distance |
| `AVOID_ALT_MIN` | 0 m | proximity avoidance only above this height; needs a valid **downward rangefinder** |
| `AVOID_ACCEL_MAX` | 3 m/s² | max accel used for avoidance (0 = no limit) |
| `AVOID_BACKUP_SPD` | 0.75 m/s | horizontal back-away speed (0 disables) |
| `AVOID_BACKUP_DZ` | 0.10 m | back-away deadzone |
| `AVOID_BACKZ_SPD` | 0.75 m/s | vertical back-away speed |
| `AVOID_ANG_MAX` | 10 deg | AltHold lean-based avoidance; **compiled only if `AP_AVOIDANCE_ALTHOLD_ENABLED` (default 0 in 4.7: "Lean-angle based object avoidance disabled by default, re-enable with custom build server")** |

Which modes use it, from 4.7.2 source:
- **Loiter: yes.** `AC_Loiter.cpp` calls `_avoid->adjust_velocity`.
- **Guided velocity control: yes** (see 2.5).
- **Vertical (upward) limiting:** `get_avoidance_adjusted_climbrate_ms` is called in AltHold, Loiter, PosHold, Sport, Auto (some paths), Circle, FlowHold, ZigZag, Autotune and Guided angle control.
- **AltHold and FlowHold horizontal (lean):** `adjust_roll_pitch_rad`, but only with the AltHold build option.
- **Follow: no** (4.7 change, see 2.2).
- RC aux switch `RCx_OPTION = 40` (Proximity Avoidance) toggles proximity avoidance (wiki). The wiki states "Horizontal object avoidance works in AltHold and Loiter".

### 3.2 Proximity from ToF rangefinders

- `PRX1_TYPE = 4` (RangeFinder). Other values include 2 MAVLink, **10 SITL**, 15 Scripting (`AP_Proximity_Params.cpp`). Only one proximity source can be enabled: either a 360° lidar or up to 9 rangefinders (wiki).
- Rangefinders: `RNGFNDx_TYPE`. ToF-relevant values: 16 VL53L0X/VL53L1X, 28 VL53L1X-ShortRange, 37/38/40 NoopLoop TOFSense, 32 MSP, 10 MAVLink, **100 SITL**.
- `RNGFNDx_ORIENT`: 0 Forward, 1 Fwd-Right, 2 Right, 3 Back-Right, 4 Back, 5 Back-Left, 6 Left, 7 Fwd-Left, 24 Up, **25 Down**.
- `RNGFNDx_MIN` / `RNGFNDx_MAX` are in **metres** in 4.7 (`@Units: m`). `RNGFNDx_GNDCLR` is 0.05–1.5 m.
- In SITL, `PRX1_TYPE=10` builds obstacles from fence polygons. Simulated rangefinders use `RNGFNDx_TYPE=100` with `SIM_SONAR_*` (UNCONFIRMED: SIM_SONAR names not grepped in this pass).

### 3.3 Path planning (`AP_OAPathPlanner`, group `OA_`)

- `OA_TYPE`: 0 Disabled, **1 BendyRuler**, **2 Dijkstra**, 3 Dijkstra with BendyRuler.
- `OA_MARGIN_MAX` (5 m), `OA_OPTIONS` (default 1; Copter bit 1 log Dijkstra points, bit 2 fast waypoints).
- `OA_DB_SIZE`, `OA_DB_EXPIRE` (s), `OA_DB_QUEUE_SIZE`, `OA_DB_OUTPUT` (0–3), `OA_DB_BEAM_WIDTH` (5°), `OA_DB_RADIUS_MIN` (0.01 m), `OA_DB_DIST_MAX` (0 m), `OA_DB_ALT_MIN` (0 m).
- **BendyRuler:** `OA_BR_LOOKAHEAD` (15 m, range 1–100), `OA_BR_CONT_RATIO` (1.5, range 1.1–2), `OA_BR_CONT_ANGLE` (75°, range 20–180), `OA_BR_TYPE` (1 horizontal, 2 vertical search).
- **Modes:** the wiki says "only applicable in AUTO, GUIDED, and RTL". In source, OA lives in `AC_WPNav_OA`, so it applies to whatever uses `wp_nav` waypoints: Auto, RTL, and Guided **position targets only when `GUID_OPTIONS` bit 6 is set**.
- **Follow does not use BendyRuler**, and Loiter uses simple avoidance, not OA.
- BendyRuler on a 250 g quad with a few ToF sensors (short range, narrow beams) will have little lookahead. UNCONFIRMED in practice; test in SITL with `OA_BR_LOOKAHEAD` reduced to the sensor range.

---

## 4. Crash detection, E-stop and failsafes

### 4.1 Crash check (`ArduCopter/crash_check.cpp`, `FS_CRASH_CHECK` default 1)

The copter **disarms** (`AP_Arming::Method::CRASH`, GCS text "Crash: Disarming: AngErr=..>30, Accel=..<3", ERR log `CRASH_CHECK`) when all of these hold continuously for **2 s** (`CRASH_CHECK_TRIGGER_SEC`, counted in main-loop iterations):
1. armed, not `land_complete`, not in standby, not force-flying, `FS_CRASH_CHECK != 0`;
2. mode allows crash check (all modes **except Acro and Flip**); not AUTOROTATE;
3. 1 Hz low-pass earth-frame accel (gravity removed) **< 3 m/s²**;
4. actual lean angle **> 15°**;
5. attitude error **> 30°**;
6. speed **< 10 m/s** (if a velocity estimate exists).

This is a "landed in a bad attitude" detector. It is **not instant** (2 s) and will not fire while tumbling fast. For "instant motor cut" in Wisp, use one of these:
- **RC aux `RCx_OPTION = 31` Motor Emergency Stop.** HIGH = stop, LOW = run (via `SRV_Channels::set_emergency_stop`; outputs go to zero, interlock off).
- **`RCx_OPTION = 165` ARM/EMERGENCY STOP.** HIGH = arm and clear E-stop, MIDDLE = clear E-stop, LOW = E-stop.
- **MAVLink force-disarm:** `MAV_CMD_COMPONENT_ARM_DISARM` with param1=0, **param2=21196** (`GCS::magic_force_arm_disarm_value`). This disarms in flight, so the companion or phone app can kill motors instantly.
- **Lua `crash-actions.lua`** adds `CRASH_ACT1..4`, `_INST`, `_TIME` actions after crash detection. Its doc says "firmware v4.8 and later", so treat it as **not supported on 4.7.2** (UNCONFIRMED whether it works on 4.7).

The motor E-stop auto-disarm timing was not checked (UNCONFIRMED).

### 4.2 Parachute / loss-of-control (`parachute_check`, same file)

- Triggers if `CHUTE_ENABLED=1` and attitude error **> 30° for 1 s** (`PARACHUTE_CHECK_TRIGGER_SEC`), or on sink rate > `CHUTE_CRT_SINK`, above `CHUTE_ALT_MIN`.
- Params: `CHUTE_ENABLED`, `CHUTE_TYPE` (0 Relay, 10 Servo), `CHUTE_SERVO_ON`, `CHUTE_SERVO_OFF`, `CHUTE_ALT_MIN`, `CHUTE_DELAY_MS`, `CHUTE_CRT_SINK`, `CHUTE_OPTIONS` (bit 0 hold open, bit 1 skip disarm before release).
- For Wisp this is a 1-second loss-of-control detector that could drive a relay or kill path. On a 250 g quad, "parachute" usually means disarm.

### 4.3 Thrust loss and yaw imbalance (same file)

- **Thrust loss.** For **1 s**, all of these hold: desired lean < 15°, throttle ≥ 90% (or throttle saturated) and > 25%, descending, attitude error < 30°. Then motor **thrust boost** is enabled. Disable with `FLIGHT_OPTIONS` bit 0. Bit 2 releases the gripper on thrust loss.
- **Yaw imbalance warning.** Filtered yaw I-term > 75% of IMAX. Warns every 10 s. Disable with `FLIGHT_OPTIONS` bit 1.

### 4.4 Vibration and EKF failsafes (`ArduCopter/ekf_check.cpp`)

- **`FS_VIBE_ENABLE` (default 1).** Bad-vibe detection (positive velD/posD innovations with filtered vel variance > 1, or the EKF reports vibration affected) persisting **≥ 1 s** switches on `pos_control->set_vibe_comp(true)`, a modified altitude controller. It turns off after 15 s clear. Not in manual-throttle modes.
- **EKF failsafe.** `FS_EKF_THRESH` (0 disabled, 0.6 strict, **0.8 default**, 1.0 relaxed). Triggers after **1 s** (10 checks at 10 Hz) of two of compass/vel/pos variances over threshold (or vel variance > 2× threshold). Action `FS_EKF_ACTION`: 0 Report only, **1 Land if mode needs position (default)**, 2 AltHold, 3 Land from all modes.
- **Dead-reckoning failsafe.** `FS_DR_ENABLE` (default 2 = RTL) and `FS_DR_TIMEOUT` (30 s).

### 4.5 Radio, GCS and battery failsafes (`ArduCopter/Parameters.cpp`, `AP_BattMonitor_Params.cpp`)

**Radio**
- `FS_THR_ENABLE`: 0 Disabled, **1 always RTL (default)**, 3 always Land, 4 SmartRTL or RTL, 5 SmartRTL or Land, 6 Auto DO_LAND_START or RTL, 7 Brake or Land.
- `FS_THR_VALUE`: PWM 910–1100.

**GCS**
- `FS_GCS_ENABLE`: **0 Disabled (default)**, 1 RTL, 3 SmartRTL or RTL, 4 SmartRTL or Land, 5 Land, 6 Auto DO_LAND_START or RTL, 7 Brake or Land.
- `FS_GCS_TIMEOUT`: default 5 s, range 2–120.
- `FS_OPTIONS` bitmask: 0 continue in Auto on RC FS, 1 continue in Auto on GCS FS, 2 continue in Guided on RC FS, 3 continue if landing, **4 continue in pilot-controlled modes on GCS FS (default)**, 5 release gripper.
- **The GCS heartbeat must come from `MAV_GCS_SYSID` (default 255), or from the range up to `MAV_GCS_SYSID_HI`.** Have the phone app send heartbeats as sysid 255 (and position as another sysid that matches `FOLL_SYSID`), or widen the range.
- For a phone-only (no RC) drone, **enable `FS_GCS_ENABLE`**. Note that bit 4 of `FS_OPTIONS` would *suppress* the GCS failsafe in pilot modes.

**Battery**
- `BATT_LOW_VOLT`, `BATT_CRT_VOLT`, `BATT_LOW_MAH`, `BATT_LOW_TIMER`, `BATT_FS_VOLTSRC` (0 raw, 1 sag-compensated).
- `BATT_FS_LOW_ACT` / `BATT_FS_CRT_ACT`: 0 Warn, 1 Land, 2 RTL, 3 SmartRTL or RTL, 4 SmartRTL or Land, 5 Terminate, 6 DO_LAND_START or RTL, 7 Brake or Land.

### 4.6 Geofence (`libraries/AC_Fence/AC_Fence.cpp`, Copter)

- `FENCE_ENABLE` (0/1).
- `FENCE_TYPE` bitmask: 0 Max altitude, 1 Circle centred on home, 2 Inclusion/exclusion circles and polygons, 3 Min altitude. **Copter default 7** (alt max + circle + polygon). The min-alt fence enables only after reaching it.
- `FENCE_ACTION` (Copter): 0 Report only, **1 RTL or Land (default)**, 2 Always Land, 3 SmartRTL or RTL or Land, 4 Brake or Land, 5 SmartRTL or Land.
- `FENCE_ALT_MAX` (100 m), `FENCE_ALT_MIN` (−10 m), `FENCE_RADIUS` (300 m), `FENCE_MARGIN` (2 m), `FENCE_MARGIN_XY`, `FENCE_TOTAL`, `FENCE_AUTOENABLE` (0 off, 1 on takeoff, 2 disable floor on landing, 3 only when armed), `FENCE_OPTIONS` (bit 0 disable mode change until breach cleared, 1 union of inclusion areas, 2 notify on margin breaches), `FENCE_NTF_FREQ`, `FENCE_ALT_MAX_TP` / `FENCE_ALT_MIN_TP` (0 AMSL, 1 home, 2 origin, 3 terrain).
- After a breach, the circle fence is recreated **20 m further out** (Copter). The pilot gets a 10 s manual-recovery window.

### 4.7 GPS glitch

- `Copter::gpsglitch_check()` (10 Hz) only **logs and announces** "GPS Glitch or Compass error" / "Glitch cleared" when the AHRS reports `GPS_GLITCHING`. Arming is blocked while glitching ("GPS glitching" pre-arm).
- The protection itself is in EKF3:
  - `EK3_GLITCH_RAD` (default 25 m): beyond this, the EKF resets to GPS. If set to 0, innovations are clipped to `EK3_POS_I_GATE`/`EK3_VEL_I_GATE` instead.
  - `EK3_GPS_CHECK` covers pre-flight GPS quality.
  - `EK3_OPTIONS` bit 0 is JammingExpected.
- A position failsafe then comes from the EKF and dead-reckoning failsafes above.

### 4.8 Speed and agility limits (4.7 names)

| Param | Default | Notes |
|---|---|---|
| `WP_SPD` | 10 m/s (range 0.1–20) | was `WPNAV_SPEED` (cm/s); **also the Follow horizontal speed limit** |
| `WP_SPD_UP` / `WP_SPD_DN` | 2.5 / 1.5 m/s | also Follow vertical limits |
| `WP_ACC` / `WP_ACC_Z` / `WP_ACC_CNR` | 2.5 / – / 0 (=2×ACC) m/s² | WP_ACC is the Follow horizontal accel |
| `LOIT_SPEED_MS` | 12.5 m/s | was `LOIT_SPEED` |
| `LOIT_ACC_MAX_M`, `LOIT_BRK_ACC_M`, `LOIT_BRK_JRK_M`, `LOIT_BRK_DELAY`, `LOIT_ANG_MAX`, `LOIT_OPTIONS` | 5 m/s², 2.5, –, –, 0, – | |
| `ATC_ANGLE_MAX` | 30 deg (range 10–80) | was `ANGLE_MAX` (cdeg) |
| `PSC_ANGLE_MAX` | 0 | position-controller lean limit (0 = use ATC_ANGLE_MAX) |
| `PILOT_SPD_UP` / `PILOT_SPD_DN` / `PILOT_ACC_Z` | 2.5 m/s / – / 2.5 m/s² | were `PILOT_SPEED_UP` / `PILOT_SPEED_DN` / `PILOT_ACCEL_Z` |

Sport mode (13) exists. No Sport-specific speed parameters were checked (UNCONFIRMED).

---

## 5. Optical flow + rangefinder (non-GPS) and source switching

**Source sets.** `EK3_SRC1_*`, `EK3_SRC2_*` and `EK3_SRC3_*`, each with `POSXY`, `VELXY`, `POSZ`, `VELZ`, `YAW`:
- POSXY: 0 None, 3 GPS, 4 Beacon, 6 ExtNav
- VELXY: adds 5 OpticalFlow, 7 WheelEncoder
- POSZ: 1 Baro, 2 RangeFinder, 3 GPS, 4 Beacon, 6 ExtNav
- YAW: 1 Compass, 2 GPS, 3 GPS+compass fallback, 6 ExtNav, 8 GSF

`EK3_SRC_OPTIONS` bitmask: 0 FuseAllVelocities, 1 AlignExtNavPosWhenUsingOptFlow, 3 UsePerCoreEKFSources. Default 0; the 4.7 notes say it defaults to *not* FuseAllVelocities.

**Flow-only setup (wiki).** `EK3_SRC1_POSXY=0`, `VELXY=5`, `POSZ=1`, `VELZ=0`, `YAW=1`, `EK3_SRC_OPTIONS=0`.
- Flow sensor params: `FLOW_TYPE` (1 PX4Flow, 2 Pixart, 3 Bebop, 4 CXOF, 5 MAVLink, 6 DroneCAN, 7 MSP, 8 UPFLOW, **10 SITL**), `FLOW_FXSCALER`, `FLOW_FYSCALER`, `FLOW_ORIENT_YAW`, `FLOW_POS_X/Y/Z`, `FLOW_ADDR`, `FLOW_OPTIONS`, `FLOW_HGT_OVR` (Rover).
- `EK3_FLOW_MAX` defaults to 2.5 rad/s (renamed from `EK3_MAX_FLOW`).
- `EK3_OPTIONS` bit 2 lets flow use SRTM terrain altitude above rangefinder range (new in 4.7).
- 4.7.2 fixed the "Optical flow terrain scale height sign" (PR #34360).

**GPS ↔ flow switching.**
- Set SRC1 = GPS and SRC2 = flow (example values above).
- Switch with **`RCx_OPTION = 90` (EKF Source Set: low/mid/high = SRC1/2/3)**, or **`MAV_CMD_SET_EKF_SOURCE_SET`** from the companion (handled in `GCS_Common.cpp`).
- Or automate with `libraries/AP_Scripting/examples/ahrs-source-gps-optflow.lua`:
  - `RCx_OPTION=300` enables auto-selection.
  - `SCR_USER1` = rangefinder altitude threshold (about 15 m)
  - `SCR_USER2` = GPS speed-accuracy threshold (about 0.3)
  - `SCR_USER3` = flow quality (about 50)
  - `SCR_USER4` = flow innovation (about 0.15)
- Related: `ahrs-source.lua`, `ahrs-source-extnav-optflow.lua` (applet), `active_source_set.lua`.
- FlowHold (mode 22) holds position from flow without a rangefinder.

---

## 6. Remote ID (reference)

- Library `AP_OpenDroneID`. Off by default (`AP_OPENDRONEID_ENABLED 0`); enable with the waf option `--enable-opendroneid`, `define AP_OPENDRONEID_ENABLED 1` in hwdef, or the custom build server feature "OpenDroneID".
- **SITL builds always enable it** (`Tools/ardupilotwaf/boards.py`: `cfg.define('AP_OPENDRONEID_ENABLED', 1)` for the SITL board).
- Params (grepped): `DID_ENABLE`, `DID_MAVPORT` (−1 disabled, 0–6 serial), `DID_CANDRIVER` (0/1/2), `DID_OPTIONS` (bit 0 EnforcePreArmChecks, 1 AllowNonGPSPosition, 2 LockUASIDOnFirstBasicIDRx), `DID_BARO_ACC`, plus more not listed here.
- ODID boards use a distinct board ID and read-only DID params (wiki `dev/.../opendroneid.rst`). Hardware example: ArduRemoteID (ESP32-S3/C3 module, github.com/ArduPilot/ArduRemoteID).
- FAA weight rules for sub-250 g craft were not researched here (UNCONFIRMED).

---

## 7. SITL on Ubuntu 24.04 and a follow-me test

### 7.1 Install and build (wiki `building-setup-linux.rst`, `setting-up-sitl-on-linux.rst`)

```bash
sudo apt update && sudo apt install -y git
git clone --recurse-submodules https://github.com/ArduPilot/ardupilot.git
cd ardupilot
git checkout Copter-4.7.2 && git submodule update --init --recursive
Tools/environment_install/install-prereqs-ubuntu.sh -y
. ~/.profile        # or log out/in
./waf configure --board sitl
./waf copter        # took 8m04s on 2 cores here
```

- The script maps Ubuntu 24.04 to codename `noble`. On noble it installs Python packages (`lxml pymavlink pyserial MAVProxy geocoder empy==3.3.4 ptyprocess dronecan`) into a **venv at `~/venv-ardupilot`**, activated from `~/.profile`.
- I did not run the prereq script itself (I used a manual venv). The commands above follow the wiki and the script's source.

### 7.2 Run SITL with MAVProxy

```bash
cd ardupilot/ArduCopter
sim_vehicle.py -v ArduCopter --console --map -w      # first run: -w wipes params
# later runs: sim_vehicle.py -v ArduCopter --console --map
```

Ports (source `SITL_State.h`, `sim_vehicle.py`):
- SERIAL0 `tcp:5760` (MAVProxy master)
- **SERIAL1 `tcp:5762`** and SERIAL2 `tcp:5763`, free for scripts or a companion. SERIAL1 defaults to MAVLink2.
- MAVProxy outputs `udp:127.0.0.1:14550` (QGC/MP) and, as usual, 14551 (UNCONFIRMED: only 14550 was seen in the source excerpt).

Instance *i* adds 10×*i* to every port. Multi-vehicle options: `--count N --auto-sysid --auto-offset-line 90,10` or `--swarm Tools/autotest/swarminit.txt`. `--sysid` sets `MAV_SYSID`.

### 7.3 Follow-me test sequence (MAVProxy console)

```text
param set FOLL_ENABLE 1
param fetch                     # FOLL_* subtree appears after enabling
param set FOLL_SYSID 101        # MUST be explicit in 4.7.2
param set FOLL_OFS_TYPE 1       # offset relative to target heading
param set FOLL_OFS_X -5         # 5 m behind
param set FOLL_OFS_Z -8         # 8 m ABOVE the phone (Z is down!)
param set FOLL_YAW_BEHAVE 1     # face the person
param set WP_SPD 8              # Follow horizontal speed cap (m/s)
mode guided
arm throttle
takeoff 10
mode follow
```

Then, in a second terminal (the "phone"):

```bash
python3 fake_phone_target.py --connect tcp:127.0.0.1:5762 --sysid 101 --pattern circle --speed 3 --radius 25
# or behind MAVProxy:  --connect udpin:127.0.0.1:14550
# FOLLOW_TARGET variant: add --msg follow_target
```

Script: `software/wisp_sitl/fake_phone_target.py`. What it does:
- connects with `source_system=101`;
- requests `HOME_POSITION` (`MAV_CMD_REQUEST_MESSAGE`) to anchor the path;
- sends a 1 Hz HEARTBEAT;
- streams `GLOBAL_POSITION_INT` at 5 Hz with `alt` (AMSL mm), `relative_alt` (mm), vx/vy (cm/s) and hdg (cdeg). Optionally it sends `FOLLOW_TARGET` with `est_capabilities = pos|vel|att`.

Core of it:

```python
m = mavutil.mavlink_connection("tcp:127.0.0.1:5762", source_system=101)
m.wait_heartbeat()
# ...each 0.2 s, with lat/lon moving at v m/s along a circle:
m.mav.global_position_int_send(now_ms, int(lat*1e7), int(lon*1e7),
    int((home_amsl_m+1.5)*1000), int(1.5*1000),     # alt, relative_alt (mm)
    int(vn*100), int(ve*100), 0, int(hdg_deg*100))  # cm/s, cdeg
```

### 7.4 What was actually run here (headless, no MAVProxy)

- Setup: `sim_vehicle.py -v ArduCopter --no-rebuild --no-mavproxy -w`, plus a pymavlink "GCS" on 5760 (a throwaway test script (not kept)) and the target script on 5762.
- Settings: `FOLL_ENABLE=1`, `FOLL_OFS_X=-5`, `FOLL_OFS_TYPE=1`; Guided, arm, takeoff 10 m, then FOLLOW.

Results:
- `FOLL_SYSID=0`: groundspeed **0.0** for 12 s, so no following. This confirms there is no auto-sysid in 4.7.2.
- `FOLL_SYSID=101`: within about 6 s, groundspeed was **3.0 m/s** (equal to the target speed) and `NAV_CONTROLLER_OUTPUT.wp_dist` was **0 m** (integer, so < 1 m from the offset point), held for 60 s.
- Altitude went from 594.1 to **585.6 m AMSL**, which is the target's 1.5 m above home, because `FOLL_OFS_Z` was 0. **Set `FOLL_OFS_Z` negative.**
- Target script killed: after about 3 s (`FOLL_TIMEOUT`), groundspeed went to 0 and the copter held position. LAND then disarmed normally.

### 7.5 Autotest references (`Tools/autotest/arducopter.py`)

- **`ModeFollow`** (line 9113).
  - Setup: `FOLL_ENABLE=1`, `FOLL_SYSID=self.mav.source_system` (the test's own GCS sysid), `FOLL_OFS_X=-30`, `FOLL_OFS_TYPE=1`; takeoff in LOITER; `SIM_SPEEDUP=1`; FOLLOW.
  - It then sends `GLOBAL_POSITION_INT` every 0.5 s for a stationary target, then with `FOLL_ALT_TYPE=1` and a deliberately bad `alt` (666 mm) to prove `relative_alt` is used, then a target moving at (3, 2, −1) m/s with hdg.
  - Pass condition: position within 3 m of the expected point.
- **`ModeFollow_with_FOLLOW_TARGET`** (line 9274). Same idea with `follow_target_send(... 1<<0|1<<1|1<<3 ...)`. It then uses `wait_speed_vector(Vector3(3, 2, 0))` to check velocity matching.
- Run with `Tools/autotest/autotest.py build.Copter test.Copter.ModeFollow` (pattern from `AGENTS.md`; not run here).

### 7.6 A sub-250 g physics model for SITL

The SITL multicopter model takes a JSON frame: `--model quad:/path/wisp.json`. The frame string must contain `:` and end in `.json` (`SIM_Frame::init`).
- Keys: `mass`, `diagonal_size`, `refSpd`, `refAngle`, `refVoltage`, `refCurrent`, `refAlt`, `refTempC`, `refBatRes`, `maxVoltage`, `battCapacityAh`, `propExpo` (= MOT_THST_EXPO), `refRotRate`, `hoverThrOut` (= MOT_THST_HOVER), `pwmMin`, `pwmMax`, `spin_min`, `spin_max`, `slew_max`, `disc_area`, `mdrag_coef`, `moment_inertia`, `num_motors`.
- Drag is derived from `refSpd` at `refAngle`.
- Motor dynamics are modelled only as a **slew limit** (`slew_max`); there is no first-order time constant (`SIM_Motor.cpp`).
- Template: `Tools/autotest/models/freestyle.json` (0.8 kg 5" quad).

---

## 8. Gazebo

- **Version for Ubuntu 24.04: Gazebo Harmonic (LTS).** The ardupilot_gazebo README says "Harmonic is recommended" and lists support for Garden, Harmonic (LTS), Ionic and **Jetty (LTS)**.
  - The plugin CI only builds Harmonic on ubuntu-22.04.
  - The README prerequisites still say "Ubuntu 22.04", and its apt instructions only cover Garden and Harmonic.
  - gazebosim docs: Harmonic binaries exist for Jammy **and Noble**; Jetty binaries are Noble-only; `index.yaml` marks jetty and harmonic `lts: true` and ionic `lts: false`, none EOL.
  - **Jetty with the plugin on 24.04 is UNCONFIRMED.** It would presumably need `libgz-sim10-dev` and `GZ_VERSION=jetty`.
  - The ArduPilot wiki Gazebo page is stale (it mentions only Garden and Harmonic on 20.04/22.04).
- **Install Harmonic** (gazebosim docs, `harmonic/install_ubuntu.md`):

```bash
sudo apt-get update && sudo apt-get install curl lsb-release gnupg
sudo curl https://packages.osrfoundation.org/gazebo.gpg --output /usr/share/keyrings/pkgs-osrf-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg] https://packages.osrfoundation.org/gazebo/ubuntu-stable $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/gazebo-stable.list > /dev/null
sudo apt-get update && sudo apt-get install gz-harmonic
gz sim -v4 -r shapes.sdf     # sanity check
```

- **Plugin** (README / wiki):

```bash
sudo apt install libgz-sim8-dev rapidjson-dev
sudo apt install libopencv-dev libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev gstreamer1.0-plugins-bad gstreamer1.0-libav gstreamer1.0-gl
git clone https://github.com/ArduPilot/ardupilot_gazebo ~/ardupilot_gazebo
export GZ_VERSION=harmonic
cd ~/ardupilot_gazebo && mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=RelWithDebInfo && make -j4
echo 'export GZ_SIM_SYSTEM_PLUGIN_PATH=$HOME/ardupilot_gazebo/build:${GZ_SIM_SYSTEM_PLUGIN_PATH}' >> ~/.bashrc
echo 'export GZ_SIM_RESOURCE_PATH=$HOME/ardupilot_gazebo/models:$HOME/ardupilot_gazebo/worlds:${GZ_SIM_RESOURCE_PATH}' >> ~/.bashrc
source ~/.bashrc
```

- **Run:**
  - Terminal 1: `gz sim -v4 -r iris_runway.sdf`
  - Terminal 2: `sim_vehicle.py -v ArduCopter -f gazebo-iris --model JSON --map --console`
  - Then `mode guided` / `arm throttle` / `takeoff 5`.
  - The frame must contain `gazebo-` and the model must be `JSON`. `gazebo-iris` loads `default_params/gazebo-iris.parm` (`Tools/autotest/pysim/vehicleinfo.py`).
  - The follow test from 7.3 works unchanged, because the target script talks to SITL's port 5762, not to Gazebo.
- **ROS 2 is not needed.** Wiki note: "the ArduPilot Gazebo plugin does not depend on ROS". The README offers rosdep only as an optional way to install dependencies.
- **Camera for vision tracking.**
  - `iris_runway.sdf` includes a 3-DOF gimbal with a zoomable camera and the `GstCameraPlugin` (H.264 RTP to `udp 127.0.0.1:5600`).
  - Find the topic with `gz topic -l | grep -i streaming`, then enable it:
    `gz topic -t /world/iris_runway/model/iris_with_gimbal/model/gimbal/link/pitch_link/sensor/camera/image/enable_streaming -m gz.msgs.Boolean -p "data: 1"`.
  - View with `gst-launch-1.0 -v udpsrc port=5600 caps='application/x-rtp, media=(string)video, clock-rate=(int)90000, encoding-name=(string)H264' ! rtph264depay ! avdec_h264 ! videoconvert ! autovideosink sync=false`, or in QGC (UDP h.264, `127.0.0.1:5600`).
  - Your Pi-side tracker can read the same RTP stream (OpenCV with GStreamer) and send `FOLLOW_TARGET` or Guided velocity commands back to SITL. A walking "person" actor model in the world was not researched (UNCONFIRMED).
- **Speed-up.** Add `<physics name="1ms" type="ignore"><max_step_size>0.001</max_step_size><real_time_factor>-1.0</real_time_factor></physics>` to the world and set `param set SIM_SPEEDUP 10`.

---

## 9. Logs for system identification

- **SystemID mode = 25** (`MODE_SYSTEMID_ENABLED` defaults to on with logging). Params (prefix `SID`):
  - `SID_AXIS`: 0 None (blocks entry), 1–3 Input Roll/Pitch/Yaw angle, 4–6 Recovery angle, 7–9 Rate, **10–12 Mixer Roll/Pitch/Yaw, 13 Mixer Thrust**, 14–15 Measured Lat/Long position, 16–17 Measured Lat/Long velocity, 18–19 Input Lat/Long velocity.
  - `SID_MAGNITUDE`, `SID_F_START_HZ`, `SID_F_STOP_HZ`, `SID_T_FADE_IN`, `SID_T_REC`, `SID_T_FADE_OUT`.
  - The magnitude can be tuned live with `TUNE = 58`.
  - The `SID` log message has the chirp plus raw IMU gyro and accel.
  - The wiki identification guide uses **Mixer axes 10–12** for plant models, does spectral analysis over several flights, and fits transfer functions. It assumes `MOT_THST_EXPO` is set correctly. That page's tooling is MATLAB-style; no ArduPilot Python SysID script was found in `Tools/` (UNCONFIRMED whether one exists elsewhere).
- **Thrust curve.**
  - `MOT_THST_EXPO` (0 linear to 1 quadratic; the wiki warns ESCs with built-in linearisation need about 0–0.2, not the default 0.65).
  - `MOT_SPIN_ARM`, `MOT_SPIN_MIN`, `MOT_SPIN_MAX`, `MOT_BAT_VOLT_MAX`.
  - `MOT_THST_HOVER` with `MOT_HOVER_LEARN` (automatic hover-throttle learning).
  - The wiki points to the **ArduPilot Thrust Expo WebTool** (`firmware.ardupilot.org/Tools/WebTools/ThrustExpo/`, not reachable from here) for fitting thrust-stand data.
- **Motor time constant.**
  - No ArduPilot parameter or tool for this was found.
  - Method: log ESC telemetry/RPM (`ESC` messages) or IMU during `SID_AXIS=13` (Mixer Thrust) chirps or step inputs, and fit a first-order lag offline in Python (pymavlink `DFReader` / `mavutil.mavlink_connection(file.bin)`, then numpy/scipy). This is my suggestion, not an ArduPilot doc.
- **Drag.** Fly at constant speed in still air and record lean angle. SITL's JSON model uses exactly `refSpd`/`refAngle` to derive the drag area (`SIM_Frame.cpp`). EKF3 also has drag fusion (`EK3_DRAG_*`; 4.7.2 fixed drag fusion with GPS yaw, PR #34027).
- **Tools.**
  - **MAVExplorer** (`MAVExplorer.py log.bin`; `graph ATT.Roll ATT.Pitch`; menu graphs; installed with MAVProxy).
  - UAV Log Viewer and the ArduPilot WebTools (referenced from the wiki `common-logs.rst`).
  - pymavlink in Python.
  - The old **LogAnalyzer is not in `Tools/` at 4.7.2**, so treat "Log Analyzer" as obsolete.

---

## Sources

All seen 2026-10-26 unless noted.

| URL | Supports |
|---|---|
| https://github.com/ArduPilot/ardupilot/tree/Copter-4.7.2 (git ls-remote + shallow clone, commit fb77356) | version, tags, branches, all source-derived facts |
| https://github.com/ArduPilot/ardupilot/blob/Copter-4.7.2/ArduCopter/ReleaseNotes.txt | 4.7.2 date, follow changes (PR 33891, 33937, 30101), 4.7 renames |
| https://github.com/ArduPilot/ardupilot/blob/Copter-4.7.2/libraries/AP_Follow/AP_Follow.cpp | FOLL_* params, messages, estimator, sysid rules, timeouts |
| https://github.com/ArduPilot/ardupilot/blob/Copter-4.7.2/ArduCopter/mode_follow.cpp | Follow control, speed limits, yaw, no avoidance |
| https://raw.githubusercontent.com/ArduPilot/ardupilot/Copter-4.6.3/ArduCopter/mode_follow.cpp | 4.6.3 Follow used FOLL_POS_P and AC_Avoid |
| https://raw.githubusercontent.com/ArduPilot/ardupilot/Copter-4.7.0/libraries/AP_Follow/AP_Follow.cpp | 4.7.0 still had `_automatic_sysid` |
| https://raw.githubusercontent.com/ArduPilot/ardupilot/master/libraries/AP_Follow/AP_Follow.cpp | master: 32-bit sysid conversion for 4.8 |
| …/libraries/GCS_MAVLink/GCS_Common.cpp, GCS.cpp, GCS.h | follow msg routing, MAV_CMD_DO_FOLLOW, MAV_SYSID/MAV_GCS_SYSID, 21196 force-disarm |
| …/ArduCopter/GCS_MAVLink_Copter.cpp, mode_guided.cpp, Parameters.cpp | SET_POSITION_TARGET handling, GUID_OPTIONS, failsafe params |
| …/ArduCopter/crash_check.cpp, ekf_check.cpp, events.cpp | crash, thrust loss, parachute, vibration, EKF, GPS-glitch logic and timings |
| …/libraries/AC_Avoidance/(AC_Avoid, AP_OAPathPlanner, AP_OABendyRuler, AP_OADatabase, AC_Avoidance_config.h) | AVOID_*, OA_*, AltHold avoidance compiled out |
| …/libraries/AC_WPNav/(AC_WPNav, AC_Loiter, AC_WPNav_OA).cpp, AC_AttitudeControl.cpp | WP_*, LOIT_*, ATC_ANGLE_MAX, OA in WPNav, Loiter avoidance |
| …/libraries/AC_Fence/AC_Fence.cpp, AP_BattMonitor_Params.cpp, AP_Parachute.cpp, RC_Channel.h/.cpp | fence, battery, chute, RC options 31/40/90/165 |
| …/libraries/AP_Proximity/AP_Proximity_Params.cpp, AP_RangeFinder/AP_RangeFinder_Params.cpp, AP_OpticalFlow.cpp, AP_NavEKF/AP_NavEKF_Source.cpp, AP_NavEKF3/AP_NavEKF3.cpp | PRX/RNGFND/FLOW/EK3 params |
| …/libraries/AP_OpenDroneID/*, Tools/ardupilotwaf/boards.py | DID_* params, ODID on in SITL |
| …/ArduCopter/mode_systemid.cpp, libraries/AP_Motors/AP_MotorsMulticopter.cpp | SID_*, MOT_* |
| …/Tools/autotest/arducopter.py (ModeFollow, ModeFollow_with_FOLLOW_TARGET), sim_vehicle.py, pysim/vehicleinfo.py, models/freestyle.json, libraries/SITL/SIM_Frame.cpp, AP_HAL_SITL/SITL_State.h | autotest, SITL options and ports, JSON frame model |
| …/Tools/environment_install/install-prereqs-ubuntu.sh | noble support, venv path |
| …/libraries/AP_Scripting/(applets/follow-target-send.md, crash-actions.md; examples/orbit_follow.lua, ahrs-source-gps-optflow.lua; docs/docs.lua) | Lua follow, orbit, source switching, crash actions (v4.8+) |
| https://github.com/ArduPilot/ardupilot_wiki (master 23c3dcd, 2026-10-25): copter/…/follow-mode.rst, ac2_followme.rst, crash_check.rst, motor-thrust-scaling.rst, systemid-model-development.rst; common/…/common-simple-object-avoidance.rst, common-oa-bendyruler.rst, common-ekf-sources.rst, common-optical-flow-sensor-setup.rst, common-systemid-mode-operation.rst; dev/…/sitl-with-gazebo.rst, setting-up-sitl-on-linux.rst, building-setup-linux.rst, using-sitl-for-ardupilot-testing.rst, opendroneid.rst, using-mavexplorer-for-log-analysis.rst | wiki statements quoted above (source of the ardupilot.org pages) |
| https://raw.githubusercontent.com/ArduPilot/MAVProxy/master/MAVProxy/modules/mavproxy_followtest.py | followtest behaviour (Guided waypoints) |
| https://raw.githubusercontent.com/ArduPilot/ardupilot_gazebo/main/README.md and .github/workflows/ubuntu-build.yml (main 80dc966) | supported Gazebo versions, Harmonic recommended, build and run commands, camera streaming |
| https://raw.githubusercontent.com/gazebosim/docs/master/harmonic/install_ubuntu.md, jetty/install_ubuntu.md, index.yaml | Harmonic on Noble, Jetty Noble-only, LTS flags, apt commands |
| pymavlink 2.4.50 / MAVProxy 1.8.75 (PyPI) | send-function signatures, FOLLOW=23 / SYSTEMID=25 mode names |
| **Not reachable:** ardupilot.org, firmware.ardupilot.org, discuss.ardupilot.org, gazebosim.org (rendered) | blocked by session network policy; the web-search budget was exhausted |
