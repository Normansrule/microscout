// STATUS: DRAFT - UNVERIFIED - requires human review at Gate G6 (simulation only)
// SPDX-License-Identifier: MIT
// three.js view of the Flight Lab. World NED (x fwd, y right, z down) -> three (x, -z, y), metres.

import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { RAYS } from "./world.js";
import { qrot } from "./math.js";

const P = (v) => new THREE.Vector3(v[0], -v[2], v[1]);

let _dot = null;
function dotTexture() {
  if (_dot) return _dot;
  const c = document.createElement("canvas"); c.width = c.height = 64;
  const g = c.getContext("2d");
  g.fillStyle = "#fff"; g.beginPath(); g.arc(32, 32, 30, 0, Math.PI * 2); g.fill();
  _dot = new THREE.CanvasTexture(c);
  return _dot;
}

export function cssVar(name, fallback) {
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return v || fallback;
}

export class LabView {
  constructor(canvas) {
    this.canvas = canvas;
    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: true });
    this.renderer.setPixelRatio(Math.min(2, window.devicePixelRatio || 1));
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(55, 1, 0.02, 200);
    this.camera.position.set(-8, 4, 6);
    this.controls = new OrbitControls(this.camera, canvas);
    this.top = new THREE.OrthographicCamera(-6, 6, 3, -3, 0.1, 100);   // plan view: no perspective lean on tall pillars
    this.top.up.set(0, 0, -1);                                          // +x (along the course) runs left to right
    this.top.position.set(0, 6, 0); this.top.lookAt(0, 0, 0);          // low enough that the fog leaves it alone
    this.controls.enableDamping = true;
    this.camMode = "chase";
    this.hemi = new THREE.HemisphereLight(0xffffff, 0x6b7480, 1.6);
    this.scene.add(this.hemi);
    const sun = new THREE.DirectionalLight(0xffffff, 1.8);
    sun.position.set(-1.2, 14, 1);        // nearly overhead: short shadows read as drop shadows, and the top view stays clear
    sun.castShadow = true;
    sun.shadow.mapSize.set(2048, 2048);
    Object.assign(sun.shadow.camera, { left: -10, right: 10, top: 10, bottom: -10, near: 1, far: 30 });
    this.scene.add(sun);
    this.courseGroup = new THREE.Group();
    this.scene.add(this.courseGroup);
    this.drones = [];
    this.ghostGroup = new THREE.Group();
    this.scene.add(this.ghostGroup);
    this.planGroup = new THREE.Group();
    this.scene.add(this.planGroup);
    this.model = null;
    this.applyTheme();
  }

  async loadModel(url) {
    try {
      const g = await new GLTFLoader().loadAsync(url);
      const m = g.scene;
      const box = new THREE.Box3().setFromObject(m);
      const size = box.getSize(new THREE.Vector3());
      const s = Math.max(size.x, size.y, size.z);
      m.scale.setScalar(s > 2 ? 0.001 : 1);           // GLB may be in mm or m
      const box2 = new THREE.Box3().setFromObject(m);
      const c = box2.getCenter(new THREE.Vector3());
      m.position.sub(c);                               // centre on the body origin
      m.traverse((o) => { if (o.isMesh) { o.castShadow = true; o.material = new THREE.MeshStandardMaterial({ color: o.material.color || 0x888888, roughness: 0.55, metalness: 0.1, transparent: o.material.transparent, opacity: o.material.opacity ?? 1 }); } });
      this.model = m;
    } catch (e) {
      console.warn("model not loaded, using a simple stand-in", e);
    }
  }

  applyTheme() {
    const bg = cssVar("--view-bg", "#dfe4e8");
    this.scene.background = new THREE.Color(bg);
    this.scene.fog = new THREE.Fog(bg, 18, 40);
    this.colors = {
      floor: cssVar("--view-floor", "#cfd6dc"), grid: cssVar("--view-grid", "#b6bfc7"), obstacle: cssVar("--view-obstacle", "#8f9aa6"),
      gate: cssVar("--accent", "#f28c28"), goal: cssVar("--ok", "#1baf7a"), ray: cssVar("--ray", "#e5484d"), wall: cssVar("--view-wall", "#9aa4ae"),
    };
  }

  /** Build meshes for a course. */
  setCourse(course) {
    this.course = course;
    const g = this.courseGroup;
    while (g.children.length) g.remove(g.children[0]);
    const [L, W, H] = course.room;
    const floor = new THREE.Mesh(new THREE.PlaneGeometry(L, W), new THREE.MeshStandardMaterial({ color: this.colors.floor, roughness: 0.95 }));
    floor.rotation.x = -Math.PI / 2;
    floor.receiveShadow = true;
    g.add(floor);
    const grid = new THREE.GridHelper(Math.max(L, W), Math.max(L, W), this.colors.grid, this.colors.grid);
    grid.position.y = 0.002;
    grid.material.transparent = true; grid.material.opacity = 0.55;
    g.add(grid);
    const room = new THREE.LineSegments(new THREE.EdgesGeometry(new THREE.BoxGeometry(L, H, W)), new THREE.LineBasicMaterial({ color: this.colors.wall, transparent: true, opacity: 0.6 }));
    room.position.y = H / 2;
    g.add(room);
    const obMat = new THREE.MeshStandardMaterial({ color: this.colors.obstacle, roughness: 0.8 });
    const gateMat = new THREE.MeshStandardMaterial({ color: this.colors.gate, roughness: 0.5, emissive: this.colors.gate, emissiveIntensity: 0.15 });
    for (const o of course.obstacles) {
      let mesh;
      if (o.type === "box") {
        const sx = o.max[0] - o.min[0], sy = o.max[2] - o.min[2], sz = o.max[1] - o.min[1];
        mesh = new THREE.Mesh(new THREE.BoxGeometry(sx, sy, sz), o.gate ? gateMat : obMat);
        mesh.position.copy(P([(o.min[0] + o.max[0]) / 2, (o.min[1] + o.max[1]) / 2, (o.min[2] + o.max[2]) / 2]));
      } else {
        mesh = new THREE.Mesh(new THREE.CylinderGeometry(o.r, o.r, o.h, 24), obMat);
        mesh.position.set(o.c[0], o.h / 2, o.c[1]);
      }
      mesh.castShadow = true; mesh.receiveShadow = true;
      g.add(mesh);
    }
    // waypoints and goal
    this.wpMeshes = [];
    const wps = course.waypoints || [];
    wps.forEach((w, i) => {
      const last = i === wps.length - 1 && !course.free;
      const m = new THREE.Mesh(new THREE.SphereGeometry(last ? 0.09 : 0.045, 16, 12), new THREE.MeshBasicMaterial({ color: last ? this.colors.goal : this.colors.gate, transparent: true, opacity: 0.85 }));
      m.position.copy(P(w));
      g.add(m);
      this.wpMeshes.push(m);
      if (last) {
        const ring = new THREE.Mesh(new THREE.TorusGeometry(0.45, 0.012, 8, 48), new THREE.MeshBasicMaterial({ color: this.colors.goal }));
        ring.position.copy(P(w)); ring.rotation.y = Math.PI / 2;
        g.add(ring);
      }
    });
    if (course.hold) this.wpMeshes.forEach((m) => m.scale.setScalar(1.6));
    this.clearGhosts();
    this.clearPlan();
  }

  setActiveWaypoint(i) {
    (this.wpMeshes || []).forEach((m, k) => { m.material.opacity = k === i ? 1 : k < i ? 0.18 : 0.6; m.scale.setScalar(k === i ? 1.4 : 1); });
  }

  /** Add a drone (model + trail + rays). color: CSS colour for the trail. */
  addDrone(color, opts = {}) {
    const rig = new THREE.Group();
    if (this.model) rig.add(this.model.clone(true));
    else {
      const body = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.03, 0.04), new THREE.MeshStandardMaterial({ color: 0xf28c28 }));
      rig.add(body);
      for (const [x, z] of [[-1, 1], [1, 1], [-1, -1], [1, -1]]) {
        const d = new THREE.Mesh(new THREE.TorusGeometry(0.028, 0.004, 6, 20), new THREE.MeshStandardMaterial({ color: 0x3b434d }));
        d.rotation.x = Math.PI / 2; d.position.set(x * 0.034, 0, z * 0.034);
        rig.add(d);
      }
    }
    if (opts.tint) rig.traverse((o) => { if (o.isMesh && o.material) { o.material = o.material.clone(); o.material.transparent = true; o.material.opacity = opts.tint; } });
    this.scene.add(rig);
    const N = 4000;
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(new Float32Array(N * 3), 3));
    geo.setDrawRange(0, 0);
    const trail = new THREE.Line(geo, new THREE.LineBasicMaterial({ color, transparent: true, opacity: 0.9 }));
    trail.frustumCulled = false;
    this.scene.add(trail);
    const rg = new THREE.BufferGeometry();
    rg.setAttribute("position", new THREE.BufferAttribute(new Float32Array(RAYS.length * 6), 3));
    rg.setAttribute("color", new THREE.BufferAttribute(new Float32Array(RAYS.length * 6), 3));
    const rays = new THREE.LineSegments(rg, new THREE.LineBasicMaterial({ vertexColors: true, transparent: true, opacity: 0.8 }));
    rays.frustumCulled = false;
    rays.visible = !!opts.rays;
    this.scene.add(rays);
    // A screen-sized dot and a stalk to the floor, so small drones stay easy to find in wide views.
    const mg = new THREE.BufferGeometry();
    mg.setAttribute("position", new THREE.BufferAttribute(new Float32Array(3), 3));
    const marker = new THREE.Points(mg, new THREE.PointsMaterial({ color, size: 11, sizeAttenuation: false, map: dotTexture(), transparent: true, alphaTest: 0.3, depthTest: false }));
    marker.frustumCulled = false; marker.renderOrder = 5;
    const sg = new THREE.BufferGeometry();
    sg.setAttribute("position", new THREE.BufferAttribute(new Float32Array(6), 3));
    const stalk = new THREE.Line(sg, new THREE.LineDashedMaterial({ color, dashSize: 0.05, gapSize: 0.05, transparent: true, opacity: 0.55 }));
    stalk.frustumCulled = false;
    this.scene.add(marker, stalk);
    const d = { rig, trail, rays, marker, stalk, n: 0, N, color, last: null };
    this.drones.push(d);
    return d;
  }

  removeDrones() {
    for (const d of this.drones) {
      this.scene.remove(d.rig, d.trail, d.rays, d.marker, d.stalk);
      for (const o of [d.trail, d.rays, d.marker, d.stalk]) { o.geometry.dispose(); o.material.dispose(); }
    }
    this.drones = [];
  }

  updateDrone(d, quad, tof = null) {
    d.rig.position.copy(P(quad.pos));
    d.rig.quaternion.set(quad.q[1], -quad.q[3], quad.q[2], quad.q[0]);
    const p = quad.pos;
    const wide = this.camMode !== "chase" || this.drones.length > 1;
    d.marker.visible = d.stalk.visible = wide;
    if (wide) {
      d.marker.geometry.attributes.position.array.set([p[0], -p[2] + 0.09, p[1]]);
      d.marker.geometry.attributes.position.needsUpdate = true;
      d.stalk.geometry.attributes.position.array.set([p[0], -p[2], p[1], p[0], 0, p[1]]);
      d.stalk.geometry.attributes.position.needsUpdate = true;
      d.stalk.computeLineDistances();
    }
    if (!d.last || Math.hypot(p[0] - d.last[0], p[1] - d.last[1], p[2] - d.last[2]) > 0.03) {
      const arr = d.trail.geometry.attributes.position.array;
      if (d.n >= d.N) { arr.copyWithin(0, 3); d.n = d.N - 1; }
      arr[d.n * 3] = p[0]; arr[d.n * 3 + 1] = -p[2]; arr[d.n * 3 + 2] = p[1];
      d.n++;
      d.trail.geometry.setDrawRange(0, d.n);
      d.trail.geometry.attributes.position.needsUpdate = true;
      d.trail.geometry.computeBoundingSphere();
      d.last = [...p];
    }
    if (tof && d.rays.visible) {
      const R = qrot(quad.q);
      const pos = d.rays.geometry.attributes.position.array, col = d.rays.geometry.attributes.color.array;
      const near = new THREE.Color(this.colors.ray), far = new THREE.Color(cssVar("--ray-far", "#7f8a95"));
      RAYS.forEach((r, i) => {
        const dw = [R[0] * r.d[0] + R[1] * r.d[1] + R[2] * r.d[2], R[3] * r.d[0] + R[4] * r.d[1] + R[5] * r.d[2], R[6] * r.d[0] + R[7] * r.d[1] + R[8] * r.d[2]];
        const e = [p[0] + dw[0] * tof[i], p[1] + dw[1] * tof[i], p[2] + dw[2] * tof[i]];
        pos.set([p[0], -p[2], p[1], e[0], -e[2], e[1]], i * 6);
        const c = far.clone().lerp(near, Math.max(0, 1 - tof[i] / 2));
        col.set([c.r, c.g, c.b, c.r, c.g, c.b], i * 6);
      });
      d.rays.geometry.attributes.position.needsUpdate = true;
      d.rays.geometry.attributes.color.needsUpdate = true;
    }
  }

  clearTrail(d) { d.n = 0; d.last = null; d.trail.geometry.setDrawRange(0, 0); }

  /** Faint paths of the RL population (ghosts) and the current policy's validation path. */
  setGhosts(trajs, color, opacity = 0.25, keep = 30) {
    for (const t of trajs) {
      if (!t || t.length < 2) continue;
      const geo = new THREE.BufferGeometry().setFromPoints(t.map(P));
      const line = new THREE.Line(geo, new THREE.LineBasicMaterial({ color, transparent: true, opacity }));
      this.ghostGroup.add(line);
    }
    while (this.ghostGroup.children.length > keep) {
      const o = this.ghostGroup.children[0];
      this.ghostGroup.remove(o); o.geometry.dispose(); o.material.dispose();
    }
    this.ghostGroup.children.forEach((o, i, a) => { o.material.opacity = opacity * (0.25 + 0.75 * (i / a.length)); });
  }
  clearGhosts() { while (this.ghostGroup.children.length) { const o = this.ghostGroup.children.pop(); o.geometry.dispose(); o.material.dispose(); } }

  /** Where a click on the canvas meets the floor, in NED metres [x, y]; null if it misses. */
  pickFloor(clientX, clientY) {
    const r = this.canvas.getBoundingClientRect();
    const ndc = new THREE.Vector2(((clientX - r.left) / r.width) * 2 - 1, -((clientY - r.top) / r.height) * 2 + 1);
    const ray = new THREE.Raycaster();
    ray.setFromCamera(ndc, this.camMode === "top" ? this.top : this.camera);
    const hit = new THREE.Vector3();
    if (!ray.ray.intersectPlane(new THREE.Plane(new THREE.Vector3(0, 1, 0), 0), hit)) return null;
    return [hit.x, hit.z];
  }

  /** Points the sensor-only MPC has seen with its ToF rays (its whole map). */
  setHits(points, color) {
    if (!this.hits) {
      const geo = new THREE.BufferGeometry();
      geo.setAttribute("position", new THREE.BufferAttribute(new Float32Array(3000 * 3), 3));
      this.hits = new THREE.Points(geo, new THREE.PointsMaterial({ color, size: 4, sizeAttenuation: false }));
      this.hits.frustumCulled = false;
      this.scene.add(this.hits);
    }
    if (points.length === this.hitsN) return;
    this.hitsN = points.length;
    this.hits.material.color.set(color);
    const a = this.hits.geometry.attributes.position.array;
    const n = Math.min(points.length, 3000);
    for (let i = 0; i < n; i++) { const p = points[i]; a[i * 3] = p[0]; a[i * 3 + 1] = -p[2]; a[i * 3 + 2] = p[1]; }
    this.hits.geometry.setDrawRange(0, n);
    this.hits.geometry.attributes.position.needsUpdate = true;
    this.hits.visible = true;
  }
  clearHits() { if (this.hits) { this.hits.visible = false; this.hitsN = -1; this.hits.geometry.setDrawRange(0, 0); } }

  /** MPC sample trajectories, drawn as one reusable line-segment buffer. */
  setPlan(trajs, color) {
    if (trajs === this.planSrc) return;
    this.planSrc = trajs;
    let n = 0; for (const t of trajs) n += Math.max(0, t.length - 1);
    if (!this.planLines || this.planCap < n) {
      this.clearPlan();
      this.planCap = Math.max(n, 2048);
      const geo = new THREE.BufferGeometry();
      geo.setAttribute("position", new THREE.BufferAttribute(new Float32Array(this.planCap * 6), 3));
      this.planLines = new THREE.LineSegments(geo, new THREE.LineBasicMaterial({ color, transparent: true, opacity: 0.35 }));
      this.planLines.frustumCulled = false;
      this.planGroup.add(this.planLines);
    }
    this.planLines.material.color.set(color);
    const a = this.planLines.geometry.attributes.position.array;
    let o = 0;
    for (const t of trajs) for (let i = 0; i + 1 < t.length; i++) {
      const p = t[i], q = t[i + 1];
      a[o++] = p[0]; a[o++] = -p[2]; a[o++] = p[1];
      a[o++] = q[0]; a[o++] = -q[2]; a[o++] = q[1];
    }
    this.planLines.geometry.setDrawRange(0, o / 3);
    this.planLines.geometry.attributes.position.needsUpdate = true;
    this.planLines.visible = true;
  }
  clearPlan() {
    if (this.planLines) { this.planGroup.remove(this.planLines); this.planLines.geometry.dispose(); this.planLines.material.dispose(); }
    this.planLines = null; this.planSrc = null;
  }

  resize() {
    const w = this.canvas.clientWidth, h = this.canvas.clientHeight;
    if (this.canvas.width !== Math.floor(w * this.renderer.getPixelRatio()) || this.canvas.height !== Math.floor(h * this.renderer.getPixelRatio())) {
      this.renderer.setSize(w, h, false);
      this.camera.aspect = w / h;
      this.camera.updateProjectionMatrix();
    }
  }

  render(follow = null, dt = 0.016) {
    this.resize();
    if (follow && this.camMode === "chase") {
      const p = P(follow.pos);
      const R = qrot(follow.q);
      const yaw = Math.atan2(R[3], R[0]);
      // A few drone-lengths behind and above; look a little ahead so the course is in view.
      const fx = Math.cos(yaw), fz = Math.sin(yaw);
      const want = p.clone().add(new THREE.Vector3(-fx * 0.85, 0.38, -fz * 0.85));
      const look = p.clone().add(new THREE.Vector3(fx * 0.6, 0, fz * 0.6));
      const k = 1 - Math.exp(-dt * 7);
      this.camera.position.lerp(want, k);
      this.controls.target.lerp(look, Math.min(1, k * 2));
      this.camera.lookAt(this.controls.target);
    } else if (this.camMode === "top" && this.course) {
      const [L, W] = this.course.room, a = this.canvas.clientWidth / Math.max(1, this.canvas.clientHeight);
      const hh = Math.max(W, L / a) / 2 * 1.06;                         // half-height that fits the whole room
      if (this.top.top !== hh || this.top.right !== hh * a) {
        Object.assign(this.top, { left: -hh * a, right: hh * a, top: hh, bottom: -hh });
        this.top.updateProjectionMatrix();
      }
      this.controls.target.set(0, 0, 0);
    } else {
      this.controls.update();
    }
    this.renderer.render(this.scene, this.camMode === "top" && this.course ? this.top : this.camera);
  }

  setCamera(mode) {
    this.camMode = mode;
    this.controls.enabled = mode === "orbit";
    if (mode === "orbit" && this.course) {
      const [L, , H] = this.course.room;
      this.camera.position.set(-L * 0.55, H * 1.6, L * 0.45);
      this.controls.target.set(0, 0.8, 0);
    }
  }
}
