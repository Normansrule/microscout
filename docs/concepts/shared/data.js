// SPDX-License-Identifier: MIT
// One SYNTHETIC follow-me snapshot that every concept mockup renders, so the three concepts compare like for like.
// Nothing here was measured: Wisp has not flown. Positions are metres in a local frame (x east, y north).

const heading = 62;                     // deg, the walker's direction of travel
const rad = (d) => (d * Math.PI) / 180;
const fwd = [Math.sin(rad(heading)), Math.cos(rad(heading))];

// the walker's path along a cliff-top trail (last 40 s, one point per second), ending at the origin
const walker = Array.from({ length: 41 }, (_, i) => {
  const t = i - 40;                                     // s, 0 = now
  const s = 1.4 * t;                                    // 1.4 m/s walking
  const bend = 0.035 * s * s * Math.sign(s) * 0.15;     // gentle curve
  return [s * fwd[0] - bend * fwd[1], s * fwd[1] + bend * fwd[0]];
});

const follow = { distance: 4.0, height: 2.5 };          // m behind, m above the walker
const behind = (p) => [p[0] - follow.distance * fwd[0], p[1] - follow.distance * fwd[1]];

// the trail continues ahead of the walker; the predicted position 3 s ahead uses the filtered target velocity
const trailAhead = Array.from({ length: 31 }, (_, i) => [i * fwd[0], i * fwd[1]]);
const predicted = [3 * 1.4 * fwd[0], 3 * 1.4 * fwd[1]];

export const SNAPSHOT = {
  trailAhead,
  predicted,
  synthetic: true,
  mode: "Follow",
  modes: ["Follow", "Orbit", "Lead", "Side", "Dolly"],
  follow,
  target: { source: "Phone GPS", confidence: 0.92, visionReady: true, speed: 1.4, heading },
  drone: {
    pos: behind([0, 0]),
    trail: walker.map(behind),
    heightAgl: 2.5,
    speed: 1.4,
    yawToTarget: heading,
  },
  walker,
  obstacles: [
    { kind: "palm", pos: [3.6, -1.2], r: 0.5 },
    { kind: "bench", pos: [-6.5, -5.8], r: 0.9 },
    { kind: "lamp post", pos: [-12.0, -3.0], r: 0.15 },
  ],
  tof: { front: 3.2, left: 4.0, right: 2.6, down: 2.5 },   // m; 4.0 = nothing within range
  geofence: { radius: 60, ceiling: 30.5 },                 // m (100 ft ceiling)
  airspace: {
    // LAANC facility-map ceilings in feet. EXAMPLE values, not the real map. Real squares are 30 arc-seconds
    // (about 0.9 by 0.8 km here), so one square covers the whole view; a boundary to a lower square runs offshore.
    here: 200,
    authorized: 100,    // ft, the authorization in hand for this flight (at or below the square's ceiling)
    neighbour: { ceiling: 50, edge: [[-120, 17], [120, 17]] },
  },
  battery: { cells: 4, voltage: 15.12, percent: 61, minutesLeft: 6, current: 7.8 },
  link: { telemetryMs: 84, rcHz: 150, rssi: -78 },
  gps: { sats: 16, hdop: 0.7 },
  camera: { recording: true, elapsed: 222, resolution: "2.7K 60" },   // s
};

// Facts shown twice are one variable: check the ones that must agree.
console.assert(Math.abs(Math.hypot(...SNAPSHOT.drone.pos) - follow.distance) < 1e-9, "drone is not at the follow distance");
console.assert(SNAPSHOT.drone.heightAgl === follow.height, "height shown twice disagrees");
console.assert(SNAPSHOT.airspace.authorized <= SNAPSHOT.airspace.here, "authorization above the square's ceiling");

export const fmtTime = (s) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;
