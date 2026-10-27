/* Landed front-end. Vanilla JS + Motion (https://motion.dev, vanilla build). */
(() => {
  "use strict";
  const { animate, stagger } = window.Motion;
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const anim = (el, kf, opts = {}) => animate(el, kf, reduce ? { ...opts, duration: 0, delay: 0 } : opts);

  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  const STATUSES = [
    { key: "saved", label: "Saved", dot: "#9AA5B8" },
    { key: "applied", label: "Applied", dot: "#F2C230" },
    { key: "interview", label: "Interview", dot: "#5B7BEA" },
    { key: "offer", label: "Offer", dot: "#2E8B57" },
    { key: "rejected", label: "Rejected", dot: "#C8483B" },
  ];
  const SECTION_NAMES = { header: "Header", summary: "Profile", education: "Education", experience: "Experience",
    projects: "Projects", skills: "Skills", languages: "Languages", activities: "Activities" };

  const state = { cv: null, offers: [], selected: null, generated: {}, apps: [], source: "demo", view: "profile" };

  // ------------------------------------------------------------------ helpers
  async function api(path, opts = {}) {
    const init = { ...opts };
    if (opts.json !== undefined) {
      init.method = opts.method || "POST";
      init.headers = { "Content-Type": "application/json" };
      init.body = JSON.stringify(opts.json);
    }
    const r = await fetch(path, init);
    if (!r.ok) {
      let msg = `Request failed (${r.status})`;
      try { msg = (await r.json()).detail || msg; } catch (_) { /* not json */ }
      throw new Error(msg);
    }
    const type = r.headers.get("content-type") || "";
    return type.includes("json") ? r.json() : r.blob();
  }

  let toastTimer;
  function toast(msg, error = false) {
    const t = $("#toast");
    t.textContent = msg;
    t.classList.toggle("error", error);
    t.hidden = false;
    anim(t, { opacity: [0, 1], y: [12, 0] }, { duration: 0.25 });
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => (t.hidden = true), error ? 6000 : 3000);
  }

  function download(blob, name) {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = name;
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 2000);
  }
  const slug = (s) => String(s || "file").toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "").slice(0, 40);

  // Split-flap: each letter cycles through random characters, then settles.
  const FLAP_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
  function flapText(el, text, { asTiles = false } = {}) {
    const letters = [...text];
    el.textContent = "";
    const spans = letters.map((ch) => {
      const s = document.createElement("span");
      if (asTiles) s.className = ch === " " ? "" : "flap";
      s.textContent = ch === " " ? " " : ch;
      el.appendChild(s);
      return s;
    });
    if (reduce) return;
    spans.forEach((s, i) => {
      const final = letters[i];
      if (final === " ") return;
      let n = 0;
      const turns = 6 + i * 2;
      const tick = () => {
        if (n++ < turns) {
          s.textContent = FLAP_CHARS[Math.floor(Math.random() * FLAP_CHARS.length)];
          setTimeout(tick, 38);
        } else {
          s.textContent = final;
          anim(s, { rotateX: [-80, 0] }, { duration: 0.18 });
        }
      };
      tick();
    });
  }

  // ------------------------------------------------------------------ navigation
  function go(view) {
    if (view !== "profile" && !state.cv) {
      toast("Add your CV first — Landed needs it to find matching offers.");
      view = "profile";
    }
    state.view = view;
    $$(".step[data-go]").forEach((b) => b.setAttribute("aria-current", b.dataset.go === view ? "page" : "false"));
    $$(".view").forEach((v) => (v.hidden = v.dataset.view !== view));
    const el = $(`#view-${view}`);
    anim(el, { opacity: [0, 1], y: [6, 0] }, { duration: 0.22, ease: "easeOut" });
    if (view === "board") loadBoard();
    if (view === "offers" && !state.offers.length) runSearch();
    if (view !== "offers") window.scrollTo({ top: 0 });
  }
  document.addEventListener("click", (e) => {
    const t = e.target.closest("[data-go]");
    if (t) { e.preventDefault(); go(t.dataset.go); }
  });

  // ------------------------------------------------------------------ engine status
  async function loadStatus() {
    try {
      const s = await api("/api/status");
      if (!s.adzuna) { $('[data-src="adzuna"]')?.setAttribute("title", "Add your free Adzuna keys in .env to search live offers (adzuna.com)"); }
      state.adzuna = s.adzuna;
    } catch (_) { /* server not ready */ }
  }

  // ------------------------------------------------------------------ CV
  function renderProfile(cv) {
    state.cv = cv;
    document.body.classList.add("has-cv");
    $("#cv-bar-text").textContent = `Matching with ${cv.name ? cv.name + "'s" : "your"} CV. Replace it anytime and offers are re-ranked.`;
    $("#profile").hidden = false;
    $("#p-name").textContent = cv.name || "Your CV";
    const nSec = Object.keys(cv.sections || {}).filter((k) => k !== "header").length;
    $("#p-meta").textContent = `${cv.email ? cv.email + ". " : ""}${cv.skills.length} skills and ${nSec} sections detected.`;
    const groups = {};
    cv.skills.forEach((s) => { const c = window.SKILL_CAT?.[s] || categoryOf(s); (groups[c] ||= []).push(s); });
    $("#p-skills").innerHTML = Object.entries(groups).map(([cat, list]) =>
      `<div class="skill-group"><span>${esc(cat)}</span><div class="chips">${list.map((s) => `<span class="chip">${esc(s)}</span>`).join("")}</div></div>`
    ).join("") || `<p class="muted">No known skills found. Check that your CV is a text PDF, not a scan.</p>`;
    $("#p-sections").innerHTML = Object.entries(cv.sections || {}).map(([k, lines]) =>
      `<div class="sec"><b>${esc(SECTION_NAMES[k] || k)}</b>${lines.slice(0, 6).map((l) => `<p>${esc(l)}</p>`).join("")}${lines.length > 6 ? `<p>+ ${lines.length - 6} more lines</p>` : ""}</div>`
    ).join("");
    anim($$(".skill-group .chip"), { opacity: [0, 1], scale: [0.85, 1] }, { delay: stagger(0.025), duration: 0.25 });
    state.offers = []; state.generated = {}; state.selected = null;
  }
  // light client-side copy of the categories (display only)
  const CAT = {
    Tech: "Python R SQL Java JavaScript React C++ Git Docker Cloud APIs Linux Spark",
    "Data & AI": "Machine Learning|Deep Learning|NLP|Computer Vision|Statistics|Data Analysis|Data Visualization|Power BI|Tableau|Excel|Generative AI|Data Engineering",
    Business: "Financial Analysis|Accounting|Corporate Finance|Market Research|Strategy|Project Management|Product Management|Business Development|Sales|Supply Chain|Operations|HR|Sustainability",
    Marketing: "Digital Marketing|SEO|Social Media|Content Creation|Brand Management|Google Analytics|Design|Communication",
    "Soft skills": "Teamwork|Leadership|Problem Solving|Presentation|Autonomy",
    Languages: "English|French|Spanish|German|Italian|Chinese|Arabic",
  };
  function categoryOf(skill) {
    for (const [cat, list] of Object.entries(CAT)) {
      const items = list.includes("|") ? list.split("|") : list.split(" ");
      if (items.includes(skill)) return cat;
    }
    return "Other";
  }

  async function uploadCV(file) {
    const fd = new FormData();
    fd.append("file", file);
    const drop = $("#drop");
    drop.querySelector("strong").textContent = "Reading your CV…";
    try {
      renderProfile(await api("/api/cv", { method: "POST", body: fd }));
      toast("CV loaded — finding your best matches…");
      go("offers");
    } catch (err) {
      toast(err.message, true);
    } finally {
      drop.querySelector("strong").textContent = "Drop your CV here or choose a file";
    }
  }
  $("#cv-file").addEventListener("change", (e) => e.target.files[0] && uploadCV(e.target.files[0]));
  const drop = $("#drop");
  drop.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); $("#cv-file").click(); } });
  ["dragenter", "dragover"].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add("over"); }));
  ["dragleave", "drop"].forEach((ev) => drop.addEventListener(ev, () => drop.classList.remove("over")));
  drop.addEventListener("drop", (e) => { e.preventDefault(); const f = e.dataTransfer.files[0]; if (f) uploadCV(f); });
  $("#sample-cv").addEventListener("click", async () => {
    try {
      renderProfile(await api("/api/cv/sample", { method: "POST" }));
      toast("Sample CV loaded — finding matches…");
      go("offers");
    } catch (err) { toast(err.message, true); }
  });

  $("#replace-cv").addEventListener("click", () => $("#cv-file").click());

  // CV text paste
  $("#show-cv-paste").addEventListener("click", () => {
    $("#cv-paste-area").hidden = false;
    $("#cv-text").focus();
  });
  $("#hide-cv-paste").addEventListener("click", () => { $("#cv-paste-area").hidden = true; });
  $("#use-cv-text").addEventListener("click", async () => {
    const text = $("#cv-text").value.trim();
    if (!text) { toast("Paste some text first.", true); return; }
    try {
      renderProfile(await api("/api/cv/text", { json: { text } }));
      toast("CV loaded — finding your best matches…");
      $("#cv-paste-area").hidden = true;
      $("#cv-text").value = "";
      go("offers");
    } catch (err) { toast(err.message, true); }
  });

  // home teaser: one orchestrated moment on first load
  function playTeaser() {
    flapText($("#teaser-title"), "DEPARTURES", { asTiles: true });
    $$(".teaser [data-flap]").forEach((td, i) => setTimeout(() => flapText(td, td.dataset.flap), 500 + i * 260));
  }

  // ------------------------------------------------------------------ offers
  $$(".toggle button").forEach((b) => b.addEventListener("click", () => {
    if (b.dataset.src === "adzuna" && !state.adzuna) {
      toast("Live search needs free Adzuna keys in the .env file — see adzuna.com/developer.", true);
      return;
    }
    state.source = b.dataset.src;
    $$(".toggle button").forEach((x) => x.setAttribute("aria-checked", x === b ? "true" : "false"));
  }));
  $("#search").addEventListener("submit", (e) => { e.preventDefault(); runSearch(); });

  async function runSearch() {
    const list = $("#offer-list");
    list.innerHTML = `<li class="thinking"><span class="plane"><i></i></span>Ranking offers against your CV…</li>`;
    loader(list);
    try {
      const { offers } = await api("/api/offers/search", { json: { source: state.source, keywords: $("#q").value, location: $("#loc").value } });
      state.offers = offers;
      await refreshApps();
      renderOffers();
      if (offers.length) selectOffer(offers[0].id, false);
    } catch (err) {
      list.innerHTML = `<li class="detail empty">${esc(err.message)}</li>`;
    }
  }

  function loader(scope) {
    const bar = scope.querySelector(".plane i");
    if (bar && !reduce) animate(bar, { x: ["-100%", "340%"] }, { duration: 1.1, repeat: Infinity, ease: "easeInOut" });
  }

  function scoreRing(score) {
    const r = 23, c = 2 * Math.PI * r;
    const cls = score >= 60 ? "high" : score >= 40 ? "mid" : "";
    return `<div class="score ${cls}" data-score="${score}">
      <svg viewBox="0 0 56 56"><circle class="track" cx="28" cy="28" r="${r}"/><circle class="val" cx="28" cy="28" r="${r}" stroke-dasharray="${c}" stroke-dashoffset="${c}"/></svg>
      <span>0</span></div>`;
  }
  function playRings(scope) {
    $$(".score", scope).forEach((el, i) => {
      const score = +el.dataset.score, circle = el.querySelector(".val"), label = el.querySelector("span");
      const c = 2 * Math.PI * 23;
      anim(circle, { strokeDashoffset: [c, c * (1 - score / 100)] }, { duration: 0.8, delay: i * 0.04, ease: "easeOut" });
      if (reduce) { label.textContent = score; return; }
      animate(0, score, { duration: 0.8, delay: i * 0.04, ease: "easeOut", onUpdate: (v) => (label.textContent = Math.round(v)) });
    });
  }

  const trackedIds = () => new Set(state.apps.map((a) => a.offer_id));

  function renderOffers() {
    const list = $("#offer-list");
    const tracked = trackedIds();
    if (!state.offers.length) {
      list.innerHTML = `<li class="muted">No results. Try different keywords, or paste an offer on the right.</li>`;
      const pi = $("#paste-inline"); if (pi) pi.hidden = false;
      return;
    }
    list.innerHTML = state.offers.map((o) => `
      <li class="offer" role="option" tabindex="0" data-id="${esc(o.id)}" aria-selected="false">
        ${scoreRing(o.score)}
        <div>
          <h3>${esc(o.title)}${tracked.has(o.id) ? `<span class="tracked">On your board</span>` : ""}</h3>
          <p class="meta">${esc(o.company)}${o.location ? ", " + esc(o.location) : ""}</p>
          <div class="chips">${o.matched_skills.slice(0, 4).map((s) => `<span class="chip match">${esc(s)}</span>`).join("")}${o.missing_skills.slice(0, 2).map((s) => `<span class="chip missing">${esc(s)}</span>`).join("")}</div>
        </div>
      </li>`).join("");
    anim($$(".offer", list), { opacity: [0, 1], x: [-12, 0] }, { delay: stagger(0.035), duration: 0.3 });
    playRings(list);
  }
  $("#offer-list").addEventListener("click", (e) => { const li = e.target.closest(".offer"); if (li) selectOffer(li.dataset.id); });
  $("#offer-list").addEventListener("keydown", (e) => {
    const li = e.target.closest(".offer");
    if (li && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); selectOffer(li.dataset.id); }
  });

  function selectOffer(id, scroll = true) {
    const o = state.offers.find((x) => x.id === id);
    if (!o) return;
    state.selected = o;
    $$(".offer").forEach((li) => li.setAttribute("aria-selected", li.dataset.id === id ? "true" : "false"));
    renderDetail(o);
    if (scroll && window.innerWidth < 960) $("#detail").scrollIntoView({ behavior: reduce ? "auto" : "smooth" });
  }

  function renderDetail(o) {
    const d = $("#detail");
    const pi = $("#paste-inline");
    if (pi) pi.hidden = true;
    const tracked = trackedIds().has(o.id);
    d.innerHTML = `
      <div style="display:flex;gap:18px;align-items:center">${scoreRing(o.score)}
        <div><h2>${esc(o.title)}</h2><p class="meta" style="margin:2px 0 0">${esc(o.company)}${o.location ? ", " + esc(o.location) : ""}. ${esc(o.source)}${o.url ? `. <a href="${esc(o.url)}" target="_blank" rel="noopener">Open the original offer</a>` : ""}</p></div></div>
      <div class="why">
        <div class="bar"><span>Meaning of CV and offer</span><span class="track"><span class="fill" style="width:${o.semantic}%"></span></span><b>${o.semantic}</b></div>
        <div class="bar"><span>Required skills you have</span><span class="track"><span class="fill" style="width:${o.coverage}%"></span></span><b>${o.coverage}</b></div>
      </div>
      <h3>You have</h3>
      <div class="chips">${o.matched_skills.map((s) => `<span class="chip match">${esc(s)}</span>`).join("") || `<span class="muted">No listed skill in common.</span>`}</div>
      <h3>The offer also asks for</h3>
      <div class="chips">${o.missing_skills.map((s) => `<span class="chip missing">${esc(s)}</span>`).join("") || `<span class="muted">Nothing missing. You cover every skill we detected.</span>`}</div>
      <h3>Offer</h3>
      <div class="desc">${esc(o.description)}</div>
      <div class="actions">
        <button class="btn primary" id="gen-btn">Write my cover letter and CV</button>
        <button class="btn ghost" id="save-btn">${tracked ? "On your board" : "Save to board"}</button>
      </div>
      <div id="gen-area"></div>
      <div class="bias-panel" id="bias-panel">
        <h3>Bias check</h3>
        <p class="muted" style="margin:2px 0 10px;font-size:14px">Wording analysis (legal risk, exclusionary language, gender coding) and a counterfactual fairness test that replays our own scoring with different candidate names.</p>
        <div class="bias-actions">
          <button class="btn ghost" id="bias-btn">Analyse offer wording</button>
          <button class="btn ghost" id="cftest-btn">Test our score for bias</button>
        </div>
        <div id="bias-result" hidden></div>
      </div>`;
    anim(d, { opacity: [0.4, 1] }, { duration: 0.2 });
    anim($$(".bar .fill", d), { scaleX: [0, 1] }, { duration: 0.6, ease: "easeOut", delay: stagger(0.1) });
    playRings(d);
    $("#gen-btn").addEventListener("click", () => generate(o));
    $("#save-btn").addEventListener("click", () => saveToBoard(o, "saved"));
    $("#bias-btn").addEventListener("click", () => runBiasCheck(o));
    $("#cftest-btn").addEventListener("click", () => runCfTest(o));
    if (state.generated[o.id]) renderGenerated(o, state.generated[o.id]);
  }

  async function generate(o) {
    const area = $("#gen-area");
    const btn = $("#gen-btn");
    btn.disabled = true;
    area.innerHTML = `<div class="gen"><div class="thinking"><span class="plane"><i></i></span>Writing from your CV only. On a laptop without GPU this can take a minute.</div></div>`;
    loader(area);
    try {
      const res = await api("/api/generate", { json: { offer: o } });
      state.generated[o.id] = res;
      renderGenerated(o, res);
    } catch (err) {
      area.innerHTML = `<div class="gen warning">${esc(err.message)}</div>`;
    } finally {
      btn.disabled = false;
      btn.textContent = "Write a new version";
    }
  }

  function flagsBox(flags, what) {
    if (!flags.length) return `<div class="ok">Checked: every skill mentioned in this ${what} appears in your CV.</div>`;
    return `<div class="warning"><span>⚠</span><span>This ${what} mentions skills that are not in your CV: ${flags.map((f) => `<span class="chip flag">${esc(f)}</span>`).join(" ")}. Remove them or make sure you can back them up.</span></div>`;
  }

  function cvPreview(cv) {
    const sec = Object.entries(cv.sections).map(([k, lines]) =>
      `<h4>${esc(SECTION_NAMES[k] || k)}</h4>${lines.map((l) => `<p class="${/^[-•*–▪]/.test(l) ? "b" : ""}">${esc(l)}</p>`).join("")}`).join("");
    return `<div class="cv-preview">
      <div class="name">${esc(cv.header[0] || "")}</div>${cv.header.slice(1).map((h) => `<p class="muted">${esc(h)}</p>`).join("")}
      <h4>Profile</h4><p class="summary">${esc(cv.summary)}</p>
      <h4>Skills</h4><div class="chips">${cv.skills.map((s) => `<span class="chip ${cv.highlighted_skills.includes(s) ? "match" : ""}">${esc(s)}</span>`).join("")}</div>
      ${sec}</div>`;
  }

  function renderGenerated(o, res) {
    const area = $("#gen-area");
    const engine = res.letter.engine === "template" ? "Written with the built-in template (no local LLM found)." : `Written by ${esc(res.engine)} on your computer.`;
    area.innerHTML = `<div class="gen">
      <div class="gen-tabs" role="tablist">
        <button role="tab" aria-selected="true" data-tab="letter">Cover letter</button>
        <button role="tab" aria-selected="false" data-tab="cv">Tailored CV</button>
      </div>
      <div data-panel="letter">
        ${flagsBox(res.letter.flags, "letter")}
        <label class="muted" for="letter-text" style="font-size:14px">${engine} Edit freely before you send it.</label>
        <textarea id="letter-text" class="letter">${esc(res.letter.text)}</textarea>
      </div>
      <div data-panel="cv" hidden>
        ${flagsBox(res.cv.flags, "CV")}
        <p class="muted" style="font-size:14px;margin-top:0">Same facts as your CV. Skills this offer asks for come first, and your bullet points are reordered by relevance inside each experience.</p>
        ${cvPreview(res.cv)}
      </div>
      <div class="actions">
        <button class="btn dark" id="dl-letter">Download letter (.docx)</button>
        <button class="btn ghost" id="dl-cv">Download CV (.docx)</button>
        <button class="btn primary" id="applied-btn">Add to board as applied</button>
      </div></div>`;
    anim(area.firstElementChild, { opacity: [0, 1], y: [10, 0] }, { duration: 0.35 });
    $$(".gen-tabs button", area).forEach((b) => b.addEventListener("click", () => {
      $$(".gen-tabs button", area).forEach((x) => x.setAttribute("aria-selected", x === b ? "true" : "false"));
      $$("[data-panel]", area).forEach((p) => (p.hidden = p.dataset.panel !== b.dataset.tab));
      anim($(`[data-panel="${b.dataset.tab}"]`, area), { opacity: [0, 1] }, { duration: 0.2 });
    }));
    $("#letter-text").addEventListener("input", (e) => { res.letter.text = e.target.value; });
    $("#dl-letter").addEventListener("click", async () =>
      download(await api("/api/export/letter", { json: { text: res.letter.text } }), `cover_letter_${slug(o.company)}.docx`));
    $("#dl-cv").addEventListener("click", async () =>
      download(await api("/api/export/cv", { json: { cv: res.cv } }), `cv_${slug(o.company)}.docx`));
    $("#applied-btn").addEventListener("click", () => saveToBoard(o, "applied", res));
  }

  // ------------------------------------------------------------------ bias panel
  function renderBiasWording(r) {
    const parts = [];
    if (!r.legal.length && !r.exclusionary.length) {
      parts.push(`<div class="ok">No legal risk or exclusionary wording detected.</div>`);
    }
    if (r.legal.length) {
      parts.push(`<div class="bias-section legal"><b>Legal risk — ${r.legal.length} flag${r.legal.length > 1 ? "s" : ""}</b>${
        r.legal.map((f) => `<div class="bias-flag">
          <span class="bias-match">${esc(f.match)}</span>
          <p>${esc(f.explanation)}</p>
          <p class="suggestion">Suggestion: ${esc(f.suggestion)}</p>
        </div>`).join("")}</div>`);
    }
    if (r.exclusionary.length) {
      parts.push(`<div class="bias-section excl"><b>Exclusionary wording — ${r.exclusionary.length} flag${r.exclusionary.length > 1 ? "s" : ""}</b>${
        r.exclusionary.map((f) => `<div class="bias-flag">
          <span class="bias-match">${esc(f.match)}</span>
          <p>${esc(f.explanation)}</p>
          <p class="suggestion">Suggestion: ${esc(f.suggestion)}</p>
        </div>`).join("")}</div>`);
    }
    const hasMasc = r.gender_masc.length > 0, hasFem = r.gender_fem.length > 0;
    parts.push(`<div class="bias-section gender"><b>Gender-coded wording</b>
      <p class="muted" style="font-size:14px">${esc(r.gender_note)}</p>
      ${hasMasc ? `<p style="margin:4px 0">Masculine signals: ${r.gender_masc.map((s) => `<span class="chip flag-masc">${esc(s)}</span>`).join(" ")}</p>` : ""}
      ${hasFem ? `<p style="margin:4px 0">Feminine signals: ${r.gender_fem.map((s) => `<span class="chip flag-fem">${esc(s)}</span>`).join(" ")}</p>` : ""}
    </div>`);
    return parts.join("");
  }

  function renderCfResult(r) {
    const cls = r.verdict === "fair" ? "ok" : "warning";
    return `<div class="${cls}">${esc(r.explanation)}</div>
    <table class="cf-table">
      <thead><tr><th>Name variant</th><th>Score</th><th>Semantic</th><th>Skill match</th></tr></thead>
      <tbody>${r.results.map((row) => `<tr><td>${esc(row.name)}</td><td>${row.score}</td><td>${row.semantic}</td><td>${row.coverage}</td></tr>`).join("")}</tbody>
    </table>`;
  }

  async function runBiasCheck(o) {
    const result = $("#bias-result");
    result.hidden = false;
    result.innerHTML = `<p class="muted" style="font-size:14px">Checking wording…</p>`;
    try {
      const r = await api("/api/bias/offer", { json: { description: o.description } });
      result.innerHTML = `<h4 style="margin:12px 0 8px">Wording analysis</h4>` + renderBiasWording(r);
    } catch (err) {
      result.innerHTML = `<div class="warning">${esc(err.message)}</div>`;
    }
  }

  async function runCfTest(o) {
    const result = $("#bias-result");
    result.hidden = false;
    result.innerHTML = `<div class="thinking"><span class="plane"><i></i></span>Testing 3 name variants against your CV…</div>`;
    loader(result);
    try {
      const r = await api("/api/bias/test", { json: { offer: o } });
      result.innerHTML = `<h4 style="margin:12px 0 8px">Counterfactual fairness test</h4>` + renderCfResult(r);
    } catch (err) {
      result.innerHTML = `<div class="warning">${esc(err.message)}</div>`;
    }
  }

  async function saveToBoard(o, status, res = state.generated[o.id]) {
    try {
      await api("/api/applications", { json: {
        offer_id: o.id, title: o.title, company: o.company, location: o.location, url: o.url,
        source: o.source, score: o.score, status,
        letter: res ? res.letter.text : "", cv_summary: res ? res.cv.summary : "",
      } });
      await refreshApps();
      toast(status === "applied" ? "Added to your board as applied." : "Saved to your board.");
      const sb = $("#save-btn"); if (sb) sb.textContent = "On your board";
      renderOffers(); $$(".offer").forEach((li) => li.setAttribute("aria-selected", li.dataset.id === o.id ? "true" : "false"));
    } catch (err) { toast(err.message, true); }
  }

  // ------------------------------------------------------------------ editor drawer
  function openDrawer(id) {
    const d = $(id);
    $("#scrim").hidden = false; d.hidden = false;
    anim(d, { x: ["100%", "0%"] }, { duration: 0.35, ease: [0.2, 0.8, 0.2, 1] });
    anim($("#scrim"), { opacity: [0, 1] }, { duration: 0.25 });
    setTimeout(() => d.querySelector("input, textarea, button")?.focus(), 50);
  }
  async function closeDrawers() {
    const open = $$(".drawer").filter((d) => !d.hidden);
    await Promise.all(open.map((d) => anim(d, { x: ["0%", "100%"] }, { duration: 0.25 }).finished));
    open.forEach((d) => (d.hidden = true));
    $("#scrim").hidden = true;
  }
  $("#scrim").addEventListener("click", closeDrawers);
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeDrawers(); });
  document.addEventListener("click", (e) => { if (e.target.closest("[data-close]")) closeDrawers(); });

  // ------------------------------------------------------------------ paste inline
  $("#paste-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = e.target.querySelector("[type=submit]");
    btn.disabled = true;
    try {
      const { offer } = await api("/api/offers/manual", { json: {
        title: $("#m-title").value, company: $("#m-company").value, description: $("#m-desc").value,
        url: $("#m-url").value, source: $("#m-source").value,
      } });
      state.offers = [offer, ...state.offers.filter((o) => o.id !== offer.id)];
      e.target.reset();
      renderOffers();
      selectOffer(offer.id);
      toast(`Scored ${offer.score}/100 against your CV.`);
    } catch (err) { toast(err.message, true); }
    finally { btn.disabled = false; }
  });

  // ------------------------------------------------------------------ board
  async function refreshApps() { state.apps = await api("/api/applications"); }

  async function loadBoard() {
    try {
      await refreshApps();
      const stats = await api("/api/stats");
      renderStats(stats);
      renderBoard();
    } catch (err) { toast(err.message, true); }
  }

  function renderStats(s) {
    $("#stats").innerHTML = [
      ["Tracked", s.total], ["Sent", s.sent], ["Response rate", s.response_rate + "%"],
      ["Interview rate", s.interview_rate + "%"], ["Average match", s.avg_score || "–"],
    ].map(([k, v]) => `<div><dt>${k}</dt><dd>${v}</dd></div>`).join("");
    const fu = $("#followups");
    fu.hidden = !s.follow_ups.length;
    fu.innerHTML = s.follow_ups.length
      ? `Time to follow up: ${s.follow_ups.map((a) => `<button class="link" data-edit="${a.id}">${esc(a.company)}</button> (${a.days_since_applied} days)`).join(", ")}.`
      : "";
  }

  function cardHTML(a) {
    return `<li class="card" draggable="true" tabindex="0" data-id="${a.id}">
      <h4>${esc(a.title)}</h4><p class="co">${esc(a.company)}</p>
      <div class="row"><span class="st">${a.applied_at ? "Applied " + esc(a.applied_at) : esc(a.source || "")}</span>${a.score != null ? `<span class="pct">${a.score}</span>` : ""}</div>
      ${a.next_step ? `<p class="next">Next: ${esc(a.next_step)}${a.next_step_date ? ", " + esc(a.next_step_date) : ""}</p>` : ""}
      ${a.follow_up ? `<p class="fu">Follow up: ${a.days_since_applied} days without news</p>` : ""}
    </li>`;
  }

  function renderBoard() {
    const board = $("#board");
    board.innerHTML = STATUSES.map((s) => {
      const items = state.apps.filter((a) => a.status === s.key);
      return `<section class="col" data-status="${s.key}" aria-label="${s.label}">
        <header><span><span class="dot" style="background:${s.dot}"></span>${s.label}</span><span class="count">${items.length}</span></header>
        <ul>${items.map(cardHTML).join("") || (s.key === "saved" ? `<li class="empty-col">Save offers from Matching Offers to see them here.</li>` : `<li class="empty-col">Drag a card here.</li>`)}</ul>
      </section>`;
    }).join("");
    anim($$(".card", board), { opacity: [0, 1], y: [10, 0] }, { delay: stagger(0.03), duration: 0.3 });
  }

  // drag & drop between columns
  let dragId = null;
  const board = $("#board");
  board.addEventListener("dragstart", (e) => {
    const c = e.target.closest(".card"); if (!c) return;
    dragId = +c.dataset.id; e.dataTransfer.effectAllowed = "move"; e.dataTransfer.setData("text/plain", dragId);
    anim(c, { opacity: 0.5 }, { duration: 0.1 });
  });
  board.addEventListener("dragend", (e) => { const c = e.target.closest(".card"); if (c) anim(c, { opacity: 1 }, { duration: 0.1 }); });
  board.addEventListener("dragover", (e) => {
    const col = e.target.closest(".col"); if (!col) return;
    e.preventDefault();
    $$(".col").forEach((x) => x.classList.toggle("drag-over", x === col));
  });
  board.addEventListener("dragleave", (e) => { if (!board.contains(e.relatedTarget)) $$(".col").forEach((x) => x.classList.remove("drag-over")); });
  board.addEventListener("drop", async (e) => {
    const col = e.target.closest(".col"); $$(".col").forEach((x) => x.classList.remove("drag-over"));
    if (!col || dragId == null) return;
    e.preventDefault();
    await moveCard(dragId, col.dataset.status);
    dragId = null;
  });
  board.addEventListener("click", (e) => { const c = e.target.closest(".card"); if (c) openEditor(+c.dataset.id); });
  board.addEventListener("keydown", (e) => {
    const c = e.target.closest(".card"); if (!c) return;
    if (e.key === "Enter") openEditor(+c.dataset.id);
    // keyboard move: Alt + arrow left/right
    if (e.altKey && (e.key === "ArrowRight" || e.key === "ArrowLeft")) {
      const a = state.apps.find((x) => x.id === +c.dataset.id);
      const i = STATUSES.findIndex((s) => s.key === a.status) + (e.key === "ArrowRight" ? 1 : -1);
      if (STATUSES[i]) moveCard(a.id, STATUSES[i].key, true);
    }
  });
  $("#followups").addEventListener("click", (e) => { const b = e.target.closest("[data-edit]"); if (b) openEditor(+b.dataset.edit); });

  async function moveCard(id, status, refocus = false) {
    const a = state.apps.find((x) => x.id === id);
    if (!a || a.status === status) return;
    try {
      await api(`/api/applications/${id}`, { method: "PATCH", json: { status } });
      await loadBoard();
      const card = $(`.card[data-id="${id}"]`);
      if (card) {
        anim(card, { backgroundColor: ["#F2C230", "#FFFFFF"], scale: [1.04, 1] }, { duration: 0.6 });
        const label = STATUSES.find((s) => s.key === status).label.toUpperCase();
        const st = card.querySelector(".st");
        flapText(st, label);
        setTimeout(() => { st.textContent = state.apps.find((x) => x.id === id)?.applied_at ? "Applied " + state.apps.find((x) => x.id === id).applied_at : label; }, 1400);
        if (refocus) card.focus();
      }
    } catch (err) { toast(err.message, true); }
  }

  // ------------------------------------------------------------------ editor
  function openEditor(id) {
    const a = state.apps.find((x) => x.id === id);
    if (!a) return;
    const ed = $("#editor");
    ed.innerHTML = `<div class="ed">
      <h2 id="ed-title">${esc(a.title)}</h2>
      <p class="muted" style="margin:-8px 0 0">${esc(a.company)}${a.url ? `. <a href="${esc(a.url)}" target="_blank" rel="noopener">Original offer</a>` : ""}</p>
      <div class="field"><span class="label">Status</span>
        <div class="status-pick">${STATUSES.map((s) => `<button type="button" data-st="${s.key}" aria-pressed="${s.key === a.status}">${s.label}</button>`).join("")}</div></div>
      <div class="row">
        <div class="field grow"><label for="e-applied">Applied on</label><input id="e-applied" type="date" value="${esc(a.applied_at || "")}"></div>
        <div class="field grow"><label for="e-contact">Contact</label><input id="e-contact" value="${esc(a.contact || "")}" placeholder="Name, email"></div>
      </div>
      <div class="row">
        <div class="field grow"><label for="e-next">Next step</label><input id="e-next" value="${esc(a.next_step || "")}" placeholder="Send follow-up email"></div>
        <div class="field"><label for="e-next-date">When</label><input id="e-next-date" type="date" value="${esc(a.next_step_date || "")}"></div>
      </div>
      <div class="field"><label for="e-notes">Notes</label><textarea id="e-notes" rows="5" placeholder="Interview questions, impressions, salary…">${esc(a.notes || "")}</textarea></div>
      ${a.letter ? `<details><summary style="cursor:pointer;font-weight:600">Cover letter you sent</summary><div class="desc" style="margin-top:8px">${esc(a.letter)}</div></details>` : ""}
      <div class="actions" style="justify-content:space-between">
        <button class="btn ghost" id="e-delete">Remove from board</button>
        <span style="display:flex;gap:10px"><button class="btn ghost" data-close>Cancel</button><button class="btn primary" id="e-save">Save changes</button></span>
      </div></div>`;
    let status = a.status;
    $$(".status-pick button", ed).forEach((b) => b.addEventListener("click", () => {
      status = b.dataset.st;
      $$(".status-pick button", ed).forEach((x) => x.setAttribute("aria-pressed", x === b));
    }));
    $("#e-save").addEventListener("click", async () => {
      try {
        await api(`/api/applications/${id}`, { method: "PATCH", json: {
          status, applied_at: $("#e-applied").value || null, contact: $("#e-contact").value,
          next_step: $("#e-next").value, next_step_date: $("#e-next-date").value || null, notes: $("#e-notes").value,
        } });
        await closeDrawers(); await loadBoard(false); toast("Changes saved.");
      } catch (err) { toast(err.message, true); }
    });
    $("#e-delete").addEventListener("click", async () => {
      if (!confirm(`Remove ${a.company} from your board?`)) return;
      await api(`/api/applications/${id}`, { method: "DELETE" });
      await closeDrawers(); await loadBoard(false); toast("Removed from your board.");
    });
    openDrawer("#editor");
  }

  // ------------------------------------------------------------------ boot
  (async () => {
    loadStatus();
    playTeaser();
    try {
      const cv = await api("/api/cv");
      if (cv && cv.skills) {
        renderProfile(cv);
        go("offers"); // return visit: skip onboarding, go straight to offers
      }
      await refreshApps();
    } catch (_) { /* first launch — stay on onboarding screen */ }
  })();
})();
