const state = { profileId: null, opportunityId: null, studentSkills: [] };
const $ = (selector) => document.querySelector(selector);

function escapeHtml(value) {
  return String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;");
}

function splitList(value) {
  return String(value || "").split(/[\n,]/).map((item) => item.trim()).filter(Boolean);
}

function showToast(message) {
  const toast = $("#toast");
  toast.textContent = message;
  toast.classList.add("show");
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => toast.classList.remove("show"), 3500);
}

async function api(path, options = {}) {
  const response = await fetch(path, { headers: { "Content-Type": "application/json", ...(options.headers || {}) }, ...options });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || "Request failed. Please try again.");
  return data;
}

function setStatus(selector, text, kind = "") {
  const element = $(selector);
  element.textContent = text;
  element.className = `pill ${kind}`.trim();
}

function fillProfile(profile) {
  $("#profile-name").value = profile.name;
  $("#profile-major").value = profile.major || "";
  $("#profile-year").value = profile.graduation_year || "";
  $("#profile-skills").value = (profile.skills || []).join(", ");
  $("#profile-projects").value = (profile.projects || []).join("\n");
}

function fillOpportunity(opportunity) {
  $("#opportunity-title").value = opportunity.title;
  $("#opportunity-organization").value = opportunity.organization;
  $("#opportunity-description").value = opportunity.description;
  $("#required-skills").value = (opportunity.required_skills || []).join(", ");
  $("#preferred-skills").value = (opportunity.preferred_skills || []).join(", ");
  $("#opportunity-source").value = opportunity.source_url || "";
}

async function saveProfile(event) {
  event.preventDefault();
  const button = event.currentTarget.querySelector("button");
  button.disabled = true;
  try {
    const year = Number($("#profile-year").value);
    const profile = await api("/api/profiles", { method: "POST", body: JSON.stringify({ name: $("#profile-name").value.trim(), major: $("#profile-major").value.trim(), graduation_year: year || null, skills: splitList($("#profile-skills").value), projects: $("#profile-projects").value.split("\n").map((item) => item.trim()).filter(Boolean) }) });
    state.profileId = profile.id;
    state.studentSkills = profile.skills || [];
    setStatus("#profile-status", "Saved", "success");
    showToast("Student profile saved.");
  } catch (error) { showToast(error.message); } finally { button.disabled = false; }
}

async function saveOpportunity(event) {
  event.preventDefault();
  const button = event.currentTarget.querySelector("button");
  button.disabled = true;
  try {
    const opportunity = await api("/api/opportunities", { method: "POST", body: JSON.stringify({ title: $("#opportunity-title").value.trim(), organization: $("#opportunity-organization").value.trim(), description: $("#opportunity-description").value.trim(), required_skills: splitList($("#required-skills").value), preferred_skills: splitList($("#preferred-skills").value), source_url: $("#opportunity-source").value.trim() }) });
    state.opportunityId = opportunity.id;
    setStatus("#opportunity-status", "Saved", "success");
    showToast("Opportunity saved.");
  } catch (error) { showToast(error.message); } finally { button.disabled = false; }
}

function tagList(target, values, kind = "") {
  const element = $(target);
  if (!values.length) { element.innerHTML = '<span class="empty-tag">None detected yet</span>'; return; }
  element.innerHTML = values.map((value) => `<span class="tag ${kind}">${escapeHtml(value)}</span>`).join("");
}

function countUp(element, target, suffix) {
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (reduced) { element.textContent = `${target}${suffix}`; return; }
  const duration = 1100;
  const start = performance.now();
  const step = (now) => {
    const t = Math.min(1, (now - start) / duration);
    const eased = 1 - Math.pow(1 - t, 3);
    element.textContent = `${Math.round(target * eased)}${suffix}`;
    if (t < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

function renderMatch(match, opportunity) {
  $("#match-empty").classList.add("hidden");
  $("#match-result").classList.remove("hidden");
  const percent = Math.round(match.score * 100);
  setStatus("#match-status", `${percent}% match`, "success");
  $("#score-ring").style.setProperty("--score", `${percent}%`);
  countUp($("#score-value"), percent, "%");
  $("#match-title").textContent = opportunity.title;
  $("#match-organization").textContent = opportunity.organization;
  $("#match-explanation").textContent = match.explanation.text;
  tagList("#matched-required", match.matched_required);
  tagList("#missing-required", match.missing_required, "missing");
  tagList("#matched-preferred", match.matched_preferred, "preferred");
  const evidence = $("#match-evidence");
  evidence.innerHTML = match.evidence.length ? match.evidence.map((item) => `<div class="evidence-item">${escapeHtml(item.project)}<small>Evidence for: ${escapeHtml(item.matched_skills)}</small></div>`).join("") : '<span class="empty-tag">No project evidence matched yet</span>';
  const source = $("#source-link");
  if (opportunity.source_url) { source.href = opportunity.source_url; source.classList.remove("hidden"); } else { source.classList.add("hidden"); }
  updateScene(match);
}

/** Push the real result into the 3D scene so the graphic is never decorative fiction. */
function updateScene(match) {
  const scene = window.skillBridgeScene;
  if (!scene) return;
  const studentSkills = (state.studentSkills && state.studentSkills.length)
    ? state.studentSkills
    : scene.graph.nodes.filter((n) => n.side === "student" && !n.isHub).map((n) => n.label);
  const requirements = [...match.matched_required, ...match.matched_preferred, ...match.missing_required];
  scene.setMatch({
    studentSkills,
    requirementSkills: requirements.length ? requirements : ["No requirements detected"],
    matched: [...match.matched_required, ...match.matched_preferred],
    missing: match.missing_required,
    preferred: [],
  });
}

async function runMatch() {
  if (!state.profileId || !state.opportunityId) { showToast("Save a student profile and an opportunity first."); return; }
  try {
    const match = await api("/api/matches", { method: "POST", body: JSON.stringify({ profile_id: state.profileId, opportunity_id: state.opportunityId }) });
    const opportunities = await api("/api/opportunities");
    const opportunity = opportunities.find((item) => item.id === state.opportunityId);
    renderMatch(match, opportunity);
    showToast("Explainable match created.");
  } catch (error) { showToast(error.message); }
}

async function loadDemo() {
  const button = $("#demo-button");
  button.disabled = true;
  try {
    const data = await api("/api/demo", { method: "POST" });
    state.profileId = data.profile.id;
    state.opportunityId = data.opportunity.id;
    state.studentSkills = data.profile.skills || [];
    fillProfile(data.profile);
    fillOpportunity(data.opportunity);
    setStatus("#profile-status", "Sample", "success");
    setStatus("#opportunity-status", "Sample", "success");
    await runMatch();
    showToast("Sample profile and opportunity loaded.");
  } catch (error) { showToast(error.message); } finally { button.disabled = false; }
}

function inViewport(element) {
  const rect = element.getBoundingClientRect();
  return rect.top < window.innerHeight && rect.bottom > 0;
}

function initReveal() {
  const items = Array.from(document.querySelectorAll(".reveal"));
  if (!items.length) return;
  const showAll = () => items.forEach((item) => item.classList.add("in"));
  if (!("IntersectionObserver" in window) || window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    showAll();
    return;
  }
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("in");
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.15, rootMargin: "0px 0px -40px 0px" });
  items.forEach((item, index) => {
    item.style.transitionDelay = `${Math.min(index * 90, 360)}ms`;
    if (inViewport(item)) { item.classList.add("in"); return; }
    observer.observe(item);
  });
  // Safety net: never leave content permanently invisible.
  setTimeout(showAll, 4000);
}

function initCounters() {
  const elements = Array.from(document.querySelectorAll("[data-count]"));
  const finish = (element) => {
    countUp(element, Number(element.dataset.count), element.dataset.suffix || "");
  };
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (reduced || !("IntersectionObserver" in window)) {
    elements.forEach(finish);
    return;
  }
  const pending = new Set();
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        finish(entry.target);
        pending.delete(entry.target);
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.4 });
  elements.forEach((element) => {
    if (inViewport(element)) { finish(element); return; }
    pending.add(element);
    observer.observe(element);
  });
  setTimeout(() => { pending.forEach(finish); pending.clear(); }, 4000);
}

function initTilt() {
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  document.querySelectorAll(".panel").forEach((panel) => {
    panel.addEventListener("pointermove", (event) => {
      if (event.pointerType === "touch") return;
      const rect = panel.getBoundingClientRect();
      const px = (event.clientX - rect.left) / rect.width - 0.5;
      const py = (event.clientY - rect.top) / rect.height - 0.5;
      panel.style.setProperty("--ry", `${px * 4.5}deg`);
      panel.style.setProperty("--rx", `${-py * 4.5}deg`);
      panel.style.transform = "perspective(1000px) rotateX(var(--rx)) rotateY(var(--ry)) translateZ(0)";
    });
    panel.addEventListener("pointerleave", () => {
      panel.style.transform = "";
    });
  });
}

function bindEvents() {
  $("#profile-form").addEventListener("submit", saveProfile);
  $("#opportunity-form").addEventListener("submit", saveOpportunity);
  $("#demo-button").addEventListener("click", loadDemo);
  document.addEventListener("keydown", (event) => { if ((event.ctrlKey || event.metaKey) && event.key === "Enter") runMatch(); });
}

document.addEventListener("DOMContentLoaded", () => {
  $("#year").textContent = new Date().getFullYear();
  bindEvents();
  initReveal();
  initCounters();
  initTilt();
});
