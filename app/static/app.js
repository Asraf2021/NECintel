/* Sərnişin mobil tətbiqi (PWA): dayanacaq + ETA + marşrut cədvəli, haradan→hara (köçürmə ilə), yük hesabatı, profil. */
(function () {
  const LEVEL_COLOR = { low: "#16a34a", medium: "#d97706", high: "#dc2626", no_data: "#9ca3af" };
  const REFRESH_MS = 3000;
  const $ = id => document.getElementById(id);
  I18N.mount();
  if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => {});

  // --- xəritə ---
  const map = L.map("map", { zoomControl: false }).setView([40.40, 49.87], 12);
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 19, attribution: "&copy; OpenStreetMap" }).addTo(map);
  const routeLayer = L.layerGroup().addTo(map), busLayer = L.layerGroup().addTo(map), tripLayer = L.layerGroup().addTo(map);
  let fitTarget = null, userMoved = false;
  map.on("dragstart zoomstart", e => { if (e.originalEvent) userMoved = true; });
  function fit() { if (!fitTarget) return; map.invalidateSize(); map.fitBounds(fitTarget, { padding: [20, 20], maxZoom: 15, animate: false }); }
  new ResizeObserver(() => { map.invalidateSize(); if (!userMoved) fit(); }).observe($("map"));

  let routes = [], current = null, busMarkers = {}, stopMarkers = {}, dir = 1, routeBounds = null, lastTrip = null, user = null;
  let showAll = false, selectedBus = null, lastArrivals = [];
  let allMode = false, allStop = null, nearest = [], userPos = null;   // "Hamısı" rejimi
  const stopIdNow = () => allMode ? (allStop ? allStop.id : "") : $("stop").value;
  async function api(path, opts) {
    const r = await fetch(path, opts);
    if (r.status === 401) { location.href = "/login"; throw new Error("login"); }
    if (!r.ok) { let m = r.statusText; try { const d = await r.json(); m = Array.isArray(d.detail) ? d.detail.map(x => x.msg).join(", ") : d.detail || m; } catch (_) {} throw new Error(m); }
    return r.json();
  }
  const levelLabel = l => t(l);
  const badge = level => `<span class="badge ${level}" title="${level === "no_data" ? t("no_data_hint") : ""}">${levelLabel(level)}</span>`;
  const mins = s => s < 45 ? t("arriving") : `${Math.max(1, Math.round(s / 60))} ${t("min")}`;
  const dirArrow = d => d === 1 ? "→" : "←";

  // --- sürüşdürülən alt panel (bottom sheet) ---
  const sheet = $("sheet"), stage = $("stage"), handle = $("handle");
  const PEEK = 30;
  let sheetFrac = 0.6, drag = null;
  function stageH() { return stage.getBoundingClientRect().height; }
  function setSheet(px, animate = true) {
    const H = stageH(); px = Math.max(PEEK, Math.min(H, px)); sheetFrac = px / H;
    sheet.classList.toggle("dragging", !animate); sheet.style.height = px + "px";
    setTimeout(() => map.invalidateSize(), animate ? 220 : 0);
  }
  function snap(px) {
    const H = stageH(), points = [PEEK, H * 0.6, H];
    setSheet(points.reduce((a, b) => Math.abs(b - px) < Math.abs(a - px) ? b : a));
  }
  handle.addEventListener("pointerdown", e => { drag = { y: e.clientY, h: sheet.getBoundingClientRect().height, moved: false }; try { handle.setPointerCapture(e.pointerId); } catch (_) {} });
  handle.addEventListener("pointermove", e => { if (!drag) return; const dy = e.clientY - drag.y; if (Math.abs(dy) > 3) drag.moved = true; setSheet(drag.h - dy, false); });
  handle.addEventListener("pointerup", () => { if (!drag) return; const h = sheet.getBoundingClientRect().height; if (!drag.moved) snap(h <= PEEK + 1 ? stageH() * 0.6 : PEEK); else snap(h); drag = null; });
  window.addEventListener("resize", () => setSheet(sheetFrac * stageH()));
  setSheet(stageH() * 0.6, false);

  // --- tablar ---
  document.querySelectorAll(".m-nav button").forEach(b => b.addEventListener("click", () => showTab(b.dataset.tab)));
  function showTab(name) {
    document.querySelectorAll(".m-nav button").forEach(x => x.classList.toggle("active", x.dataset.tab === name));
    document.querySelectorAll(".m-tab").forEach(s => s.hidden = s.id !== "tab-" + name);
    if (name === "report" || name === "profile") setSheet(stageH()); else if (sheetFrac > 0.95 || sheetFrac < 0.2) setSheet(stageH() * 0.6);
    if (name === "trip") { map.invalidateSize(); if (lastTrip) drawTrip(lastTrip); }
    else if (name === "stop") { tripLayer.clearLayers(); map.invalidateSize(); if (current) { drawRoute(); } }
  }

  // --- marşrut ---
  function renderRouteOptions() {
    const q = $("route-filter").value.trim().toLowerCase();
    const list = routes.filter(r => !q || r.number.toLowerCase().startsWith(q) || r.name.toLowerCase().includes(q));
    const prev = $("route").value;
    $("route").innerHTML = `<option value="all">${t("all_routes")}</option>` + list.map(r => `<option value="${r.id}">${r.number} — ${r.name}</option>`).join("");
    $("route").value = (prev === "all" || list.some(r => r.id === prev)) ? prev : (list[0] ? list[0].id : "all");
  }
  async function selectRoute() {
    const id = $("route").value; if (!id) return;
    localStorage.setItem("st_route", id);
    allMode = id === "all";
    $("stop").hidden = allMode; $("stop-search-wrap").hidden = !allMode;
    if (allMode) {
      current = null; selectedBus = null; routeLayer.clearLayers(); busLayer.clearLayers(); busMarkers = {}; stopMarkers = {};
      $("route-meta").textContent = t("all_hint"); $("report-route").textContent = t("all_routes");
      $("route-load").className = "badge no_data"; $("route-load").textContent = "—"; $("route-reports").textContent = "";
      if (allStop) $("stop-search").value = allStop.name;
      await refresh(); await renderTimeline(); return;
    }
    current = await api(`/api/routes/${id}`);
    $("report-route").textContent = `${current.number} — ${current.name}`;
    const [a, b] = current.name.split(" – ");
    const g = { 1: [], 2: [] }; current.stops.forEach(s => g[s.direction].push(s));
    $("stop").innerHTML = `<option value="">${t("choose_stop")}</option>` +
      `<optgroup label="${a || t("dir1")} → ${b || ""}">${g[1].map(s => `<option value="${s.id}">${s.name}</option>`).join("")}</optgroup>` +
      `<optgroup label="${b || t("dir2")} → ${a || ""}">${g[2].map(s => `<option value="${s.id}">${s.name}</option>`).join("")}</optgroup>`;
    const saved = localStorage.getItem("st_stop_" + id); if (saved) $("stop").value = saved;
    $("route-meta").textContent = `${current.carrier || ""} · ${(current.length_m / 1000).toFixed(1)} ${t("km")} · ≈ ${current.duration_min || "?"} ${t("min")} · ${current.stops.length} ${t("stops_n")}`;
    drawRoute(); await refresh(); await renderTimeline();
  }
  function drawRoute() {
    routeLayer.clearLayers(); busLayer.clearLayers(); busMarkers = {}; stopMarkers = {};
    const line = L.polyline(current.polyline, { color: current.color, weight: 5, opacity: 0.8 }).addTo(routeLayer);
    current.stops.forEach(s => {
      stopMarkers[s.id] = L.circleMarker([s.lat, s.lon], { radius: 5, color: "#fff", weight: 2, fillColor: current.color, fillOpacity: 1 })
        .bindTooltip(`${s.name} ${dirArrow(s.direction)}`).on("click", () => { $("stop").value = s.id; refresh(); }).addTo(routeLayer);
    });
    routeBounds = line.getBounds(); fitTarget = routeBounds; userMoved = false; fit(); setTimeout(fit, 100);
  }
  const busIcon = b => L.divIcon({ className: "", iconAnchor: [20, 11], html: `<div style="background:${LEVEL_COLOR[b.load_level]};color:#fff;border:2px solid #fff;border-radius:8px;padding:1px 6px;font-size:11px;font-weight:700;box-shadow:0 1px 4px rgba(0,0,0,.4);white-space:nowrap">🚌 ${b.route_number}</div>` });
  function updateBuses(buses) {
    const seen = new Set();
    buses.forEach(b => {
      seen.add(b.id);
      const tip = `${t("bus")} ${b.plate} · ${b.speed_kmh} km/s · ${t("next")}: ${b.next_stop || "—"} · ${levelLabel(b.load_level)}`;
      if (busMarkers[b.id]) busMarkers[b.id].setLatLng([b.lat, b.lon]).setIcon(busIcon(b)).setTooltipContent(tip);
      else busMarkers[b.id] = L.marker([b.lat, b.lon], { icon: busIcon(b) }).bindTooltip(tip).addTo(busLayer);
    });
    Object.keys(busMarkers).forEach(id => { if (!seen.has(id)) { busLayer.removeLayer(busMarkers[id]); delete busMarkers[id]; } });
    const sel = $("bus").value;
    $("bus").innerHTML = `<option value="">${t("whole_route")}</option>` + buses.map(b => `<option value="${b.id}">${t("bus")} ${b.plate} (${t("next")}: ${b.next_stop || "—"})</option>`).join("");
    if (buses.some(b => b.id === sel)) $("bus").value = sel;
  }
  function renderEta(data) {
    const stopId = stopIdNow();
    if (current) Object.entries(stopMarkers).forEach(([id, m]) => m.setStyle({ radius: id === stopId ? 9 : 5, fillColor: id === stopId ? "#111827" : current.color }));
    if (!stopId) { $("eta").innerHTML = ""; $("eta-empty").style.display = ""; $("eta-empty").textContent = t("pick_stop"); return; }
    lastArrivals = data.arrivals;
    if (!data.arrivals.length) { $("eta").innerHTML = ""; $("eta-all").hidden = true; $("eta-empty").style.display = ""; $("eta-empty").textContent = t("no_buses"); return; }
    $("eta-empty").style.display = "none";
    if (!selectedBus || !data.arrivals.some(a => a.bus_id === selectedBus)) selectedBus = data.arrivals[0].bus_id;
    const arrivals = showAll ? data.arrivals : data.arrivals.filter(a => a.bus_id === selectedBus);
    $("eta").innerHTML = arrivals.map(a => `<li class="${a.bus_id === selectedBus ? "sel" : ""}" data-bus="${a.bus_id}">
      <span class="num" style="background:${a.route_color}">${a.route_number}</span>
      <div><div>${a.bus_id === data.arrivals[0].bus_id ? t("next_bus") : t("after")} · ${a.plate} ${badge(a.load_level)}</div>
        <div class="sub">${(a.distance_m / 1000).toFixed(1)} ${t("km")} · ${a.stops_between} ${t("intermediate")}</div></div>
      <span class="eta">${mins(a.eta_seconds)}</span></li>`).join("");
    $("eta").querySelectorAll("li").forEach(li => li.addEventListener("click", () => { selectedBus = li.dataset.bus; renderEta({ arrivals: lastArrivals }); renderTimeline(); }));
    $("eta-all").hidden = data.arrivals.length < 2;
    $("eta-all").textContent = showAll ? t("show_nearest") : `${t("show_all")} (${data.arrivals.length})`;
  }
  async function renderTimeline() {
    if (!current && !allMode) return;
    if (allMode && !selectedBus) { $("timeline").innerHTML = ""; $("timeline-title").textContent = t("bus_timeline"); $("dir-toggle").hidden = true; return; }
    try {
      if (selectedBus && stopIdNow()) {   // seçilmiş avtobusun hər dayanacağa gəliş vaxtı
        const d = await api(`/api/buses/${selectedBus}/timeline`);
        const stopId = stopIdNow();
        const idx = d.stops.findIndex(s => s.id === stopId);
        const list = idx >= 0 ? d.stops.slice(idx) : d.stops;
        $("timeline-title").textContent = t("bus_timeline");
        $("dir-toggle").hidden = true;
        $("timeline").innerHTML = `<div class="tl-dir">🚌 ${d.bus.plate} · ${t("next")}: ${d.bus.next_stop || "—"} · ${d.bus.speed_kmh} km/s</div>` +
          list.map(s => `<div class="tl-row ${s.id === stopId ? "cur" : ""}"><span class="tl-name">${s.name}</span><span class="muted">${(s.distance_m / 1000).toFixed(1)} ${t("km")}</span><span class="tl-eta">${mins(s.eta_seconds)}</span></div>`).join("");
        return;
      }
      $("timeline-title").textContent = t("timeline_title"); $("dir-toggle").hidden = false;
      const d = await api(`/api/routes/${current.id}/timeline`);
      $("timeline").innerHTML = `<div class="tl-dir">${t(dir === 1 ? "dir1" : "dir2")} · ${t("avg_speed")} ${d.route.avg_speed_kmh} km/s</div>` +
        d.stops.filter(s => s.direction === dir).map(s => `<div class="tl-row"><span class="tl-name">${s.name}</span><span class="muted">${s.leg_seconds ? "+" + Math.round(s.leg_seconds / 60) + " " + t("min") : ""}</span><span class="tl-eta">${mins(s.next_bus.eta_seconds)}</span></div>`).join("");
    } catch (e) { $("timeline").innerHTML = `<div class="empty">${e.message}</div>`; }
  }
  function renderArrivalBuses(data) {
    busLayer.clearLayers(); busMarkers = {}; routeLayer.clearLayers();
    const pts = [[data.stop.lat, data.stop.lon]];
    L.circleMarker([data.stop.lat, data.stop.lon], { radius: 9, color: "#fff", weight: 2, fillColor: "#111827", fillOpacity: 1 }).bindTooltip(data.stop.name).addTo(routeLayer);
    data.arrivals.forEach(a => {
      pts.push([a.lat, a.lon]);
      busMarkers[a.bus_id] = L.marker([a.lat, a.lon], { icon: busIcon({ load_level: a.load_level, route_number: a.route_number }) })
        .bindTooltip(`${a.route_number} · ${a.plate} · ${mins(a.eta_seconds)}`).addTo(busLayer);
    });
    fitTarget = L.latLngBounds(pts); userMoved = false; fit();
    const sel = $("bus").value;
    $("bus").innerHTML = data.arrivals.map(a => `<option value="${a.bus_id}">${a.route_number} · ${t("bus")} ${a.plate} (${mins(a.eta_seconds)})</option>`).join("");
    if (data.arrivals.some(a => a.bus_id === sel)) $("bus").value = sel; else if (selectedBus) $("bus").value = selectedBus;
  }
  async function refresh() {
    if (allMode) {
      try {
        if (!allStop) { renderEta({ arrivals: [] }); $("eta-empty").textContent = t("pick_stop"); return; }
        const data = await api(`/api/eta?stop_id=${allStop.id}&per_route=2`);
        renderArrivalBuses(data); renderEta(data);
      } catch (e) { if (e.message !== "login") $("toast").textContent = t("error") + ": " + e.message; }
      return;
    }
    if (!current) return;
    try {
      const [buses, route] = await Promise.all([api(`/api/buses?route_id=${current.id}`), api(`/api/routes/${current.id}`)]);
      updateBuses(buses);
      $("route-load").className = "badge " + route.load.level; $("route-load").textContent = levelLabel(route.load.level);
      $("route-load").title = route.load.level === "no_data" ? t("no_data_hint") : "";
      $("route-reports").textContent = route.load.report_count ? `(${route.load.report_count} ${t("reports_n")})` : "";
      const stopId = stopIdNow(); localStorage.setItem("st_stop_" + current.id, stopId);
      renderEta(stopId ? await api(`/api/eta?stop_id=${stopId}&route_id=${current.id}&per_route=3`) : { arrivals: [] });
    } catch (e) { if (e.message !== "login") $("toast").textContent = t("error") + ": " + e.message; }
  }
  async function sendReport(level) {
    let routeId = current ? current.id : null;
    if (allMode) {
      const a = lastArrivals.find(x => x.bus_id === ($("bus").value || selectedBus));
      if (!a) { $("toast").textContent = t("pick_bus_first"); return; }
      routeId = a.route_id;
    }
    const body = { route_id: routeId, level };
    if ($("bus").value) body.bus_id = $("bus").value;
    if (stopIdNow()) body.stop_id = stopIdNow();
    const buttons = document.querySelectorAll(".report-buttons button"); buttons.forEach(b => b.disabled = true);
    try {
      const res = await api("/api/reports", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      $("toast").textContent = `${t("thanks")} ${t("current_load")} — ${levelLabel(res.line_load.level)}.`;
      await refresh();
    } catch (e) { $("toast").textContent = t("error") + ": " + e.message; }
    finally { setTimeout(() => buttons.forEach(b => b.disabled = false), 1500); }
  }

  // --- haradan → hara (köçürmə ilə) ---
  function drawTrip(opt) {
    tripLayer.clearLayers(); routeLayer.clearLayers(); busLayer.clearLayers(); busMarkers = {};
    const all = [];
    opt.legs.forEach((leg, li) => {
      const pts = leg.stops.map(s => [s.lat, s.lon]); all.push(...pts);
      L.polyline(pts, { color: leg.route_color, weight: 6, opacity: 0.9 }).addTo(tripLayer);
      leg.stops.forEach((s, i) => {
        const end = i === 0 || i === leg.stops.length - 1;
        L.circleMarker([s.lat, s.lon], { radius: end ? 8 : 4, color: "#fff", weight: 2, fillColor: end ? "#111827" : leg.route_color, fillOpacity: 1 })
          .bindTooltip(`${s.name} · +${Math.round((leg.depart_seconds + s.offset_seconds) / 60)} ${t("min")}`).addTo(tripLayer);
      });
    });
    if (all.length) { fitTarget = L.latLngBounds(all); userMoved = false; fit(); }
    // seçilmiş variantın dayanacaq cədvəli (operator panelindəki kimi)
    $("trip-timeline").innerHTML = `<h3>${t("stops_and_time")}</h3>` + opt.legs.map(leg => `
      <div class="tl-dir"><span class="line-num" style="background:${leg.route_color}">${leg.route_number}</span> ${leg.from.name} → ${leg.to.name} · ${t("wait")} ${mins(leg.wait.eta_seconds)} (${t("bus")} ${leg.wait.plate || "—"})</div>
      ${leg.stops.map(s => `<div class="tl-row"><span class="tl-name">${s.name}</span><span class="muted">+${Math.round(s.offset_seconds / 60)} ${t("min")}</span><span class="tl-eta">${Math.round((leg.depart_seconds + s.offset_seconds) / 60)} ${t("min")}</span></div>`).join("")}`).join("");
  }
  async function findTrip() {
    const from = $("from").value.trim(), to = $("to").value.trim();
    if (!from || !to) { $("trip-toast").textContent = t("both_stops"); return; }
    $("trip-toast").textContent = t("searching"); $("trip-results").innerHTML = ""; $("trip-timeline").innerHTML = "";
    try {
      const data = await api(`/api/trip?from_name=${encodeURIComponent(from)}&to_name=${encodeURIComponent(to)}&limit=3`);
      if (!data.options.length) { $("trip-toast").textContent = t("no_trip"); return; }
      $("trip-toast").textContent = `${data.options.length} ${t("found")}`;
      $("trip-results").innerHTML = data.options.map((o, i) => `
        <div class="trip" data-i="${i}">
          <div class="trip-head">
            <div class="chips">${o.legs.map(l => `<span class="num" style="background:${l.route_color}">${l.route_number}</span>`).join('<span class="muted">›</span>')}</div>
            <div><div><strong>${Math.round(o.total_seconds / 60)} ${t("min")}</strong> <span class="muted">· ${o.transfers ? t("transfer1") : t("direct")}</span></div>
              <div class="sub">${t("wait")} ${Math.round(o.wait_seconds / 60)} + ${t("ride")} ${Math.round(o.travel_seconds / 60)} ${t("min")} · ${o.stops_count} ${t("stops_n")}${o.transfer_stop ? ` · ${t("transfer_at")} ${o.transfer_stop}` : ""}</div>
              <div class="sub">${o.legs.map(l => `${l.route_number}: ${badge(l.load.level)}`).join(" ")}</div></div>
          </div></div>`).join("");
      $("trip-results").querySelectorAll(".trip").forEach(div => div.addEventListener("click", () => {
        $("trip-results").querySelectorAll(".trip").forEach(x => x.classList.toggle("selected", x === div));
        lastTrip = data.options[+div.dataset.i]; drawTrip(lastTrip);
      }));
      lastTrip = data.options[0]; $("trip-results").querySelector(".trip").classList.add("selected"); drawTrip(lastTrip);
    } catch (e) { $("trip-toast").textContent = t("error") + ": " + e.message; }
  }

  // --- dayanacaq axtarışı (autocomplete) ---
  let stopNames = [];
  const norm = s => s.toLowerCase().replace(/ı/g, "i").replace(/ə/g, "e").replace(/ş/g, "s").replace(/ç/g, "c").replace(/ğ/g, "g").replace(/ü/g, "u").replace(/ö/g, "o");
  async function loadNearest() {
    const pos = userPos || { lat: 40.3777, lon: 49.8469 };   // GPS yoxdursa: 28 May (şəhər mərkəzi)
    try { nearest = await api(`/api/stops/nearest?lat=${pos.lat}&lon=${pos.lon}&limit=5`); } catch (_) { nearest = []; }
  }
  function attachAutocomplete(input, listEl, onPick) {
    function render() {
      const q = norm(input.value.trim());
      let items;
      if (q.length < 2) {   // boş olmasın: ən yaxın 5 dayanacaq
        items = nearest.map(s => ({ name: s.name, sub: `${(s.distance_m / 1000).toFixed(1)} ${t("km")} · ${s.routes.slice(0, 6).join(", ")}` }));
        listEl.innerHTML = `<div class="ac-head">📍 ${t("nearest")}</div>` + items.map(i => `<div class="ac-item" data-name="${i.name.replace(/"/g, "&quot;")}">${i.name}<span class="muted"> · ${i.sub}</span></div>`).join("");
      } else {
        const starts = [], contains = [];
        for (const n of stopNames) { const nn = norm(n); if (nn.startsWith(q)) starts.push(n); else if (nn.includes(q)) contains.push(n); }
        items = starts.concat(contains).slice(0, 25);
        listEl.innerHTML = items.length ? items.map(n => `<div class="ac-item" data-name="${n.replace(/"/g, "&quot;")}">${n}</div>`).join("") : `<div class="ac-item muted">${t("no_match")}</div>`;
      }
      listEl.hidden = false;
      listEl.querySelectorAll(".ac-item").forEach(d => d.addEventListener("mousedown", e => {
        e.preventDefault(); if (d.classList.contains("muted")) return;
        input.value = d.dataset.name; listEl.hidden = true; if (onPick) onPick(d.dataset.name);
      }));
    }
    input.addEventListener("input", render); input.addEventListener("focus", render);
    input.addEventListener("blur", () => setTimeout(() => { listEl.hidden = true; }, 150));
  }
  attachAutocomplete($("from"), $("from-list")); attachAutocomplete($("to"), $("to-list"));
  [$("from"), $("to"), $("stop-search")].forEach(i => i.addEventListener("focus", () => { if (sheetFrac < 0.95) setSheet(stageH()); }));   // siyahıya yer açılır
  attachAutocomplete($("stop-search"), $("stop-search-list"), async name => {
    let s = nearest.find(x => x.name === name);
    if (!s) { const found = await api(`/api/stops?q=${encodeURIComponent(name)}&limit=20`); s = found.find(x => x.name === name) || found[0]; }
    if (!s) return;
    allStop = { id: s.id, name: s.name }; selectedBus = null; showAll = true;
    await refresh(); await renderTimeline();
  });

  // --- profil / PWA ---
  let installEvt = null;
  window.addEventListener("beforeinstallprompt", e => { e.preventDefault(); installEvt = e; });
  $("install").addEventListener("click", async () => {
    if (installEvt) { installEvt.prompt(); const r = await installEvt.userChoice; if (r.outcome === "accepted") $("install-hint").textContent = t("installed"); installEvt = null; }
    else $("install-hint").textContent = t("install_hint");
  });
  $("logout").addEventListener("click", async () => { await fetch("/api/auth/logout", { method: "POST" }); location.href = "/login"; });

  // --- hadisələr ---
  $("route-filter").addEventListener("input", () => { renderRouteOptions(); selectRoute(); });
  $("route").addEventListener("change", selectRoute);
  $("stop").addEventListener("change", () => { selectedBus = null; refresh().then(renderTimeline); });
  $("eta-all").addEventListener("click", () => { showAll = !showAll; renderEta({ arrivals: lastArrivals }); });
  document.querySelectorAll(".dir-toggle button").forEach(b => b.addEventListener("click", () => { dir = +b.dataset.dir; document.querySelectorAll(".dir-toggle button").forEach(x => x.classList.toggle("sel", x === b)); renderTimeline(); }));
  document.querySelectorAll(".report-buttons button").forEach(b => b.addEventListener("click", () => sendReport(b.dataset.level)));
  $("trip-go").addEventListener("click", findTrip);
  $("trip-swap").addEventListener("click", () => { const x = $("from").value; $("from").value = $("to").value; $("to").value = x; });
  [$("from"), $("to")].forEach(i => i.addEventListener("keydown", e => { if (e.key === "Enter") findTrip(); }));
  document.addEventListener("langchange", () => { if (current) { selectRoute(); } if (lastTrip) drawTrip(lastTrip); renderProfile(); });

  function renderProfile() { if (!user) return; $("p-name").textContent = user.full_name || user.username; $("p-role").textContent = `@${user.username} · ${t(user.role === "operator" ? "role_operator" : "role_passenger")}`; }

  (async function init() {
    const me = await api("/api/auth/me"); user = me.user; if (!user) { location.href = "/login"; return; }
    renderProfile();
    await new Promise(res => { if (!navigator.geolocation) return res(); navigator.geolocation.getCurrentPosition(p => { userPos = { lat: p.coords.latitude, lon: p.coords.longitude }; res(); }, () => res(), { timeout: 2500 }); });
    await loadNearest();
    routes = await api("/api/routes"); renderRouteOptions();
    const saved = localStorage.getItem("st_route"); if (saved && (saved === "all" || routes.some(r => r.id === saved))) $("route").value = saved;
    await selectRoute();
    setInterval(refresh, REFRESH_MS); setInterval(renderTimeline, 10000);
    api("/api/stops/names").then(names => { stopNames = names; }).catch(() => {});
  })().catch(e => { if (e.message !== "login") $("toast").textContent = t("error") + ": " + e.message; });
})();
