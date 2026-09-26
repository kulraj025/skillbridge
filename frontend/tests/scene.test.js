/**
 * Unit tests for the SkillBridge 3D scene math.
 * Run with: node --test frontend/tests/
 */
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");

const {
  CAMERA,
  LAYOUT,
  buildSceneGraph,
  fibonacciSphere,
  normalizeLabel,
  projectPoint,
  rotatePoint,
} = require("../three-scene.js");

test("fibonacciSphere returns the requested number of points", () => {
  assert.equal(fibonacciSphere(0, 50).length, 0);
  assert.equal(fibonacciSphere(1, 50).length, 1);
  assert.equal(fibonacciSphere(7, 50).length, 7);
});

test("fibonacciSphere keeps every point on the requested radius", () => {
  const radius = 76;
  fibonacciSphere(12, radius).forEach((point) => {
    const distance = Math.sqrt(
      point.x * point.x + point.y * point.y + point.z * point.z
    );
    assert.ok(
      Math.abs(distance - radius) < 1e-9,
      `expected |p| = ${radius}, got ${distance}`
    );
  });
});

test("fibonacciSphere is deterministic", () => {
  assert.deepEqual(fibonacciSphere(6, 40), fibonacciSphere(6, 40));
});

test("rotatePoint is the identity at zero rotation", () => {
  const point = { x: 12, y: -5, z: 30 };
  const rotated = rotatePoint(point, 0, 0);
  assert.ok(Math.abs(rotated.x - point.x) < 1e-9);
  assert.ok(Math.abs(rotated.y - point.y) < 1e-9);
  assert.ok(Math.abs(rotated.z - point.z) < 1e-9);
});

test("rotatePoint preserves distance from the origin", () => {
  const point = { x: 100, y: 40, z: -60 };
  const rotated = rotatePoint(point, 0.4, 1.1);
  const before = Math.hypot(point.x, point.y, point.z);
  const after = Math.hypot(rotated.x, rotated.y, rotated.z);
  assert.ok(Math.abs(before - after) < 1e-6, `${before} vs ${after}`);
});

test("projectPoint flips the y axis so up is up on screen", () => {
  const projected = projectPoint({ x: 0, y: 100, z: 0 }, 1, CAMERA);
  assert.ok(projected.y < 0, "positive world y should render above centre");
});

test("projectPoint makes distant points smaller than near points", () => {
  const near = projectPoint({ x: 50, y: 0, z: -LAYOUT.boundZ }, 1, CAMERA);
  const far = projectPoint({ x: 50, y: 0, z: LAYOUT.boundZ }, 1, CAMERA);
  assert.ok(near.scale > far.scale, "near point should have a larger scale");
  assert.ok(near.x > far.x, "near point should project further from centre");
});

test("projectPoint rejects points behind the camera", () => {
  const behind = projectPoint({ x: 0, y: 0, z: -LAYOUT.boundZ * 100 }, 1, CAMERA);
  assert.equal(behind, null);
});

test("projectPoint always keeps a usable scale for normal depth", () => {
  for (let z = -LAYOUT.boundZ; z <= LAYOUT.boundZ; z += 10) {
    const projected = projectPoint({ x: 10, y: 10, z }, 1, CAMERA);
    assert.ok(projected && Number.isFinite(projected.scale) && projected.scale > 0);
  }
});

test("normalizeLabel trims and lowercases", () => {
  assert.equal(normalizeLabel("  REST API "), "rest api");
  assert.equal(normalizeLabel(null), "");
});

test("buildSceneGraph creates one node per skill plus two hubs", () => {
  const graph = buildSceneGraph({
    studentSkills: ["Python", "SQL"],
    requirementSkills: ["Python", "Git"],
  });
  // 2 student skills + 2 requirement skills + 2 hubs
  assert.equal(graph.nodes.length, 6);
  assert.equal(graph.nodes.filter((n) => n.isHub).length, 2);
  assert.equal(graph.nodes.filter((n) => n.side === "student").length, 3);
});

test("buildSceneGraph connects only matched requirements", () => {
  const graph = buildSceneGraph({
    studentSkills: ["Python", "SQL"],
    requirementSkills: ["Python", "Git"],
    matched: ["python"],
    missing: ["git"],
  });
  const bridges = graph.edges.filter((e) => e.kind === "bridge");
  assert.equal(bridges.length, 1, "only the matched requirement gets a bridge");
  assert.equal(graph.counts.bridges, 1);
  assert.equal(graph.counts.missing, 1);
});

test("buildSceneGraph links a matched requirement to the same-named skill", () => {
  const graph = buildSceneGraph({
    studentSkills: ["Python", "SQL"],
    requirementSkills: ["SQL", "Git"],
    matched: ["sql"],
  });
  const bridge = graph.edges.find((e) => e.kind === "bridge");
  const from = graph.nodes.find((n) => n.id === bridge.from);
  const to = graph.nodes.find((n) => n.id === bridge.to);
  assert.equal(from.label, "SQL");
  assert.equal(to.label, "SQL");
});

test("buildSceneGraph falls back to the nearest skill when names differ", () => {
  const graph = buildSceneGraph({
    studentSkills: ["Python", "SQL"],
    requirementSkills: ["PostgreSQL"],
    matched: ["postgresql"],
  });
  const bridge = graph.edges.find((e) => e.kind === "bridge");
  const from = graph.nodes.find((n) => n.id === bridge.from);
  assert.ok(from, "a fallback bridge should still be created");
  assert.ok(["Python", "SQL"].includes(from.label));
});

test("buildSceneGraph colours requirements by match state", () => {
  const graph = buildSceneGraph({
    studentSkills: ["Python"],
    requirementSkills: ["Python", "Git", "Docker", "Figma"],
    matched: ["python"],
    missing: ["git", "docker"],
    preferred: ["figma"],
  });
  const kindOf = (label) =>
    graph.nodes.find(
      (n) => !n.isHub && n.side === "requirement" && n.label === label
    ).kind;
  assert.equal(kindOf("Python"), "matched");
  assert.equal(kindOf("Git"), "missing");
  assert.equal(kindOf("Docker"), "missing");
  assert.equal(kindOf("Figma"), "preferred");
});

test("buildSceneGraph is case insensitive and de-duplicates", () => {
  const graph = buildSceneGraph({
    studentSkills: ["Python"],
    requirementSkills: ["Python", "python"],
    matched: ["PYTHON"],
  });
  const bridges = graph.edges.filter((e) => e.kind === "bridge");
  assert.equal(bridges.length, 2, "both spellings are matched");
});

test("buildSceneGraph handles an empty profile without throwing", () => {
  const graph = buildSceneGraph({
    studentSkills: [],
    requirementSkills: ["Python"],
    matched: ["python"],
  });
  assert.equal(graph.edges.filter((e) => e.kind === "bridge").length, 0);
  assert.equal(graph.nodes.filter((n) => n.isHub).length, 2);
});
