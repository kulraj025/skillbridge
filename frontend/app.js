const state = { profileId: null, opportunityId: null };
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

function renderMatch(match, opportunity) {
  $("#match-empty").classList.add("hidden");
  $("#match-result").classList.remove("hidden");
  setStatus("#match-status", `${Math.round(match.score * 100)}% match`, "success");
  $("#score-ring").style.setProperty("--score", `${Math.round(match.score * 100)}%`);
  $("#score-value").textContent = `${Math.round(match.score * 100)}%`;
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
    fillProfile(data.profile);
    fillOpportunity(data.opportunity);
    setStatus("#profile-status", "Sample", "success");
    setStatus("#opportunity-status", "Sample", "success");
    await runMatch();
    showToast("Sample profile and opportunity loaded.");
  } catch (error) { showToast(error.message); } finally { button.disabled = false; }
}

function bindEvents() {
  $("#profile-form").addEventListener("submit", saveProfile);
  $("#opportunity-form").addEventListener("submit", saveOpportunity);
  $("#demo-button").addEventListener("click", loadDemo);
  document.addEventListener("keydown", (event) => { if ((event.ctrlKey || event.metaKey) && event.key === "Enter") runMatch(); });
}

document.addEventListener("DOMContentLoaded", () => { $("#year").textContent = new Date().getFullYear(); bindEvents(); });
