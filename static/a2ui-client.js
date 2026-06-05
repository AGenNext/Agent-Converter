/* A2UI client (https://a2ui.org) — a real renderer for agent-driven surfaces.
 *
 * Consumes the server-to-client A2UI messages and renders them natively into
 * the DOM, without executing any agent-supplied code:
 *
 *   createSurface     create (or reset) a surface container
 *   updateComponents  add / update components on a surface
 *   updateDataModel   merge data into the surface's data model
 *   deleteSurface     remove a surface
 *
 * Components from the v0.9 "basic" catalog are mapped to DOM. Text properties
 * support {{path}} bindings resolved against the surface data model. Container
 * components (Row, Column, Card) may carry nested child component definitions
 * in properties.children.
 *
 * Exposes window.A2UIClient.
 */
(function () {
  "use strict";

  function getPath(obj, path) {
    return path.split(".").reduce((o, k) => (o == null ? o : o[k]), obj);
  }

  // Resolve {{path}} bindings in a string against the data model.
  function interpolate(text, dataModel) {
    if (typeof text !== "string") return text;
    return text.replace(/\{\{\s*([\w.]+)\s*\}\}/g, (m, p) => {
      const v = getPath(dataModel, p);
      return v == null ? "" : String(v);
    });
  }

  function elem(tag, className, text) {
    const n = document.createElement(tag);
    if (className) n.className = className;
    if (text != null) n.textContent = text;
    return n;
  }

  function chip(tag) {
    const key = String(tag).toLowerCase();
    const c = elem("span", "chip " + key, String(tag).toUpperCase());
    c.style.marginLeft = "8px";
    return c;
  }

  class Surface {
    constructor(root) {
      this.root = root; // container element for this surface
      this.dataModel = {};
      this.components = new Map(); // id -> rendered element
      this.bindables = []; // { node, raw } leaf nodes with {{bindings}}
    }
  }

  class A2UIClient {
    constructor(mountEl) {
      this.mount = mountEl;
      this.surfaces = new Map(); // surfaceId -> Surface
    }

    handle(msg) {
      if (!msg || !msg.method) return;
      const p = msg.params || {};
      switch (msg.method) {
        case "createSurface": return this._createSurface(p);
        case "updateDataModel": return this._updateDataModel(p);
        case "updateComponents": return this._updateComponents(p);
        case "deleteSurface": return this._deleteSurface(p);
        default: /* unknown method: ignore for forward-compat */ return;
      }
    }

    _surface(id) {
      let s = this.surfaces.get(id);
      if (!s) {
        const container = elem("div", "a2-surface");
        this.mount.appendChild(container);
        s = new Surface(container);
        this.surfaces.set(id, s);
      }
      return s;
    }

    _createSurface(p) {
      const s = this._surface(p.surfaceId);
      s.root.innerHTML = "";
      s.components.clear();
      s.bindables = [];
      if (p.catalog) s.root.dataset.catalog = p.catalog;
    }

    _updateDataModel(p) {
      const s = this._surface(p.surfaceId);
      Object.assign(s.dataModel, p.dataModel || {});
      // Re-resolve bindings only on the leaf nodes that actually carry one,
      // so sibling content (e.g. a confidence chip) is preserved.
      s.bindables.forEach((b) => {
        b.node.textContent = interpolate(b.raw, s.dataModel);
      });
    }

    _updateComponents(p) {
      const s = this._surface(p.surfaceId);
      (p.components || []).forEach((def) => {
        const node = this._render(def, s);
        const prev = s.components.get(def.id);
        if (prev && prev.parentNode) prev.parentNode.replaceChild(node, prev);
        else s.root.appendChild(node);
        s.components.set(def.id, node);
      });
    }

    _deleteSurface(p) {
      const s = this.surfaces.get(p.surfaceId);
      if (s && s.root.parentNode) s.root.parentNode.removeChild(s.root);
      this.surfaces.delete(p.surfaceId);
    }

    // Map a component definition to a DOM element.
    _render(def, s) {
      const c = def.component || {};
      const type = c.componentType || "Text";
      const props = c.properties || {};
      const dm = s.dataModel;

      // Set a node's text, and if it contains a {{binding}} register it as a
      // leaf bindable so later updateDataModel calls can refresh just this node.
      const bindText = (node, raw) => {
        const str = raw == null ? "" : String(raw);
        node.textContent = interpolate(str, dm);
        if (str.indexOf("{{") >= 0) s.bindables.push({ node: node, raw: str });
      };

      switch (type) {
        case "Heading": {
          const lvl = Math.min(Math.max(parseInt(props.level || 2, 10), 1), 4);
          const h = elem("h" + lvl, "a2-heading");
          bindText(h, props.text);
          return h;
        }
        case "Text": {
          const wrap = elem("div", "a2-text");
          const span = elem("span");
          bindText(span, props.text);
          wrap.appendChild(span);
          if (props.tag) wrap.appendChild(chip(props.tag));
          return wrap;
        }
        case "List": {
          const ul = elem("ul", "a2-list");
          (props.items || []).forEach((it) => {
            const li = elem("li");
            li.textContent = interpolate(String(it), dm);
            ul.appendChild(li);
          });
          return ul;
        }
        case "Divider":
          return elem("hr", "a2-divider");
        case "Row":
        case "Column":
        case "Card": {
          const box = elem("div", "a2-" + type.toLowerCase());
          (props.children || []).forEach((child) => {
            box.appendChild(this._render(child, s));
          });
          return box;
        }
        case "Button": {
          const b = elem("button", "a2-button");
          bindText(b, props.label || props.text);
          return b;
        }
        default: {
          // Unknown component: render its text if present, else a small note.
          const d = elem("div", "a2-unknown");
          bindText(d, props.text || `[${type}]`);
          return d;
        }
      }
    }
  }

  window.A2UIClient = A2UIClient;
})();
