/* Operator paneli (AYNA üslubu): tam ekran xəritə, sol panel – xətlər siyahısı və marşrut detalı, sağ panel – xəbərdarlıqlar. */
(function () {
  const LEVEL_COLOR = { low: "#16a34a", medium: "#d97706", high: "#dc2626", no_data: "#9ca3af" };
  const REFRESH_MS = 4000;
  const $ = id => document.getElementById(id);
  I18N.mount();

  const map = L.map("map", { zoomControl: true, preferCanvas: true }).setView([40.40, 49.87], 11);
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 19, attribution: "&copy; OpenStreetMap" }).addTo(map);
  const lineLayer = L.layerGroup().addTo(map), stopLayer = L.layerGroup().addTo(map), busLayer = L.layerGroup().addTo(map), detailLayer = L.layerGroup().addTo(map);
  // dayanacağa klik → bu dayanacağa yaxınlaşan bütün marşrutların avtobusları
  async function openStopPopup(s) {
    const popup = L.popup({ maxWidth: 320 }).setLatLng([s.lat, s.lon]).setContent(`<b>${s.name}</b><br><span class="muted">…</span>`).openOn(map);
    try {
      const d = await api(`/api/eta?stop_id=${s.id}&per_route=1`);
      const rows = d.arrivals.slice(0, 8).map(a => `<div class="pop-row"><span class="line-num" style="background:${a.route_color}">${a.route_number}</span> <span>${a.plate}</span> <span class="badge ${a.load_level}">${t(a.load_level)}</span><b>${mins(a.eta_seconds)}</b></div>`).join("");
      popup.setContent(`<b>${s.name}</b><div class="muted small">${t("approaching")}</div>${rows || `<div class="muted">${t("no_buses")}</div>`}`);
    } catch (e) { popup.setContent(`<b>${s.name}</b><br>${e.message}`); }
  }
  function setPanels(side, hidden) {
    document.body.classList.toggle("hide-" + side, hidden);
    const b = $("toggle-" + side); b.textContent = side === "left" ? (hidden ? "▶" : "◧") : (hidden ? "◀" : "◨");
    b.title = t(hidden ? "show_panels" : "hide_panels");
    setTimeout(() => map.invalidateSize(), 250);
  }
  $("toggle-left").addEventListener("click", () => setPanels("left", !document.body.classList.contains("hide-left")));
  $("toggle-right").addEventListener("click", () => setPanels("right", !document.body.classList.contains("hide-right")));
  new ResizeObserver(() => map.invalidateSize()).observe($("map"));

  const linePolys = {}, busMarkers = {}, knownAlerts = new Set(), logLines = [], seenReports = new Set();
  let lastLines = [], selected = null, dir = 1, detail = null;

  async function api(path, opts) {
    const r = await fetch(path, opts);
    if (r.status === 401 || r.status === 403) { location.href = "/login?need=operator"; throw new Error("login"); }
    if (!r.ok) { let m = r.statusText; try { m = (await r.json()).detail || m; } catch (_) {} throw new Error(m); }
    return r.json();
  }
  function log(msg) { const ts = new Date().toLocaleTimeString("az-AZ", { hour12: false }); logLines.unshift(`[${ts}] ${msg}`); if (logLines.length > 30) logLines.pop(); $("log").textContent = logLines.join("\n"); }
  const mins = s => s < 45 ? t("arriving") : `${Math.max(1, Math.round(s / 60))} ${t("min")}`;
  const badge = l => `<span class="badge ${l}" title="${l === "no_data" ? t("no_data_hint") : ""}">${t(l)}</span>`;
  const sources = s => `<b title="passenger">S ${s.passenger || 0}</b> · V ${s.sim_passenger || 0}${s.demo ? ` · D ${s.demo}` : ""}`;

  async function ensureLine(l) {
    if (linePolys[l.id] !== undefined) return;
    linePolys[l.id] = null;
    const d = await api(`/api/routes/${l.id}`);
    linePolys[l.id] = L.polyline(d.polyline, { color: LEVEL_COLOR[l.load.level], weight: 4, opacity: 0.7 })
      .bindTooltip(`${l.number} — ${l.name}`).on("click", () => openDetail(l.id)).addTo(lineLayer);
    d.stops.forEach(s => L.circleMarker([s.lat, s.lon], { radius: 3.5, color: "#fff", weight: 1, fillColor: "#334155", fillOpacity: 0.9 })
      .bindTooltip(s.name).on("click", e => { L.DomEvent.stop(e); openStopPopup(s); }).addTo(stopLayer));
  }

  function renderLines(lines) {
    lastLines = lines;
    const q = $("line-filter").value.trim().toLowerCase();
    const shown = lines.filter(l => (!$("only-data").checked || l.load.level !== "no_data" || l.monitored) && (!q || l.number.toLowerCase().startsWith(q)));
    let buses = 0, reports = 0; lines.forEach(l => { buses += l.bus_count; reports += l.load.report_count; });
    $("kpi-lines").textContent = lines.length; $("kpi-buses").textContent = buses; $("kpi-reports").textContent = reports;
    $("lines").innerHTML = shown.map(l => `
      <div class="line-card ${l.active_alert ? "alert-row" : ""}" data-id="${l.id}">
        <span class="line-num" style="background:${l.color}">${l.number}</span>
        <div class="lc-body"><div class="lc-name">${l.name}</div>
          <div class="lc-sub">${badge(l.load.level)} <span class="muted">${sources(l.report_sources)} · ${l.bus_count} 🚌 · ${l.avg_speed_kmh} km/s${l.bunching ? ' · <span class="flag">' + t("bunching_yes") + '</span>' : ""}</span></div>
          ${l.high_for_minutes ? `<div class="bar"><div style="width:${Math.min(100, Math.round(l.high_for_minutes / l.anomaly_threshold_minutes * 100))}%"></div></div>` : ""}</div>
        <span class="lc-arrow">›</span></div>`).join("") || `<div class="empty">—</div>`;
    $("lines").querySelectorAll(".line-card").forEach(c => c.addEventListener("click", () => openDetail(c.dataset.id)));
    lines.filter(l => l.load.level !== "no_data" || l.monitored).forEach(l => ensureLine(l).then(() => {
      if (linePolys[l.id]) linePolys[l.id].setStyle({ color: LEVEL_COLOR[l.load.level], weight: l.load.level === "high" ? 6 : 4, opacity: selected && selected !== l.id ? 0.25 : 0.75 });
    }).catch(() => {}));
    if (selected) renderDetailStats();
  }

  function renderAlerts(alerts) {
    $("kpi-alerts").textContent = alerts.filter(a => a.status === "active").length;
    alerts.forEach(a => { if (!knownAlerts.has(a.id)) { knownAlerts.add(a.id); if (a.status === "active") log(`⚠ #${a.id}: ${a.message}`); } });
    if (!alerts.length) { $("alerts").innerHTML = `<div class="empty">${t("no_alerts")}</div>`; return; }
    $("alerts").innerHTML = alerts.map(a => `
      <div class="alert ${a.status}">
        <div><strong>${a.status === "active" ? "⚠ " + t("recommend") : a.status === "acknowledged" ? "✔ " + t("acked") : "✓ " + t("resolved")}</strong> · <span class="line-num" style="background:${a.route ? a.route.color : "#333"}">${a.route ? a.route.number : a.route_id}</span></div>
        <div style="margin-top:4px">${a.message}</div>
        <div class="meta">${new Date(a.created_at).toLocaleString()}</div>
        ${a.status === "active" ? `<div style="margin-top:6px"><button data-ack="${a.id}">${t("ack_btn")}</button> <button class="btn" data-open="${a.route_id}">№ ${a.route ? a.route.number : ""} ›</button></div>` : ""}
      </div>`).join("");
    $("alerts").querySelectorAll("button[data-ack]").forEach(b => b.addEventListener("click", () => ack(b.dataset.ack)));
    $("alerts").querySelectorAll("button[data-open]").forEach(b => b.addEventListener("click", () => openDetail(b.dataset.open)));
  }

  function renderFeed(reports) {
    if (!reports.length) { $("feed").innerHTML = `<li class="empty">${t("no_feed")}</li>`; return; }
    reports.forEach(r => { if (!seenReports.has(r.id)) { seenReports.add(r.id); if (seenReports.size > reports.length) log(`👤 ${r.route_number}: ${t(r.level)}${r.stop_name ? " (" + r.stop_name + ")" : ""}`); } });
    $("feed").innerHTML = reports.map(r => `<li><span class="line-num" style="background:${r.route_color}">${r.route_number}</span> ${badge(r.level)}
      <span class="muted">${r.plate ? "🚌 " + r.plate + " · " : ""}${r.stop_name || t("on_route")} · ${new Date(r.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span></li>`).join("");
  }

  function renderBuses(buses) {
    buses.forEach(b => {
      const dim = selected && b.route_id !== selected;
      const icon = L.divIcon({ className: "", iconAnchor: [5, 5], html: `<div style="width:${dim ? 8 : 12}px;height:${dim ? 8 : 12}px;border-radius:50%;background:${LEVEL_COLOR[b.load_level]};opacity:${dim ? .35 : 1};border:1.5px solid #fff;box-shadow:0 0 2px rgba(0,0,0,.5)"></div>` });
      const tip = `${b.route_number} · ${b.plate} · ${b.speed_kmh} km/s · → ${b.next_stop || "—"}`;
      if (busMarkers[b.id]) busMarkers[b.id].setLatLng([b.lat, b.lon]).setIcon(icon).setTooltipContent(tip);
      else busMarkers[b.id] = L.marker([b.lat, b.lon], { icon }).bindTooltip(tip).addTo(busLayer);
    });
  }

  // --- detal görünüşü ---
  async function openDetail(id) {
    selected = id; dir = 1;
    document.querySelectorAll("#view-detail .dir-toggle button").forEach(b => b.classList.toggle("sel", b.dataset.dir === "1"));
    $("view-list").hidden = true; $("view-detail").hidden = false;
    detail = await api(`/api/routes/${id}`);
    $("d-number").textContent = detail.number; $("d-badge").textContent = detail.number; $("d-badge").style.background = detail.color;
    $("d-name").textContent = detail.name; $("d-carrier").textContent = detail.carrier || "—";
    $("d-len").textContent = `${(detail.length_m / 1000).toFixed(1)} km`; $("d-duration").textContent = `${detail.duration_min || "?"} ${t("min")}`;
    $("d-stops").textContent = `${detail.stops.length} ${t("stops_n")}`;
    detailLayer.clearLayers();
    const line = L.polyline(detail.polyline, { color: detail.color, weight: 7, opacity: 0.95 }).addTo(detailLayer);
    detail.stops.forEach(s => L.circleMarker([s.lat, s.lon], { radius: 5, color: "#fff", weight: 2, fillColor: detail.color, fillOpacity: 1 }).bindTooltip(s.name).on("click", e => { L.DomEvent.stop(e); openStopPopup(s); }).addTo(detailLayer));
    map.fitBounds(line.getBounds(), { padding: [40, 40] });
    Object.values(linePolys).forEach(p => p && p.setStyle({ opacity: 0.2 }));
    renderDetailStats(); renderDetailTimeline();
  }
  function renderDetailStats() {
    const l = lastLines.find(x => x.id === selected); if (!l) return;
    $("d-load").innerHTML = badge(l.load.level) + (l.load.score ? ` <span class="muted">${l.load.score.toFixed(2)}</span>` : "");
    $("d-reports").innerHTML = sources(l.report_sources); $("d-buses").textContent = l.bus_count; $("d-speed").textContent = `${l.avg_speed_kmh} km/s`;
    $("d-bunching").innerHTML = l.bunching ? `<span class="flag">${t("bunching_yes")}</span>` : t("normal");
    $("d-high").innerHTML = l.high_for_minutes ? `<div class="bar" style="display:inline-block;vertical-align:middle"><div style="width:${Math.min(100, Math.round(l.high_for_minutes / l.anomaly_threshold_minutes * 100))}%"></div></div> ${l.high_for_minutes} / ${l.anomaly_threshold_minutes} ${t("min")}` : "—";
  }
  async function renderDetailTimeline() {
    if (!selected) return;
    try {
      const d = await api(`/api/routes/${selected}/timeline`);
      $("d-timeline").innerHTML = d.stops.filter(s => s.direction === dir).map((s, i) => `<div class="tl-row"><span class="tl-name"><span class="muted">${i + 1}.</span> ${s.name}</span><span class="muted">${s.leg_seconds ? "+" + Math.round(s.leg_seconds / 60) : ""}</span><span class="tl-eta">${mins(s.next_bus.eta_seconds)}</span></div>`).join("");
    } catch (e) { if (e.message !== "login") $("d-timeline").innerHTML = `<div class="empty">${e.message}</div>`; }
  }
  function closeDetail() {
    selected = null; detail = null; detailLayer.clearLayers();
    $("view-list").hidden = false; $("view-detail").hidden = true;
    Object.values(linePolys).forEach(p => p && p.setStyle({ opacity: 0.75 }));
  }

  async function refresh() {
    try {
      const [lines, alerts, buses, feed] = await Promise.all([
        api("/api/operator/lines"), api("/api/operator/alerts?status=all&limit=20"), api("/api/buses"), api("/api/reports/recent?source=passenger&limit=12")]);
      renderLines(lines);
      renderAlerts(alerts.filter(a => a.status !== "resolved").concat(alerts.filter(a => a.status === "resolved").slice(0, 2)));
      const drawn = new Set(lines.filter(l => l.load.level !== "no_data" || l.monitored || l.id === selected).map(l => l.id));
      renderBuses(buses.filter(b => drawn.has(b.route_id)));
      renderFeed(feed);
      if (selected) renderDetailTimeline();
    } catch (e) { if (e.message !== "login") log(t("error") + ": " + e.message); }
  }
  async function ack(id) { try { await api(`/api/operator/alerts/${id}/ack`, { method: "POST" }); log(`✔ #${id}`); await refresh(); } catch (e) { log(e.message); } }
  async function demo(routeId) {
    try { const res = await api(`/api/operator/demo/high-load/${routeId}`, { method: "POST" }); log(`Demo ${routeId}: +${res.created_alerts.length} ⚠`); await refresh(); }
    catch (e) { log(e.message); }
  }

  $("line-filter").addEventListener("input", () => renderLines(lastLines));
  $("only-data").addEventListener("change", () => renderLines(lastLines));
  $("back").addEventListener("click", closeDetail);
  $("d-demo").addEventListener("click", () => selected && demo(selected));
  document.querySelectorAll("#view-detail .dir-toggle button").forEach(b => b.addEventListener("click", () => { dir = +b.dataset.dir; document.querySelectorAll("#view-detail .dir-toggle button").forEach(x => x.classList.toggle("sel", x === b)); renderDetailTimeline(); }));
  $("logout").addEventListener("click", async () => { await fetch("/api/auth/logout", { method: "POST" }); location.href = "/login"; });
  document.addEventListener("langchange", () => { renderLines(lastLines); if (selected) { renderDetailStats(); renderDetailTimeline(); } });

  (async function init() {
    const me = await api("/api/auth/me");
    if (!me.user || me.user.role !== "operator") { location.href = "/login?need=operator"; return; }
    $("user").textContent = me.user.full_name || me.user.username;
    await refresh(); setInterval(refresh, REFRESH_MS);
  })().catch(e => { if (e.message !== "login") log(e.message); });
})();
