/* CVSF Process Simulator – 3D apparatus view (three.js r147).
 * Geometry from the Fusion 360 model (cm), scaled to the design inputs; motion from the model results.
 * Scene axes: x = apparatus axis (feed left -> discharge right), y = up, z = towards the viewer. 1 unit = 1 cm.
 */
(function () {
  "use strict";
  const D = window.CVSF_DATA;
  const G = D.geom, OP = D.op, PR = D.prof, SC = D.screw;
  const wrap = document.getElementById("wrap");
  const canvas = document.getElementById("c");

  // ------------------------------------------------------------------ renderer, scene, camera
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, preserveDrawingBuffer: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.outputEncoding = THREE.sRGBEncoding;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.05;
  renderer.localClippingEnabled = true;
  const scene = new THREE.Scene();
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new THREE.RoomEnvironment(), 0.04).texture;

  const xMin = -11, xMax = G.x_end + G.end_piece + 1.5;
  const xC = 0.5 * (xMin + xMax);
  const camera = new THREE.PerspectiveCamera(30, 2, 0.1, 2000);
  const controls = new THREE.OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true; controls.dampingFactor = 0.08;
  controls.minDistance = 4; controls.maxDistance = 300;

  scene.add(new THREE.HemisphereLight(0xdfeeff, 0x223344, 0.55));
  const key = new THREE.DirectionalLight(0xffffff, 1.1); key.position.set(-20, 40, 35); scene.add(key);
  const rim = new THREE.DirectionalLight(0x9cc8ff, 0.6); rim.position.set(30, 10, -40); scene.add(rim);

  const grid = new THREE.GridHelper(Math.ceil((xMax - xMin + 30) / 10) * 10, Math.ceil((xMax - xMin + 30) / 10) * 2,
    0x35506a, 0x223447);
  grid.position.set(xC, -6.19, 0); grid.material.transparent = true; grid.material.opacity = 0.22; scene.add(grid);

  // ------------------------------------------------------------------ materials
  const cut = [new THREE.Plane(new THREE.Vector3(0, 0, -1), 0)];
  const clipMats = [];
  function clipable(m) { clipMats.push(m); return m; }
  const glassMat = clipable(new THREE.MeshPhysicalMaterial({
    color: 0xd6ecff, metalness: 0.0, roughness: 0.04, transparent: true, opacity: 0.16, clearcoat: 1.0,
    clearcoatRoughness: 0.03, envMapIntensity: 2.2, side: THREE.DoubleSide, depthWrite: false,
    specularIntensity: 1.0, ior: 1.47 }));
  const glassInner = clipable(glassMat.clone()); glassInner.opacity = 0.11;
  const edgeMat = clipable(new THREE.LineBasicMaterial({ color: 0xbfe3ff, transparent: true, opacity: 0.75 }));
  const threadMat = clipable(new THREE.MeshStandardMaterial({ color: 0xf2f6fa, roughness: 0.55, transparent: true,
    opacity: 0.6, depthWrite: false }));
  const couplingMat = clipable(new THREE.MeshStandardMaterial({ color: 0x2c353e, metalness: 0.55, roughness: 0.45, envMapIntensity: 0.45 }));
  const ptfeMat = new THREE.MeshStandardMaterial({ color: 0xf7f7f3, roughness: 0.5, metalness: 0.0, envMapIntensity: 0.8 });
  const driveMat = new THREE.MeshStandardMaterial({ color: 0x1c2228, metalness: 0.3, roughness: 0.6, envMapIntensity: 0.12 });
  const hoseMat = new THREE.MeshStandardMaterial({ color: 0x1d242b, roughness: 0.7 });

  function noiseTexture(base, spread) {
    const c = document.createElement("canvas"); c.width = c.height = 128;
    const g = c.getContext("2d"); g.fillStyle = base; g.fillRect(0, 0, 128, 128);
    for (let i = 0; i < 2600; i++) {
      const v = Math.floor(Math.random() * spread);
      g.fillStyle = `rgba(${120 + v},${115 + v},${100 + v},${0.25 + Math.random() * 0.35})`;
      g.fillRect(Math.random() * 128, Math.random() * 128, 1 + Math.random() * 2, 1 + Math.random() * 2);
    }
    const t = new THREE.CanvasTexture(c); t.wrapS = t.wrapT = THREE.RepeatWrapping; return t;
  }
  const fritTex = noiseTexture("#d8d2c4", 110); fritTex.repeat.set(6, 2);
  const fritMat = new THREE.MeshStandardMaterial({ map: fritTex, color: 0xf1ece2, roughness: 0.95, side: THREE.DoubleSide,
    transparent: true, opacity: 0.42, depthWrite: false });   // sintered borosilicate: translucent

  // ------------------------------------------------------------------ helpers
  function latheX(profile, mat, x0, segs) {
    // profile: [[r, x], ...] along the axis; lathe around Y then rotate Y -> +X
    const pts = profile.map(p => new THREE.Vector2(p[0], p[1]));
    const geo = new THREE.LatheGeometry(pts, segs || 72);
    const m = new THREE.Mesh(geo, mat); m.rotation.z = -Math.PI / 2; m.position.x = x0;
    return m;
  }
  function edges(mesh, ang) {
    const e = new THREE.LineSegments(new THREE.EdgesGeometry(mesh.geometry, ang || 25), edgeMat);
    e.rotation.copy(mesh.rotation); e.position.copy(mesh.position); return e;
  }
  function nozzle(x, y0, y1, r, rin, thread, mat) {
    const g = new THREE.Group();
    const geo = new THREE.LatheGeometry([new THREE.Vector2(rin, y0), new THREE.Vector2(r, y0),
      new THREE.Vector2(r, y1), new THREE.Vector2(rin, y1), new THREE.Vector2(rin, y0)], 40);
    const m = new THREE.Mesh(geo, mat || glassMat); g.add(m);
    const e = new THREE.LineSegments(new THREE.EdgesGeometry(geo, 30), edgeMat); g.add(e);
    if (thread) {                                     // GL thread rings at the free end of the nozzle
      const up = y1 > y0;
      for (let k = 0; k < 5; k++) {
        const t = new THREE.Mesh(new THREE.TorusGeometry(r + 0.02, 0.035, 6, 32), threadMat);
        t.rotation.x = Math.PI / 2; t.position.y = up ? y1 - 0.08 - k * 0.13 : y1 + 0.08 + k * 0.13;
        g.add(t);
      }
    }
    g.position.x = x; return g;
  }
  function label(text, sub, x, y, z, scale, color) {
    const c = document.createElement("canvas"); const w = 512, h = sub ? 150 : 96; c.width = w; c.height = h;
    const g = c.getContext("2d");
    g.font = "600 52px Segoe UI, Arial"; g.fillStyle = color || "#ffffff"; g.textAlign = "center"; g.textBaseline = "top";
    g.shadowColor = "rgba(0,0,0,0.8)"; g.shadowBlur = 8;
    g.fillText(text, w / 2, 8);
    if (sub) { g.font = "400 34px Segoe UI, Arial"; g.fillStyle = "#bcd3ea"; g.fillText(sub, w / 2, 78); }
    const t = new THREE.CanvasTexture(c); t.encoding = THREE.sRGBEncoding;
    const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: t, transparent: true, depthTest: false, sizeAttenuation: false }));
    const sc = 0.0155 * (scale || 6); s.scale.set(sc, sc * h / w, 1); s.position.set(x, y, z); s.renderOrder = 10;
    scene.add(s); return s;
  }

  const Rb = G.Rb, Rt = G.r_tube;
  const app = new THREE.Group(); scene.add(app);

  // ------------------------------------------------------------------ glass module
  function glassModule(x0, L, kind) {
    const s = G.shoulder, rj = G.r_jacket, rji = G.r_jacket_in, rn = G.r_neck;
    const jacket = latheX([[rn, 0], [rj, s], [rj, L - s], [rn, L], [rn - 0.1, L], [rji, L - s - 0.05],
      [rji, s + 0.05], [rn - 0.1, 0], [rn, 0]], glassMat, x0);
    app.add(jacket); app.add(edges(jacket, 20));
    const tube = latheX([[Rb, 0], [Rt, 0], [Rt, L], [Rb, L], [Rb, 0]], glassInner, x0, 64);
    app.add(tube);
    // end faces (necks) as rings
    for (const xx of [x0, x0 + L]) {
      const ring = new THREE.Mesh(new THREE.RingGeometry(Rt, rn, 48), glassMat);
      ring.rotation.y = Math.PI / 2; ring.position.x = xx; app.add(ring);
    }
  }
  function frit(x0, L) {
    const half = Math.min(0.5 * G.b / Rb, 1.2);          // b = developed width of the frit (arc length)
    for (const r of [Rb + 0.004, Rb + 0.22]) {
      const geo = new THREE.CylinderGeometry(r, r, L, 40, 1, true, Math.PI / 2 - half, 2 * half);
      const m = new THREE.Mesh(geo, fritMat); m.rotation.z = -Math.PI / 2; m.position.x = x0 + L / 2; app.add(m);
    }
  }
  function coupling(x0, L) {
    if (L <= 0.05) return;
    const m = latheX([[Rt, 0], [G.r_coupling, 0], [G.r_coupling, 0.42 * L], [G.r_coupling - 0.12, 0.5 * L],
      [G.r_coupling, 0.58 * L], [G.r_coupling, L], [Rt, L], [Rt, 0]], couplingMat, x0, 48);
    app.add(m);
  }

  // drive + lead-in coupling
  const drive = new THREE.Mesh(new THREE.BoxGeometry(6.5, 6.0, 6.0), driveMat);
  drive.position.set(-8.0, 0, 0); app.add(drive);
  const flange = new THREE.Mesh(new THREE.CylinderGeometry(2.4, 2.4, 0.8, 40), couplingMat);
  flange.rotation.z = Math.PI / 2; flange.position.set(-4.4, 0, 0); app.add(flange);
  coupling(-0.2, G.lead_in + 0.2);
  label("Drive", "screw motor", -8.0, 4.4, 0, 5.5);

  // modules
  const mods = D.modules;
  const nozzleX = [];      // remember nozzle positions per module for the emitters
  mods.forEach((m, i) => {
    glassModule(m.x0, G.glass, m.type);
    frit(m.frit0, G.Lf);
    const fc = 0.5 * (m.frit0 + m.frit1);
    const tops = m.type === "F" ? [fc, fc + 2.4] : m.type === "W" ? [m.frit0 + 0.6, fc] : [m.frit0 + 0.6, fc, fc + 2.4];
    const nz = { top: tops, bottom: fc };
    tops.forEach(x => app.add(nozzle(x, Rt - 0.02, G.nozzle_top, G.r_nozzle, G.r_nozzle_in, true)));
    app.add(nozzle(fc, -G.r_jacket_in + 0.02, G.nozzle_bottom, G.r_nozzle, G.r_nozzle_in, true));
    // vacuum hose stub
    const hose = new THREE.Mesh(new THREE.CylinderGeometry(0.42, 0.42, 1.6, 20), hoseMat);
    hose.position.set(fc, G.nozzle_bottom - 0.8, 0); app.add(hose);
    if (m.type === "F") {
      nz.feed = m.frit0 + 0.04;
      app.add(nozzle(nz.feed, Rt - 0.02, G.nozzle_top - 0.1, 0.72, 0.52, true));
      const tubeIn = new THREE.Mesh(new THREE.CylinderGeometry(0.25, 0.25, 3.0, 16), ptfeMat);
      tubeIn.position.set(nz.feed, G.nozzle_top + 1.2, 0); app.add(tubeIn);
    }
    if (m.type === "W") {
      tops.forEach(x => { const t = new THREE.Mesh(new THREE.CylinderGeometry(0.16, 0.16, 2.4, 12), ptfeMat);
        t.position.set(x, G.nozzle_top + 0.7, 0); app.add(t); });
    }
    nozzleX.push(nz);
    const names = { F: ["filtration · deliquoring", "#ffffff"], W: ["washing", "#ffffff"], D: ["deliquoring", "#ffffff"] };
    let sub = names[m.type][0];
    if (m.type === "W") sub = (m.name === "W1") ? "wash liquid 1: EtOH/water (red)" : "wash liquid 2: ethanol";
    label(m.name, sub, m.x0 + G.glass / 2, 5.6, 0, 7.5);
    if (i < mods.length - 1) coupling(m.x0 + G.glass, G.coupling);
  });
  // coupling to end piece + end piece
  coupling(mods[mods.length - 1].x0 + G.glass, G.coupling);
  (function endPiece() {
    const x0 = G.x_end, L = G.end_piece;
    glassModule(x0, L, "E");
    app.add(nozzle(G.x_dis, -G.r_jacket_in + 0.02, G.nozzle_bottom - 0.4, 1.05, 0.9, false));
    app.add(nozzle(G.x_dis, Rt - 0.02, G.nozzle_top, G.r_nozzle, G.r_nozzle_in, true));
    const cap = new THREE.Mesh(new THREE.CylinderGeometry(G.r_neck + 0.25, G.r_neck + 0.25, 0.5, 40), couplingMat);
    cap.rotation.z = Math.PI / 2; cap.position.x = x0 + L + 0.25; app.add(cap);
    label("Discharge", "filter cake → product", G.x_dis, -5.3, 0, 7.0);
  })();
  label("Feed", "suspension", mods[0].frit0 - 2.2, G.nozzle_top + 3.2, 0, 5.5, "#9fd0ff");

  // ------------------------------------------------------------------ screw (PTFE)
  const screw = new THREE.Group(); app.add(screw);
  (function buildScrew() {
    const x0 = SC.x0, x1 = SC.x1, rc = SC.r_core, ro = SC.r_out - 0.015, P = SC.P, w = Math.max(SC.w, 0.06);
    const core = new THREE.Mesh(new THREE.CylinderGeometry(rc, rc, x1 - x0, 48, 1), ptfeMat);
    core.rotation.z = -Math.PI / 2; core.position.x = 0.5 * (x0 + x1); screw.add(core);
    const shaft = new THREE.Mesh(new THREE.CylinderGeometry(0.62, 0.62, x0 + 4.4, 24), ptfeMat);
    shaft.rotation.z = -Math.PI / 2; shaft.position.x = 0.5 * (x0 - 4.4); screw.add(shaft);
    const tip = new THREE.Mesh(new THREE.ConeGeometry(rc, 0.8, 32), ptfeMat);
    tip.rotation.z = -Math.PI / 2; tip.position.x = x1 + 0.4; screw.add(tip);
    const turns = (x1 - x0) / P, segs = Math.ceil(turns * 64);
    for (let k = 0; k < Math.max(1, SC.N); k++) {
      const phase = 2 * Math.PI * k / Math.max(1, SC.N);
      // four faces, each with its own vertices (crisp edges): [r_a, dx_a, r_b, dx_b]
      const faces = [[rc, -w / 2, ro, -w / 2], [ro, -w / 2, ro, w / 2], [ro, w / 2, rc, w / 2], [rc, w / 2, rc, -w / 2]];
      const pos = [], idx = [];
      faces.forEach((f, fi) => {
        const base = pos.length / 3;
        for (let i = 0; i <= segs; i++) {
          const xs = x0 + (x1 - x0) * i / segs;
          const th = phase + 2 * Math.PI * (xs - x0) / P;           // right-handed helix about +x
          const c = Math.cos(th), s = Math.sin(th);
          pos.push(xs + f[1], f[0] * c, f[0] * s, xs + f[3], f[2] * c, f[2] * s);
        }
        for (let i = 0; i < segs; i++) {
          const a = base + 2 * i, b = a + 1, cc = a + 2, d = a + 3;
          idx.push(a, cc, b, b, cc, d);
        }
      });
      const geo = new THREE.BufferGeometry();
      geo.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3)); geo.setIndex(idx);
      geo.computeVertexNormals();
      const mat = ptfeMat.clone(); mat.side = THREE.DoubleSide;
      screw.add(new THREE.Mesh(geo, mat));
    }
  })();

  // ------------------------------------------------------------------ profiles (z grid 0.05 cm)
  const zg0 = PR.z[0], dzg = PR.z[1] - PR.z[0], nZ = PR.z.length;
  function iz(z) { let i = Math.round((z - zg0) / dzg); return i < 0 ? 0 : (i >= nZ ? nZ - 1 : i); }
  const COL_ML = new THREE.Color(0x1f63e0).convertSRGBToLinear(), COL_W1 = new THREE.Color(0xe0262b).convertSRGBToLinear(),
    COL_E = new THREE.Color(0xf4f3ee).convertSRGBToLinear();
  const lut = new Float32Array(nZ * 3);
  for (let i = 0; i < nZ; i++) {
    const ml = PR.ML[i], rw = PR.RW[i], e = Math.max(0, 1 - ml - rw);
    lut[3 * i] = ml * COL_ML.r + rw * COL_W1.r + e * COL_E.r;
    lut[3 * i + 1] = ml * COL_ML.g + rw * COL_W1.g + e * COL_E.g;
    lut[3 * i + 2] = ml * COL_ML.b + rw * COL_W1.b + e * COL_E.b;
  }
  const z0 = G.z0;            // scene x of z = 0
  const xFeed = (nozzleX[0].feed || mods[0].frit0);
  const xDis = G.x_dis;
  const hcEnd = Math.max(OP.hc, 0.02);

  // segment mesh along x between xa and xb with height function hf(x) above the bore bottom
  function segmentMesh(xa, xb, hf, colorFn, mat, inset) {
    const nx = Math.max(2, Math.ceil((xb - xa) / 0.1)), na = 22;
    const pos = [], col = [], idx = [];
    const R = Rb - (inset || 0);
    for (let i = 0; i <= nx; i++) {
      const x = xa + (xb - xa) * i / nx;
      const h = Math.max(1e-3, Math.min(hf(x), 2 * R - 1e-3));
      const a = Math.acos((R - h) / R);                       // half angle of the segment
      const c = colorFn ? colorFn(x) : null;
      for (let j = 0; j <= na; j++) {                          // arc (bottom) + chord (top) as closed loop
        const t = j < na ? -a + 2 * a * j / (na - 1) : -a;
        const y = -R * Math.cos(t), zz = R * Math.sin(t);
        pos.push(x, y, zz);
        if (c) col.push(c[0], c[1], c[2]);
      }
    }
    const nv = na + 1;
    for (let i = 0; i < nx; i++) for (let j = 0; j < na; j++) {
      const a = i * nv + j, b = a + 1, c2 = a + nv, d = c2 + 1;
      idx.push(a, c2, b, b, c2, d);
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
    if (colorFn) geo.setAttribute("color", new THREE.Float32BufferAttribute(col, 3));
    geo.setIndex(idx); geo.computeVertexNormals();
    const m = new THREE.Mesh(geo, mat); app.add(m); return m;
  }
  const zOf = x => x - z0;
  const cakeAt = x => PR.cake[iz(zOf(x))];
  const topAt = x => PR.top[iz(zOf(x))];
  const rP = D.particle.r_vis;

  // suspension (mother liquor) from the feed to z_S1
  const zS1x = z0 + Math.min(OP.zS1, G.x_end - z0);
  const liqMat = new THREE.MeshPhysicalMaterial({ color: 0x1f6bff, transparent: true, opacity: 0.5, roughness: 0.1,
    metalness: 0, clearcoat: 0.6, depthWrite: false, side: THREE.DoubleSide });
  if (zS1x > xFeed) segmentMesh(xFeed - 0.6, zS1x, topAt, null, liqMat, 0.01);
  // filter cake bed (body below the particle layer), coloured by the pore liquid
  const bedMat = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.75, metalness: 0 });
  const xBed0 = z0 + 0.05, xBed1 = Math.min(SC.x1 + 0.6, xDis);
  segmentMesh(xBed0, xBed1, x => Math.max(cakeAt(x) - 0.8 * rP, 0.005),
    x => { const i = 3 * iz(zOf(x)); return [0.78 * lut[i] + 0.08, 0.78 * lut[i + 1] + 0.08, 0.78 * lut[i + 2] + 0.08]; },
    bedMat, 0.005);
  // supernatant wash liquid on the cake
  if (D.wash.on) {
    D.wash.steps.forEach(st => {
      const red = st.color === "red";
      const m = new THREE.MeshPhysicalMaterial({ color: red ? 0xff3b3b : 0xe9f6ff, transparent: true,
        opacity: red ? 0.42 : 0.30, roughness: 0.05, clearcoat: 1, depthWrite: false, side: THREE.DoubleSide });
      segmentMesh(st.x_dose - 0.15, st.x_end, x => cakeAt(x) + 0.16 * (1 - 0.75 * (x - st.x_dose) / Math.max(st.x_end - st.x_dose, 0.1)), null, m, 0.012);
    });
  }
  // z_S1 marker
  if (OP.zS1 > 0) {
    const ring = new THREE.Mesh(new THREE.TorusGeometry(G.r_jacket + 0.15, 0.06, 8, 64),
      new THREE.MeshBasicMaterial({ color: OP.finished ? 0x48a6ff : 0xff6b4a }));
    ring.rotation.y = Math.PI / 2; ring.position.x = zS1x; app.add(ring);
    label("z_S1 = " + OP.zS1.toFixed(2) + " cm", OP.finished ? "end of cake formation" : "NOT on the frit",
      zS1x, -3.1, 2.8, 6.0, OP.finished ? "#7cc4ff" : "#ff8a70");
  }

  // ------------------------------------------------------------------ particles
  const NP = Math.round(Math.min(9000, Math.max(2500, (xDis - xFeed) * 120 * (OP.hc / 0.4) * Math.pow(0.07 / rP, 2))));
  const pgeo = new THREE.IcosahedronGeometry(rP, 1);
  const pmat = new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.45, metalness: 0.0, envMapIntensity: 0.45 });
  const parts = new THREE.InstancedMesh(pgeo, pmat, NP);
  parts.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
  parts.instanceColor = new THREE.InstancedBufferAttribute(new Float32Array(NP * 3), 3);
  parts.instanceColor.setUsage(THREE.DynamicDrawUsage);
  parts.frustumCulled = false;
  app.add(parts);
  const M = parts.instanceMatrix.array, CC = parts.instanceColor.array;
  for (let i = 0; i < NP; i++) { const o = 16 * i; M[o] = M[o + 5] = M[o + 10] = M[o + 15] = 1; }
  const pX = new Float32Array(NP), pV = new Float32Array(NP), pU = new Float32Array(NP), pS = new Float32Array(NP),
    pJ = new Float32Array(NP);
  const SIG = 0.07;                       // relative spread of the axial velocity (qualitative axial dispersion)
  function gauss() { let u = 0, v = 0; while (u === 0) u = Math.random(); v = Math.random(); return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v); }
  function initParticle(i, x) {
    pX[i] = x; pV[i] = OP.v_ax * Math.max(0.6, 1 + SIG * gauss());
    pU[i] = Math.random(); pS[i] = 2 * Math.random() - 1; pJ[i] = (Math.random() - 0.5) * 0.6;
  }
  function resetParticles() {
    for (let i = 0; i < NP; i++) initParticle(i, xFeed - 0.4 + Math.random() * (xDis - xFeed + 0.4));
  }
  resetParticles();
  const coreR = SC.r_core + rP;
  function placeParticle(i, x) {
    let y, z;
    if (x > xDis) {                                   // falling through the discharge
      const fall = (x - xDis) * 9.0;
      y = -Rb - fall; z = pS[i] * 0.7; x = xDis + pS[i] * 0.5 + pJ[i] * 0.8;
      if (y < G.nozzle_bottom - 1.0) return false;
    } else {
      const k = iz(zOf(x));
      const cake = PR.cake[k], top = PR.top[k];
      const share = Math.min(1, cake / hcEnd);
      const u = pU[i];
      let h;
      if (zOf(x) < 0) h = u * PR.top[k];
      else if (u < share) h = u * hcEnd;
      else h = cake + (u - share) / Math.max(1 - share, 1e-6) * Math.max(top - cake, 0);
      h = Math.min(Math.max(h, 0), 2 * Rb - 2 * rP);
      y = -Rb + rP + h;
      const half = Math.sqrt(Math.max(Rb * Rb - y * y, 0)) - rP;
      z = pS[i] * Math.max(half, 0);
      if (y * y + z * z < coreR * coreR) {           // keep particles out of the screw core
        const zz = Math.sqrt(Math.max(coreR * coreR - y * y, 0));
        z = (pS[i] >= 0 ? 1 : -1) * Math.min(zz, Math.max(half, 0));
      }
    }
    const o = 16 * i; M[o + 12] = x; M[o + 13] = y; M[o + 14] = z;
    return true;
  }
  function colorParticle(i, x) {
    const k = 3 * iz(zOf(Math.min(x, xDis)) + pJ[i]);
    CC[3 * i] = lut[k]; CC[3 * i + 1] = lut[k + 1]; CC[3 * i + 2] = lut[k + 2];
  }

  // tracer particle
  const tracer = new THREE.Group(); app.add(tracer);
  tracer.add(new THREE.Mesh(new THREE.SphereGeometry(rP * 2.0, 20, 14),
    new THREE.MeshStandardMaterial({ color: 0xffd34d, emissive: 0xffb000, emissiveIntensity: 0.9, roughness: 0.3 })));
  const halo = new THREE.Mesh(new THREE.TorusGeometry(rP * 3.6, rP * 0.45, 8, 32),
    new THREE.MeshBasicMaterial({ color: 0xffd34d, transparent: true, opacity: 0.85, depthTest: false }));
  halo.renderOrder = 12; tracer.add(halo);
  const beacon = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.03, 6.5, 6),
    new THREE.MeshBasicMaterial({ color: 0xffd34d, transparent: true, opacity: 0.5, depthTest: false }));
  beacon.position.y = 3.6; beacon.renderOrder = 11; tracer.add(beacon);
  const tr = { x: xFeed, t0: 0, active: true, last: null };

  // ------------------------------------------------------------------ droplets (feed, wash liquid, filtrate)
  const ND = 700;
  const dgeo = new THREE.SphereGeometry(1, 10, 8);
  const dmat = new THREE.MeshPhysicalMaterial({ color: 0xffffff, roughness: 0.05, transparent: true, opacity: 0.85,
    clearcoat: 1, depthWrite: false });
  const drops = new THREE.InstancedMesh(dgeo, dmat, ND);
  drops.instanceColor = new THREE.InstancedBufferAttribute(new Float32Array(ND * 3), 3);
  drops.frustumCulled = false; app.add(drops);
  const DM = drops.instanceMatrix.array, DC = drops.instanceColor.array;
  const dP = new Float32Array(ND * 3), dV = new Float32Array(ND * 3), dL = new Float32Array(ND), dR = new Float32Array(ND),
    dY = new Float32Array(ND);
  for (let i = 0; i < ND; i++) { dL[i] = -1; }
  let dNext = 0;
  function emit(x, y, z, vx, vy, vz, r, col, yStop) {
    const i = dNext; dNext = (dNext + 1) % ND;
    dP[3 * i] = x; dP[3 * i + 1] = y; dP[3 * i + 2] = z; dV[3 * i] = vx; dV[3 * i + 1] = vy; dV[3 * i + 2] = vz;
    dL[i] = 1; dR[i] = r; dY[i] = yStop;
    DC[3 * i] = col[0]; DC[3 * i + 1] = col[1]; DC[3 * i + 2] = col[2];
  }
  const emitters = [];
  const _fc = new THREE.Color(0x3c86ff).convertSRGBToLinear(); const FEEDC = [_fc.r, _fc.g, _fc.b];
  // feed stream (suspension)
  emitters.push({ rate: 26, f() { emit(xFeed + (Math.random() - 0.5) * 0.25, G.nozzle_top + 0.3, (Math.random() - 0.5) * 0.25, 0, -6, 0, 0.09,
    FEEDC, -Rb + topAt(xFeed) ); } });
  // wash liquid dosing
  if (D.wash.on) D.wash.steps.forEach(st => {
    const col = st.color === "red" ? [COL_W1.r, COL_W1.g, COL_W1.b] : [0.86, 0.93, 1.0];
    emitters.push({ rate: 14, f() { emit(st.x_dose + (Math.random() - 0.5) * 0.15, G.nozzle_top + 0.2, (Math.random() - 0.5) * 0.15, 0, -4, 0,
      0.085, col, -Rb + cakeAt(st.x_dose) + 0.1); } });
  });
  // filtrate under each frit (+ vacuum outlet)
  mods.forEach((m, mi) => {
    const nz = nozzleX[mi];
    emitters.push({ rate: m.type === "D" ? 4 : 12, f() {
      const x = m.frit0 + Math.random() * (m.frit1 - m.frit0);
      const k = 3 * iz(zOf(x));
      const col = m.type === "F" ? FEEDC : [lut[k], lut[k + 1], lut[k + 2]];
      emit(x, -Rb - 0.24, (Math.random() - 0.5) * 0.9, 0, -1.5, 0, 0.05, col, -G.r_jacket_in + 0.06);
    } });
    emitters.push({ rate: m.type === "D" ? 2 : 6, f() {
      const k = 3 * iz(zOf(nz.bottom));
      const col = m.type === "F" ? FEEDC : [lut[k], lut[k + 1], lut[k + 2]];
      emit(nz.bottom + (Math.random() - 0.5) * 0.3, -G.r_jacket_in, (Math.random() - 0.5) * 0.3, 0, -2, 0, 0.07, col, G.nozzle_bottom - 1.6);
    } });
  });
  emitters.forEach(e => e.acc = Math.random());
  function stepDrops(dt) {
    emitters.forEach(e => { e.acc += e.rate * dt; while (e.acc >= 1) { e.acc -= 1; e.f(); } });
    for (let i = 0; i < ND; i++) {
      const o = 16 * i;
      if (dL[i] < 0) { DM[o] = DM[o + 5] = DM[o + 10] = 0; DM[o + 15] = 1; continue; }
      dV[3 * i + 1] -= 40 * dt;
      dP[3 * i] += dV[3 * i] * dt; dP[3 * i + 1] += dV[3 * i + 1] * dt; dP[3 * i + 2] += dV[3 * i + 2] * dt;
      if (dP[3 * i + 1] < dY[i]) dL[i] = -1;
      const r = dR[i], st = Math.min(1.8, 1 + Math.abs(dV[3 * i + 1]) * 0.05);
      DM[o] = r; DM[o + 5] = r * st; DM[o + 10] = r; DM[o + 15] = 1;
      DM[o + 12] = dP[3 * i]; DM[o + 13] = dP[3 * i + 1]; DM[o + 14] = dP[3 * i + 2];
    }
    drops.instanceMatrix.needsUpdate = true; drops.instanceColor.needsUpdate = true;
  }

  // ------------------------------------------------------------------ HUD, legend, controls
  const hud = document.getElementById("hud"), legend = document.getElementById("legend"), msg = document.getElementById("msg");
  const fmtT = s => { s = Math.max(0, s); const m = Math.floor(s / 60), r = Math.floor(s % 60); return `${m}:${String(r).padStart(2, "0")} min`; };
  const tau = OP.tau;
  function moduleAt(x) {
    if (x < mods[0].x0) return "inlet";
    for (const m of mods) {
      if (x >= m.frit0 && x <= m.frit1) return `${m.name} (frit)`;
      if (x >= m.x0 && x < m.x0 + G.glass) return m.name;
      if (x >= m.x0 + G.glass && x < m.x0 + G.pitch) return `${m.name} → transport`;
    }
    return x < xDis ? "end piece" : "discharge";
  }
  legend.innerHTML = `
    <div class="h">Legend</div>
    <div class="r"><span class="sw" style="background:#1f63e0"></span>pore liquid: mother liquor (impurity)</div>
    <div class="r"><span class="sw" style="background:#e0262b"></span>wash liquid 1: EtOH/water, red optical tracer</div>
    <div class="r"><span class="sw" style="background:#f4f3ee"></span>wash liquid 2: ethanol (colourless)</div>
    <div class="r"><span class="sw" style="background:linear-gradient(90deg,#1f63e0,#e0262b,#f4f3ee)"></span>mixed colour = pore liquid composition (wash model X*(WR))</div>
    <div class="r"><span class="sw" style="background:#ffd34d;box-shadow:0 0 6px #ffb000"></span>tracer particle (mean velocity v<sub>p,ax</sub>)</div>
    <div class="r"><span class="sq" style="background:rgba(214,236,255,0.25);border-color:#bfe3ff"></span>borosilicate glass module</div>
    <div class="r"><span class="sq" style="background:#f7f7f3"></span>screw, PTFE (${SC.N > 1 ? SC.N + "-flighted, " : ""}right-handed)</div>
    <div class="r"><span class="sq" style="background:#d8d2c4"></span>frit (filter medium, Δp)</div>
    <div class="r"><span class="sq" style="background:rgba(47,127,255,0.45)"></span>suspension until z<sub>S1</sub></div>
    <div class="n">Particles enlarged for visibility. Colours and motion are a qualitative representation of the model results.</div>`;
  const notes = [];
  if (D.wash.msg) notes.push(D.wash.msg);
  if (D.wash.on) D.wash.steps.forEach(st => { if (st.need > st.avail + 1e-6)
    notes.push(`${st.name}: the wash liquid needs ${st.need.toFixed(1)} cm of frit, only ${st.avail.toFixed(1)} cm are available after the dosing point – WR is not fully applied.`); });
  if (!OP.finished) notes.push("Cake formation is not completed on the frit of F1 (z_S1 > L_f): supernatant suspension enters the next module.");
  let rotNote = false;
  function showMsg() {
    const all = notes.concat(rotNote ? ["Screw rotation is displayed slowed down at this speed-up (display limit); conveying velocities remain true to scale in time."] : []);
    msg.style.display = all.length ? "block" : "none"; msg.innerHTML = all.join("<br>");
  }
  showMsg();

  const bar = document.getElementById("bar");
  const state = { play: true, speed: 1, t: 0, view: "overview", cut: false, follow: false };
  function btn(txt, title, fn, cls) { const b = document.createElement("button"); b.innerHTML = txt; b.title = title || ""; b.onclick = fn; if (cls) b.className = cls; bar.appendChild(b); return b; }
  function sep() { const s = document.createElement("span"); s.className = "sep"; bar.appendChild(s); }
  function lbl(t) { const s = document.createElement("span"); s.className = "lbl"; s.textContent = t; bar.appendChild(s); }
  const bPlay = btn("⏸ Pause", "start / stop the simulation", () => { state.play = !state.play; bPlay.innerHTML = state.play ? "⏸ Pause" : "▶ Play"; });
  sep(); lbl("Speed:");
  const speeds = [[1, "1× real time"], [10, "10×"], [60, "60×"], [300, "300×"]];
  const sb = speeds.map(([v, t]) => btn(t, v === 1 ? "real time: screw speed and particle velocity as in the apparatus" : `fast forward ${v}×`, () => setSpeed(v)));
  function setSpeed(v) { state.speed = v; sb.forEach((b, i) => b.className = speeds[i][0] === v ? "on" : ""); }
  setSpeed(1);
  sep();
  btn("⟲ Reset", "restart at t = 0 (steady-state filling)", () => { state.t = 0; resetParticles(); tr.x = xFeed; tr.t0 = 0; tr.last = null; screw.rotation.x = 0; });
  btn("● Release tracer", "release a tracer particle at the feed", () => { tr.x = xFeed; tr.t0 = state.t; tr.active = true; });
  sep(); lbl("View:");
  const bv = {};
  bv.overview = btn("Overview", "whole apparatus", () => setView("overview"));
  bv.feed = btn("F1 close-up", "feed and cake formation", () => setView("feed"));
  bv.wash = btn("Washing", "washing modules", () => setView("wash"));
  bv.follow = btn("Follow tracer", "camera follows the tracer particle", () => setView("follow"));
  const bPan = btn("Info panels", "show / hide the info panels", () => {
    const on = hud.style.display !== "none"; hud.style.display = legend.style.display = on ? "none" : "block";
    bPan.className = on ? "" : "on"; }, "on");
  const bCut = btn("Section view", "cut away the front half of the glass and couplings", () => {
    state.cut = !state.cut; bCut.className = state.cut ? "on" : "";
    clipMats.forEach(m => { m.clippingPlanes = state.cut ? cut : null; m.needsUpdate = true; });
  });
  function setView(v) {
    state.view = v; state.follow = v === "follow";
    Object.keys(bv).forEach(k => bv[k].className = k === v ? "on" : "");
    let tx, d, el = 0.2;
    if (v === "overview") { tx = xC; d = 0.53 * (xMax - xMin) / Math.tan(15 * Math.PI / 180) / Math.max(camera.aspect, 1); d = Math.max(d, 40); }
    else if (v === "feed") { tx = mods[0].x0 + G.glass * 0.5; d = 26; }
    else if (v === "wash") { const w = mods.filter(m => m.type === "W"); tx = w.length ? 0.5 * (w[0].x0 + w[w.length - 1].x0 + G.glass) : xC; d = w.length > 1 ? 44 : 28; }
    else { tx = tr.x; d = 20; }
    const ty = v === "overview" ? 0.072 * d : (v === "follow" ? 0.6 : 0.05 * d);
    controls.target.set(tx, ty, 0);
    camera.position.set(tx - d * 0.12, ty + d * el, d);
    controls.update();
  }

  // ------------------------------------------------------------------ overview strip (2D)
  const sc2 = document.getElementById("stripc"), g2 = sc2.getContext("2d");
  function drawStrip() {
    const W = sc2.clientWidth, H = sc2.clientHeight, dpr = window.devicePixelRatio || 1;
    if (sc2.width !== Math.round(W * dpr)) { sc2.width = Math.round(W * dpr); sc2.height = Math.round(H * dpr); }
    g2.setTransform(dpr, 0, 0, dpr, 0, 0); g2.clearRect(0, 0, W, H);
    const xa = -1.0, xb = G.x_end + G.end_piece + 0.5, L = 14, Rr = W - 14;
    const X = x => L + (x - xa) / (xb - xa) * (Rr - L);
    const y0 = 18, h = 16;
    g2.font = "11px Segoe UI, Arial"; g2.textBaseline = "middle";
    // couplings / apparatus body
    g2.fillStyle = "#3a4652"; g2.fillRect(X(-0.2), y0 + 3, X(G.x_end) - X(-0.2), h - 6);
    mods.forEach(m => {
      g2.fillStyle = "rgba(190,225,255,0.28)"; g2.strokeStyle = "#bfe3ff"; g2.lineWidth = 1;
      g2.fillRect(X(m.x0), y0, X(m.x0 + G.glass) - X(m.x0), h); g2.strokeRect(X(m.x0), y0, X(m.x0 + G.glass) - X(m.x0), h);
      g2.fillStyle = "#d8d2c4"; g2.fillRect(X(m.frit0), y0 + h - 4, X(m.frit1) - X(m.frit0), 4);
      g2.fillStyle = "#e8eef5"; g2.textAlign = "center"; g2.fillText(m.name, X(m.x0 + G.glass / 2), y0 + h / 2);
    });
    g2.fillStyle = "rgba(190,225,255,0.28)"; g2.fillRect(X(G.x_end), y0, X(G.x_end + G.end_piece) - X(G.x_end), h);
    g2.strokeRect(X(G.x_end), y0, X(G.x_end + G.end_piece) - X(G.x_end), h);
    // pore liquid composition along the apparatus
    for (let x = xFeed; x < xDis; x += 0.25) {
      const k = 3 * iz(zOf(x));
      g2.fillStyle = `rgb(${Math.round(255 * Math.pow(lut[k], 1 / 2.2))},${Math.round(255 * Math.pow(lut[k + 1], 1 / 2.2))},${Math.round(255 * Math.pow(lut[k + 2], 1 / 2.2))})`;
      g2.fillRect(X(x), y0 + h + 3, X(x + 0.25) - X(x) + 0.6, 5);
    }
    // z_S1
    g2.strokeStyle = OP.finished ? "#48a6ff" : "#ff6b4a"; g2.lineWidth = 2;
    g2.beginPath(); g2.moveTo(X(zS1x), y0 - 4); g2.lineTo(X(zS1x), y0 + h + 9); g2.stroke();
    // ticks (z axis, 0 = start of frit F1)
    g2.fillStyle = "#9fb4c8"; g2.textAlign = "center"; g2.strokeStyle = "#9fb4c8"; g2.lineWidth = 1;
    for (let z = Math.ceil((xa - z0) / 10) * 10; z <= xb - z0; z += 10) {
      const xx = X(z + z0); g2.beginPath(); g2.moveTo(xx, y0 + h + 9); g2.lineTo(xx, y0 + h + 13); g2.stroke();
      g2.fillText(String(z), xx, y0 + h + 21);
    }
    g2.textAlign = "left"; g2.fillText("z / cm (0 = start of frit F1)", X(xa), 8);
    // tracer
    if (tr.active) {
      const xx = X(Math.min(tr.x, xDis));
      g2.fillStyle = "#ffd34d"; g2.beginPath(); g2.arc(xx, y0 + h / 2, 5, 0, 2 * Math.PI); g2.fill();
      g2.textAlign = "right"; g2.fillStyle = "#ffe08a";
      g2.fillText(`tracer z = ${zOf(Math.min(tr.x, xDis)).toFixed(1)} cm · ${fmtT(state.t - tr.t0)}`, W - 14, 8);
    }
  }

  // ------------------------------------------------------------------ animation loop
  const omega = 2 * Math.PI * OP.n / 60;                    // rad/s (real)
  function resize() {
    const w = wrap.clientWidth, h = wrap.clientHeight;
    if (!w || !h) return false;
    renderer.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix();
  }
  window.addEventListener("resize", resize);
  let inited = false;
  function ensureInit() { if (!inited && resize() !== false) { inited = true; setView(state.view); } }
  ensureInit();
  let last = performance.now(), visible = true;
  if ("IntersectionObserver" in window) new IntersectionObserver(e => { visible = e[0].isIntersecting; }).observe(wrap);
  function frame(now) {
    const dtr = Math.min(0.1, (now - last) / 1000); last = now;
    if (!visible || wrap.clientWidth === 0) { requestAnimationFrame(frame); return; }   // hidden tab: no rendering
    ensureInit();
    if (Math.abs(wrap.clientWidth / wrap.clientHeight - camera.aspect) > 1e-3) resize();
    const dts = state.play ? dtr * state.speed : 0;
    state.t += dts;
    // screw: right-handed, negative rotation about +x (counter-clockwise viewed from the feed end) -> conveys +x
    let wv = omega * state.speed, cap = 2 * Math.PI * 2.0;
    rotNote = state.play && wv > cap; if (rotNote) wv = cap;
    if (state.play) screw.rotation.x -= wv * dtr;
    // particles
    for (let i = 0; i < NP; i++) {
      pX[i] += pV[i] * dts;
      if (!placeParticle(i, pX[i])) { initParticle(i, xFeed - 0.5 + Math.random() * 0.4); placeParticle(i, pX[i]); }
      colorParticle(i, pX[i]);
    }
    parts.instanceMatrix.needsUpdate = true; parts.instanceColor.needsUpdate = true;
    // tracer
    if (tr.active) {
      tr.x += OP.v_ax * dts;
      if (tr.x >= xDis) { tr.last = state.t - tr.t0; tr.x = xFeed; tr.t0 = state.t; }
      const k = iz(zOf(tr.x));
      const hh = zOf(tr.x) < 0 ? 0.5 * PR.top[k] : Math.min(0.55 * hcEnd, PR.cake[k] + 0.0);
      const yT = -Rb + rP * 2 + Math.max(hh, 0);
      tracer.position.set(tr.x, yT, 0.6 * Math.sqrt(Math.max(Rb * Rb - yT * yT, 0)));
      halo.rotation.y += dtr * 2;
      if (state.follow) { const dx = tr.x - controls.target.x; controls.target.x += dx; camera.position.x += dx; }
    }
    stepDrops(state.play ? dtr : 0);
    showMsg();
    controls.update();
    renderer.render(scene, camera);
    // HUD
    const vmm = OP.v_ax * 600;
    hud.innerHTML = `<div class="t">t = ${fmtT(state.t)}</div>
      <div class="s">${state.play ? (state.speed === 1 ? "real time" : "fast forward " + state.speed + "×") : "paused"} · simulated process time</div><hr>
      <span class="k">Screw:</span> <span class="v">${OP.n.toFixed(2)} rpm</span> · P = ${OP.P_mm.toFixed(1)} mm${OP.N > 1 ? " · " + OP.N + " flights" : ""}<br>
      <span class="s">right-handed, turning counter-clockwise viewed from the feed end → conveys left to right</span><br>
      <span class="k">v<sub>p,ax</sub> = P·n/θm:</span> <span class="v">${vmm.toFixed(1)} mm/min</span> · θm = ${OP.theta.toFixed(3)}<br>
      <span class="k">Filling degree α:</span> ${(100 * OP.alpha).toFixed(0)} % · <span class="k">h<sub>c</sub>:</span> ${(10 * OP.hc).toFixed(2)} mm<br>
      <span class="k">z<sub>S1</sub>:</span> <span class="v">${OP.zS1.toFixed(2)} cm</span> ${OP.finished ? "(on the frit)" : "<b style='color:#ff8a70'>(beyond L_f)</b>"}<hr>
      <span class="k">Mean residence times</span><br>
      on a frit (L<sub>f</sub> = ${G.Lf.toFixed(1)} cm): <span class="v">${fmtT(60 * tau.frit)}</span><br>
      per module (${G.pitch.toFixed(1)} cm): <span class="v">${fmtT(60 * tau.module)}</span><br>
      feed → discharge: <span class="v">${fmtT(60 * tau.total)}</span><hr>
      <span class="k">Tracer:</span> z = <span class="v">${zOf(Math.min(tr.x, xDis)).toFixed(1)} cm</span> · ${moduleAt(tr.x)}<br>
      residence time so far: <span class="v">${fmtT(state.t - tr.t0)}</span>${tr.last != null ? `<br>last passage feed → discharge: <span class="v">${fmtT(tr.last)}</span>` : ""}`;
    drawStrip();
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
  window.CVSF_STATE = state;
})();
