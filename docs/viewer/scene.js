// STATUS: DRAFT - UNVERIFIED - requires human review at Gate G5 (concept model, pre-G5)
// SPDX-License-Identifier: MIT
// Shared three.js scene for the MicroScout concept model: used by the GitHub Pages
// viewer (docs/index.html) and by the headless renderer (tools/viz/render3d).
// The model is a CONCEPT: frame and canopy are parametric CAD, everything else is an envelope.
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";

const EXPLODE = {   // mm offsets along "up" for the exploded view
  canopy_tpu: 20, battery_2s_550: 40, battery_strap: 40, fc_board: 11, esp32_module: 11, camera: 11,
  tof_front_8x8: 11, led_: 11, tof_: 11, esc_board: 5, sensor_pod_down: -8, prop_: 9, motor_: 3,
};
const FINISH = {   // name prefix -> material tweaks
  frame_pa11: { roughness: 0.62, metalness: 0.0 },
  canopy_tpu: { roughness: 0.42, metalness: 0.0, clearcoat: 0.25 },
  battery_strap: { roughness: 0.5, metalness: 0.0 },
  fc_board: { roughness: 0.5, metalness: 0.1 }, esc_board: { roughness: 0.5, metalness: 0.1 },
  sensor_pod_down: { roughness: 0.5, metalness: 0.1 }, tof_: { roughness: 0.5, metalness: 0.1 },
  esp32_module: { roughness: 0.3, metalness: 0.85 },
  motor_: { roughness: 0.28, metalness: 0.9 },
  prop_: { roughness: 0.2, metalness: 0.0, transparent: true, opacity: 0.82 },
  battery_2s_550: { roughness: 0.55, metalness: 0.15 },
  camera: { roughness: 0.25, metalness: 0.4 },
  led_: { roughness: 0.2, metalness: 0.0, emissive: 0x9fd4ff, emissiveIntensity: 1.6 },
};

function lookup(table, name) {
  for (const k of Object.keys(table)) if (name.startsWith(k)) return table[k];
  return null;
}

export async function createViewer(canvas, opts = {}) {
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: !!opts.transparent, preserveDrawingBuffer: true });
  renderer.setPixelRatio(opts.pixelRatio || Math.min(window.devicePixelRatio, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = opts.exposure || 1.0;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;

  const scene = new THREE.Scene();
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  if (!opts.transparent) scene.background = new THREE.Color(opts.background || 0xeef0f2);

  const camera = new THREE.PerspectiveCamera(opts.fov || 30, 1, 1, 5000);
  const key = new THREE.DirectionalLight(0xffffff, 2.2);
  key.position.set(120, 260, 160);
  key.castShadow = true;
  key.shadow.mapSize.set(2048, 2048);
  Object.assign(key.shadow.camera, { left: -160, right: 160, top: 160, bottom: -160, near: 10, far: 800 });
  key.shadow.bias = -0.0004;
  scene.add(key);
  scene.add(new THREE.HemisphereLight(0xffffff, 0x8899aa, 0.6));

  const ground = new THREE.Mesh(new THREE.PlaneGeometry(4000, 4000), new THREE.ShadowMaterial({ opacity: 0.18 }));
  ground.rotation.x = -Math.PI / 2;
  ground.receiveShadow = true;
  scene.add(ground);

  const gltf = await new GLTFLoader().loadAsync(opts.glbUrl);
  const model = gltf.scene;
  // normalise units to millimetres (the writer may export metres)
  const box0 = new THREE.Box3().setFromObject(model);
  const size0 = box0.getSize(new THREE.Vector3());
  if (Math.max(size0.x, size0.y, size0.z) < 2) model.scale.setScalar(1000);
  const rig = new THREE.Group();          // pose target: origin at the frame centre
  rig.add(model);
  scene.add(rig);

  const parts = {};
  model.traverse((o) => {
    if (o.isMesh) {
      o.castShadow = true;
      o.receiveShadow = true;
      let n = o, name = "";
      while (n && !name) { if (n.name && !n.name.startsWith("mesh") && n.name !== "Scene") name = n.name; n = n.parent; }
      const fin = lookup(FINISH, name);
      const base = o.material;
      const mat = new THREE.MeshPhysicalMaterial({ color: base.color ? base.color.clone() : 0x888888, side: THREE.DoubleSide });
      if (fin) Object.assign(mat, fin, { emissive: new THREE.Color(fin.emissive || 0x000000) });
      o.material = mat;
      (parts[name] = parts[name] || []).push(o);
    }
  });
  model.updateMatrixWorld(true);
  const homes = new Map();
  for (const [name, meshes] of Object.entries(parts)) for (const m of meshes) homes.set(m, m.position.clone());

  const box = new THREE.Box3().setFromObject(rig);
  const lift = -box.min.y;                 // stand on the ground plane
  rig.position.y = lift;
  const center = box.getCenter(new THREE.Vector3());

  function resize(w, h) {
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  }

  function setExplode(f) {
    rig.updateMatrixWorld(true);
    for (const [name, meshes] of Object.entries(parts)) {
      const d = lookup(EXPLODE, name) || 0;
      for (const m of meshes) {
        const h = homes.get(m);
        if (!d || !f) { m.position.copy(h); continue; }
        // move along world "up" by d*f millimetres, expressed in the parent's local frame
        const wp = m.parent.localToWorld(h.clone());
        wp.y += d * f * rig.scale.y;
        m.position.copy(m.parent.worldToLocal(wp));
      }
    }
  }

  const propAxis = {};
  function spinProps(angle) {
    for (const [name, meshes] of Object.entries(parts)) {
      if (!name.startsWith("prop_")) continue;
      const k = +name.split("_")[1];
      const dir = (k === 1 || k === 4) ? 1 : -1;   // FL/RR clockwise per the CAD placeholder
      for (const m of meshes) {
        if (!propAxis[m.uuid]) {
          m.geometry.computeBoundingBox();
          const c = m.geometry.boundingBox.getCenter(new THREE.Vector3());
          m.geometry.translate(-c.x, 0, -c.z);
          m.position.x += c.x; m.position.z += c.z;
          homes.set(m, m.position.clone());
          propAxis[m.uuid] = true;
        }
        m.rotation.y = -dir * angle;
      }
    }
  }

  function setPoseNED(p, q, scaleMm = 1000, origin = [0, 0, 0]) {
    // NED (x fwd, y right, z down) -> three (x fwd, y up, z right)
    rig.position.set(origin[0] + p[0] * scaleMm, origin[1] - p[2] * scaleMm + lift, origin[2] + p[1] * scaleMm);
    const qn = new THREE.Quaternion(q[1], -q[3], q[2], q[0]);   // basis change of the FRD body quaternion
    rig.quaternion.copy(qn);
  }

  function frame(view, dist) {
    const d = dist || 330;
    const c = center.clone(); c.y += lift;
    const V = {
      hero: [0.95, 0.62, 0.78], front: [1, 0.18, 0.0001], side: [0.0001, 0.18, 1], top: [0.0001, 1, 0.0001],
      under: [0.6, -0.55, 0.7], rear: [-0.9, 0.5, -0.6], low: [1.0, 0.18, 0.55],
    }[view] || view;
    const v = new THREE.Vector3(...V).normalize().multiplyScalar(d);
    camera.position.copy(c).add(v);
    if (view === "top") camera.up.set(1, 0, 0); else camera.up.set(0, 1, 0);
    camera.lookAt(c);
    ground.visible = view !== "under";
  }

  return { THREE, renderer, scene, camera, rig, model, parts, resize, setExplode, spinProps, setPoseNED, frame, center, lift,
    render: () => renderer.render(scene, camera) };
}
