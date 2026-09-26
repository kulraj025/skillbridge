/**
 * SkillBridge 3D bridge scene
 *
 * A dependency-free 3D visualization of the core product idea: skills on one
 * side, opportunity requirements on the other, and a visible bridge between
 * them. Matched requirements are connected. Gaps are deliberately left open so
 * the "missing evidence" story is as visible as the "matched" story.
 *
 * Rendering is Canvas 2D with a hand-rolled perspective projection. The scene
 * only needs points and lines, so shipping a WebGL bundle would cost more than
 * it returns.
 */
(function (global, factory) {
  "use strict";
  var api = factory();
  if (typeof module === "object" && module.exports) {
    module.exports = api;
  }
  if (global) {
    global.SkillBridge3D = api;
  }
})(typeof window !== "undefined" ? window : null, function () {
  "use strict";

  var GOLDEN_ANGLE = Math.PI * (3 - Math.sqrt(5));

  /** Camera constants. focal is 1 so units stay in world scale. */
  var CAMERA = Object.freeze({ focal: 1, distance: 2.2, near: 0.35 });

  /** Scene extents. boundX/boundY drive the fit calculation on resize. */
  var LAYOUT = Object.freeze({
    clusterGap: 138,
    clusterRadius: 76,
    platformDrop: 112,
    boundX: 238,
    boundY: 126,
    boundZ: 118,
  });

  var PALETTE = Object.freeze({
    student: "#67e0d5",
    matched: "#6fe0a4",
    preferred: "#ffbd76",
    missing: "#ff9292",
    idle: "#8aa4b4",
    hub: "#3d5a6c",
  });

  var DEFAULT_DATA = Object.freeze({
    studentSkills: ["Python", "SQL", "JavaScript", "Communication", "Teamwork"],
    requirementSkills: ["Python", "SQL", "Git", "REST API", "FastAPI"],
    matched: ["Python", "SQL"],
    missing: ["Git", "REST API", "FastAPI"],
    preferred: [],
  });

  /* ------------------------------------------------------------------ *
   * Pure math. Exported and unit tested.
   * ------------------------------------------------------------------ */

  function clamp(value, low, high) {
    return value < low ? low : value > high ? high : value;
  }

  /** Deterministic, evenly distributed points on a sphere. */
  function fibonacciSphere(count, radius) {
    if (count <= 0) {
      return [];
    }
    var points = [];
    for (var i = 0; i < count; i += 1) {
      var t = count === 1 ? 0.5 : i / (count - 1);
      var y = 1 - 2 * t;
      var ring = Math.sqrt(Math.max(0, 1 - y * y));
      var theta = GOLDEN_ANGLE * i;
      points.push({
        x: Math.cos(theta) * ring * radius,
        y: y * radius,
        z: Math.sin(theta) * ring * radius,
      });
    }
    return points;
  }

  /** Rotate around Y then X. Distances from the origin are preserved. */
  function rotatePoint(point, rotationX, rotationY) {
    var cosY = Math.cos(rotationY);
    var sinY = Math.sin(rotationY);
    var x1 = point.x * cosY - point.z * sinY;
    var z1 = point.x * sinY + point.z * cosY;
    var cosX = Math.cos(rotationX);
    var sinX = Math.sin(rotationX);
    return {
      x: x1,
      y: point.y * cosX - z1 * sinX,
      z: point.y * sinX + z1 * cosX,
    };
  }

  /**
   * Perspective projection. Returns screen offsets from the canvas centre, or
   * null when the point sits behind the camera plane.
   */
  function projectPoint(point, unit, camera) {
    var distance = camera.distance + point.z / LAYOUT.boundZ;
    if (distance <= camera.near) {
      return null;
    }
    var scale = camera.focal / distance;
    return {
      x: point.x * unit * scale,
      y: -point.y * unit * scale,
      scale: scale,
      depth: point.z,
    };
  }

  function normalizeLabel(value) {
    return String(value == null ? "" : value).trim().toLowerCase();
  }

  function nearestNode(nodes, target) {
    var best = null;
    var bestDistance = Infinity;
    for (var i = 0; i < nodes.length; i += 1) {
      var dx = nodes[i].base.x - target.x;
      var dy = nodes[i].base.y - target.y;
      var dz = nodes[i].base.z - target.z;
      var distance = dx * dx + dy * dy + dz * dz;
      if (distance < bestDistance) {
        bestDistance = distance;
        best = nodes[i];
      }
    }
    return best;
  }

  function buildSceneGraph(options) {
    var opts = options || {};
    var studentSkills = (opts.studentSkills || []).map(String).filter(Boolean);
    var requirementSkills = (opts.requirementSkills || []).map(String).filter(Boolean);

    var matchedSet = new Set((opts.matched || []).map(normalizeLabel));
    var missingSet = new Set((opts.missing || []).map(normalizeLabel));
    var preferredSet = new Set((opts.preferred || []).map(normalizeLabel));

    var nodes = [];
    var edges = [];

    function addCluster(side, labels, centerX) {
      var center = { x: centerX, y: 0, z: 0 };
      var points = fibonacciSphere(labels.length, LAYOUT.clusterRadius);
      var hubId = side + ":hub";

      nodes.push({
        id: hubId,
        side: side,
        label: side === "student" ? "You" : "Role",
        kind: "hub",
        color: PALETTE.hub,
        base: center,
        phase: 0,
        clusterCenter: center,
        isHub: true,
      });

      labels.forEach(function (label, index) {
        var point = points[index];
        var kind = "student";
        if (side === "requirement") {
          var key = normalizeLabel(label);
          if (matchedSet.has(key)) {
            kind = "matched";
          } else if (preferredSet.has(key)) {
            kind = "preferred";
          } else if (missingSet.has(key)) {
            kind = "missing";
          } else {
            kind = "idle";
          }
        }
        var id = side + ":" + index;
        nodes.push({
          id: id,
          side: side,
          label: label,
          kind: kind,
          color: PALETTE[kind] || PALETTE.idle,
          base: { x: centerX + point.x, y: point.y, z: point.z },
          phase: index * 0.72,
          clusterCenter: center,
          isHub: false,
        });
        edges.push({ from: hubId, to: id, kind: "spoke" });
      });
    }

    addCluster("student", studentSkills, -LAYOUT.clusterGap);
    addCluster("requirement", requirementSkills, LAYOUT.clusterGap);

    var studentNodes = nodes.filter(function (node) {
      return node.side === "student" && !node.isHub;
    });

    var bridgeIndex = 0;
    requirementSkills.forEach(function (label, index) {
      if (!matchedSet.has(normalizeLabel(label))) {
        return;
      }
      var targetId = "requirement:" + index;
      var target = null;
      for (var i = 0; i < nodes.length; i += 1) {
        if (nodes[i].id === targetId) {
          target = nodes[i];
          break;
        }
      }
      if (!target || !studentNodes.length) {
        return;
      }
      var key = normalizeLabel(label);
      var exact = null;
      for (var j = 0; j < studentNodes.length; j += 1) {
        if (normalizeLabel(studentNodes[j].label) === key) {
          exact = studentNodes[j];
          break;
        }
      }
      var source = exact || nearestNode(studentNodes, target.base);
      if (source) {
        edges.push({
          from: source.id,
          to: targetId,
          kind: "bridge",
          phase: bridgeIndex * 0.85,
        });
        bridgeIndex += 1;
      }
    });

    return {
      nodes: nodes,
      edges: edges,
      counts: {
        requirements: requirementSkills.length,
        matched: matchedSet.size,
        missing: missingSet.size,
        bridges: bridgeIndex,
      },
    };
  }

  /* ------------------------------------------------------------------ *
   * Rendering
   * ------------------------------------------------------------------ */

  function hexToRgb(hex) {
    var value = hex.replace("#", "");
    return {
      r: parseInt(value.slice(0, 2), 16),
      g: parseInt(value.slice(2, 4), 16),
      b: parseInt(value.slice(4, 6), 16),
    };
  }

  function rgba(hex, alpha) {
    var c = hexToRgb(hex);
    return "rgba(" + c.r + "," + c.g + "," + c.b + "," + alpha + ")";
  }

  /** Cached radial glow sprite. Avoids rebuilding gradients every frame. */
  function createSpriteFactory() {
    var cache = {};
    return function sprite(color) {
      if (cache[color]) {
        return cache[color];
      }
      var size = 64;
      var canvas = document.createElement("canvas");
      canvas.width = size;
      canvas.height = size;
      var ctx = canvas.getContext("2d");
      var gradient = ctx.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
      gradient.addColorStop(0, rgba(color, 0.95));
      gradient.addColorStop(0.32, rgba(color, 0.42));
      gradient.addColorStop(1, rgba(color, 0));
      ctx.fillStyle = gradient;
      ctx.fillRect(0, 0, size, size);
      cache[color] = canvas;
      return canvas;
    };
  }

  function prefersReducedMotion() {
    return (
      typeof window !== "undefined" &&
      typeof window.matchMedia === "function" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches
    );
  }

  function BridgeScene(canvas, options) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this.settings = Object.assign(
      {
        autoRotate: true,
        spinSpeed: 0.16,
        bobAmplitude: 3.4,
        maxPixelRatio: 2,
        tooltip: null,
      },
      (options && options.settings) || {}
    );

    this.rotationX = -0.16;
    this.rotationY = 0.42;
    this.spin = this.rotationY;
    this.dragging = false;
    this.destroyed = false;
    this.pointerInside = false;
    this.hovered = null;
    this.projected = [];
    this.width = 0;
    this.height = 0;
    this.unit = 1;

    this.glow = createSpriteFactory();
    this.graph = buildSceneGraph((options && options.data) || DEFAULT_DATA);
    this.nodesById = {};
    this.indexGraph();

    this.dust = [];
    for (var i = 0; i < 70; i += 1) {
      this.dust.push({
        x: (Math.sin(i * 12.9898) * 43758.5453 % 1) * LAYOUT.boundX * 2.4,
        y: (Math.sin(i * 78.233) * 12345.6789 % 1) * LAYOUT.boundY * 2.1,
        z: (Math.sin(i * 39.425) * 24634.1234 % 1) * LAYOUT.boundZ * 2.2,
        size: 0.5 + ((i * 7) % 5) * 0.22,
      });
    }

    this.lastFrame = 0;
    this.frame = this.frame.bind(this);
    this.visible = true;
    this.reducedMotion = prefersReducedMotion();

    this.bindEvents();
    this.resize();
    this.start();
  }

  BridgeScene.prototype.indexGraph = function indexGraph() {
    var self = this;
    this.nodesById = {};
    this.graph.nodes.forEach(function (node) {
      self.nodesById[node.id] = node;
    });
  };

  BridgeScene.prototype.setMatch = function setMatch(update) {
    this.graph = buildSceneGraph(
      Object.assign({}, this.graphCounts(), update || {})
    );
    this.indexGraph();
    if (this.reducedMotion || !this.visible) {
      this.draw(0);
    }
  };

  BridgeScene.prototype.graphCounts = function graphCounts() {
    return {
      studentSkills: this.graph.nodes
        .filter(function (n) {
          return n.side === "student" && !n.isHub;
        })
        .map(function (n) {
          return n.label;
        }),
      requirementSkills: this.graph.nodes
        .filter(function (n) {
          return n.side === "requirement" && !n.isHub;
        })
        .map(function (n) {
          return n.label;
        }),
    };
  };

  BridgeScene.prototype.resize = function resize() {
    var rect = this.canvas.getBoundingClientRect();
    var ratio = Math.min(
      window.devicePixelRatio || 1,
      this.settings.maxPixelRatio
    );
    var width = Math.max(1, Math.round(rect.width));
    var height = Math.max(1, Math.round(rect.height));
    this.width = width;
    this.height = height;
    this.canvas.width = Math.round(width * ratio);
    this.canvas.height = Math.round(height * ratio);
    this.ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    this.unit =
      Math.min(
        (0.92 * width) / (2 * LAYOUT.boundX),
        (0.92 * height) / (2 * LAYOUT.boundY)
      ) * CAMERA.distance;
    if (this.reducedMotion || !this.visible) {
      this.draw(0);
    }
  };

  BridgeScene.prototype.worldPosition = function worldPosition(node, time) {
    var bob =
      node.isHub || this.reducedMotion
        ? 0
        : Math.sin(time * 1.1 + node.phase) * this.settings.bobAmplitude;
    var point = { x: node.base.x, y: node.base.y + bob, z: node.base.z };
    return rotatePoint(point, this.rotationX, this.rotationY);
  };

  BridgeScene.prototype.draw = function draw(time) {
    var ctx = this.ctx;
    var self = this;
    var centerX = this.width / 2;
    var centerY = this.height / 2;

    ctx.clearRect(0, 0, this.width, this.height);
    ctx.save();
    ctx.globalCompositeOperation = "lighter";

    var i;
    var p;

    // Dust field for depth.
    ctx.fillStyle = "rgba(150, 190, 210, 0.30)";
    for (i = 0; i < this.dust.length; i += 1) {
      var dust = this.dust[i];
      var drift = this.reducedMotion ? 0 : time * 4;
      p = projectPoint(
        rotatePoint(
          { x: dust.x, y: dust.y + Math.sin(dust.x * 0.01) * 3, z: dust.z + drift },
          this.rotationX,
          this.rotationY
        ),
        this.unit,
        CAMERA
      );
      if (!p) {
        continue;
      }
      ctx.globalAlpha = 0.5;
      ctx.fillRect(centerX + p.x, centerY + p.y, dust.size, dust.size);
    }
    ctx.globalAlpha = 1;

    // Platforms under each cluster.
    [-1, 1].forEach(function (side) {
      self.drawPlatform(centerX, centerY, side * LAYOUT.clusterGap, time);
    });

    // Spokes and bridges, far to near.
    var order = this.graph.edges.slice().sort(function (a, b) {
      return (
        (self.nodesById[b.from].base.z + self.nodesById[b.to].base.z) / 2 -
        (self.nodesById[a.from].base.z + self.nodesById[a.to].base.z) / 2
      );
    });

    for (i = 0; i < order.length; i += 1) {
      var edge = order[i];
      var from = this.worldPosition(this.nodesById[edge.from], time);
      var to = this.worldPosition(this.nodesById[edge.to], time);
      var a = projectPoint(from, this.unit, CAMERA);
      var b = projectPoint(to, this.unit, CAMERA);
      if (!a || !b) {
        continue;
      }
      if (edge.kind === "spoke") {
        ctx.strokeStyle = rgba(PALETTE.hub, 0.4);
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(centerX + a.x, centerY + a.y);
        ctx.lineTo(centerX + b.x, centerY + b.y);
        ctx.stroke();
      } else {
        this.drawBridge(centerX, centerY, a, b, edge, time);
      }
    }

    // Nodes, far to near.
    this.projected = [];
    var nodes = this.graph.nodes.slice().sort(function (m, n) {
      return n.base.z - m.base.z;
    });
    for (i = 0; i < nodes.length; i += 1) {
      var node = nodes[i];
      var rotated = this.worldPosition(node, time);
      var projected = projectPoint(rotated, this.unit, CAMERA);
      if (!projected) {
        continue;
      }
      var radius = (node.isHub ? 5 : 7.4) * projected.scale * 1.9;
      var sx = centerX + projected.x;
      var sy = centerY + projected.y;

      var sprite = this.glow(node.color);
      var drawSize = radius * 4.2;
      ctx.globalAlpha = node.isHub ? 0.5 : 0.92;
      ctx.drawImage(sprite, sx - drawSize / 2, sy - drawSize / 2, drawSize, drawSize);
      ctx.globalAlpha = 1;
      ctx.fillStyle = node.color;
      ctx.beginPath();
      ctx.arc(sx, sy, radius, 0, Math.PI * 2);
      ctx.fill();

      var facing = rotated.z - node.clusterCenter.z;
      this.projected.push({
        id: node.id,
        x: sx,
        y: sy,
        r: radius + 10,
        radius: radius,
        label: node.label,
        color: node.color,
        kind: node.kind,
        isHub: node.isHub,
        alpha: facing > 0 ? 0.32 : 0.95,
      });
    }

    ctx.restore();

    // Labels drawn without additive blending so text stays readable.
    ctx.save();
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    for (i = 0; i < this.projected.length; i += 1) {
      var item = this.projected[i];
      if (item.isHub) {
        continue;
      }
      var fontSize = clamp(item.radius * 1.75, 9, 14);
      ctx.font = "600 " + fontSize.toFixed(1) + "px Inter, system-ui, sans-serif";
      ctx.fillStyle = "rgba(6, 16, 24, 0.72)";
      var width = ctx.measureText(item.label).width;
      roundRect(
        ctx,
        item.x - width / 2 - 6,
        item.y + item.radius + 5,
        width + 12,
        fontSize + 8,
        5
      );
      ctx.fill();
      ctx.fillStyle = rgba(item.color, item.alpha);
      ctx.fillText(item.label, item.x, item.y + item.radius + 5 + (fontSize + 8) / 2);
    }
    ctx.restore();

    this.renderTooltip();
  };

  BridgeScene.prototype.drawPlatform = function drawPlatform(centerX, centerY, offsetX, time) {
    var ctx = this.ctx;
    var points = fibonacciSphere(28, LAYOUT.clusterRadius + 26);
    var y = LAYOUT.platformDrop + (this.reducedMotion ? 0 : Math.sin(time * 0.6 + offsetX) * 2);
    ctx.save();
    ctx.strokeStyle = rgba(PALETTE.hub, 0.5);
    ctx.lineWidth = 1.1;
    ctx.beginPath();
    for (var i = 0; i < points.length; i += 1) {
      var rotated = rotatePoint(
        { x: offsetX + points[i].x, y: y, z: points[i].z },
        this.rotationX,
        0
      );
      var p = projectPoint(rotated, this.unit, CAMERA);
      if (!p) {
        continue;
      }
      if (i === 0) {
        ctx.moveTo(centerX + p.x, centerY + p.y);
      } else {
        ctx.lineTo(centerX + p.x, centerY + p.y);
      }
    }
    ctx.closePath();
    ctx.stroke();
    ctx.restore();
  };

  BridgeScene.prototype.drawBridge = function drawBridge(centerX, centerY, a, b, edge, time) {
    var ctx = this.ctx;
    var color = PALETTE.matched;
    var bow = 26 + Math.abs(a.x - b.x) * 0.05;
    var midX = (a.x + b.x) / 2;
    var midY = (a.y + b.y) / 2 - bow;

    ctx.strokeStyle = rgba(color, 0.3);
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(centerX + a.x, centerY + a.y);
    ctx.quadraticCurveTo(centerX + midX, centerY + midY, centerX + b.x, centerY + b.y);
    ctx.stroke();

    if (this.reducedMotion) {
      return;
    }
    var t = (time * 0.32 + (edge.phase || 0)) % 1;
    var inv = 1 - t;
    var px = inv * inv * a.x + 2 * inv * t * midX + t * t * b.x;
    var py = inv * inv * a.y + 2 * inv * t * midY + t * t * b.y;
    var size = 26;
    var sprite = this.glow(color);
    ctx.globalAlpha = 0.9;
    ctx.drawImage(
      sprite,
      centerX + px - size / 2,
      centerY + py - size / 2,
      size,
      size
    );
    ctx.globalAlpha = 1;
  };

  function roundRect(ctx, x, y, width, height, radius) {
    var r = Math.min(radius, height / 2);
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.arcTo(x + width, y, x + width, y + height, r);
    ctx.arcTo(x + width, y + height, x, y + height, r);
    ctx.arcTo(x, y + height, x, y, r);
    ctx.arcTo(x, y, x + width, y, r);
    ctx.closePath();
  }

  BridgeScene.prototype.renderTooltip = function renderTooltip() {
    var element = this.settings.tooltip;
    if (!element) {
      return;
    }
    if (!this.hovered) {
      element.classList.remove("visible");
      return;
    }
    var color = this.hovered.color;
    element.innerHTML =
      '<span class="tip-dot" style="background:' +
      color +
      '"></span>' +
      escapeText(this.hovered.label);
    element.classList.add("visible");
  };

  function escapeText(value) {
    return String(value).replace(
      /[&<>"']/g,
      function (character) {
        return {
          "&": "&amp;",
          "<": "&lt;",
          ">": "&gt;",
          '"': "&quot;",
          "'": "&#039;",
        }[character];
      }
    );
  }

  BridgeScene.prototype.pick = function pick(clientX, clientY) {
    var rect = this.canvas.getBoundingClientRect();
    var x = clientX - rect.left;
    var y = clientY - rect.top;
    var best = null;
    var bestDistance = Infinity;
    for (var i = 0; i < this.projected.length; i += 1) {
      var item = this.projected[i];
      if (item.isHub) {
        continue;
      }
      var dx = item.x - x;
      var dy = item.y - y;
      var distance = Math.sqrt(dx * dx + dy * dy);
      if (distance <= item.r && distance < bestDistance) {
        bestDistance = distance;
        best = item;
      }
    }
    return best;
  };

  BridgeScene.prototype.bindEvents = function bindEvents() {
    var self = this;
    var last = null;

    this.onPointerDown = function (event) {
      self.dragging = true;
      last = { x: event.clientX, y: event.clientY };
      self.canvas.classList.add("dragging");
      self.canvas.setPointerCapture(event.pointerId);
    };

    this.onPointerMove = function (event) {
      if (self.dragging && last) {
        var dx = event.clientX - last.x;
        var dy = event.clientY - last.y;
        self.spin += dx * 0.0075;
        self.rotationX = clamp(self.rotationX + dy * 0.004, -0.75, 0.75);
        last = { x: event.clientX, y: event.clientY };
        if (!self.reducedMotion) {
          self.draw(performance.now() / 1000);
        }
        return;
      }
      var hit = self.pick(event.clientX, event.clientY);
      self.hovered = hit;
      self.canvas.style.cursor = hit ? "pointer" : "grab";
      if (self.settings.tooltip && hit) {
        var rect = self.canvas.getBoundingClientRect();
        self.settings.tooltip.style.left = hit.x + "px";
        self.settings.tooltip.style.top = hit.y - 14 + "px";
      }
      self.renderTooltip();
    };

    this.onPointerUp = function (event) {
      self.dragging = false;
      last = null;
      self.canvas.classList.remove("dragging");
      if (event.pointerId != null && self.canvas.hasPointerCapture(event.pointerId)) {
        self.canvas.releasePointerCapture(event.pointerId);
      }
    };

    this.onPointerLeave = function () {
      self.hovered = null;
      self.renderTooltip();
    };

    this.canvas.addEventListener("pointerdown", this.onPointerDown);
    this.canvas.addEventListener("pointermove", this.onPointerMove);
    this.canvas.addEventListener("pointerup", this.onPointerUp);
    this.canvas.addEventListener("pointercancel", this.onPointerUp);
    this.canvas.addEventListener("pointerleave", this.onPointerLeave);

    this.onResize = function () {
      self.resize();
    };
    window.addEventListener("resize", this.onResize);

    if (typeof ResizeObserver !== "undefined") {
      this.resizeObserver = new ResizeObserver(function () {
        self.resize();
      });
      this.resizeObserver.observe(this.canvas);
    }

    if (typeof IntersectionObserver !== "undefined") {
      this.intersectionObserver = new IntersectionObserver(
        function (entries) {
          self.visible = entries[0].isIntersecting;
          if (self.visible) {
            self.start();
          } else {
            self.stop();
          }
        },
        { threshold: 0.05 }
      );
      this.intersectionObserver.observe(this.canvas);
    }
  };

  BridgeScene.prototype.start = function start() {
    if (this.destroyed || this.running) {
      return;
    }
    this.running = true;
    this.lastFrame = 0;
    if (this.reducedMotion) {
      this.draw(0);
      return;
    }
    window.requestAnimationFrame(this.frame);
  };

  BridgeScene.prototype.stop = function stop() {
    this.running = false;
  };

  BridgeScene.prototype.frame = function frame(timestamp) {
    if (!this.running) {
      return;
    }
    if (!this.lastFrame) {
      this.lastFrame = timestamp;
    }
    var delta = Math.min(0.05, (timestamp - this.lastFrame) / 1000);
    this.lastFrame = timestamp;

    if (this.settings.autoRotate && !this.dragging) {
      this.spin += delta * this.settings.spinSpeed;
    }
    this.rotationY += (this.spin - this.rotationY) * Math.min(1, delta * 9);
    this.draw(timestamp / 1000);
    window.requestAnimationFrame(this.frame);
  };

  BridgeScene.prototype.destroy = function destroy() {
    this.destroyed = true;
    this.stop();
    var self = this;
    this.canvas.removeEventListener("pointerdown", this.onPointerDown);
    this.canvas.removeEventListener("pointermove", this.onPointerMove);
    this.canvas.removeEventListener("pointerup", this.onPointerUp);
    this.canvas.removeEventListener("pointercancel", this.onPointerUp);
    this.canvas.removeEventListener("pointerleave", this.onPointerLeave);
    window.removeEventListener("resize", this.onResize);
    if (this.resizeObserver) {
      this.resizeObserver.disconnect();
    }
    if (this.intersectionObserver) {
      this.intersectionObserver.disconnect();
    }
    return self;
  };

  function bootstrap() {
    var canvas = document.getElementById("bridge-canvas");
    if (!canvas) {
      return null;
    }
    var tooltip = document.getElementById("scene-tooltip");
    var scene = new BridgeScene(canvas, { data: DEFAULT_DATA, settings: { tooltip: tooltip } });
    scene.start();
    if (typeof window !== "undefined") {
      window.skillBridgeScene = scene;
    }
    return scene;
  }

  if (typeof document !== "undefined") {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", bootstrap, { once: true });
    } else {
      bootstrap();
    }
  }

  return {
    BridgeScene: BridgeScene,
    CAMERA: CAMERA,
    LAYOUT: LAYOUT,
    PALETTE: PALETTE,
    DEFAULT_DATA: DEFAULT_DATA,
    bootstrap: bootstrap,
    buildSceneGraph: buildSceneGraph,
    fibonacciSphere: fibonacciSphere,
    normalizeLabel: normalizeLabel,
    prefersReducedMotion: prefersReducedMotion,
    projectPoint: projectPoint,
    rotatePoint: rotatePoint,
  };
});
