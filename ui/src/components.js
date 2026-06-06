// Reusable, framework-free UI components for the Research Agent chat UI.
// Each function returns a DOM element, so they work in Storybook
// (@storybook/html), in the served control panel, or in any plain page.

function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") node.className = v;
    else if (k === "html") node.innerHTML = v;
    else node.setAttribute(k, v);
  }
  for (const c of children) {
    if (c == null) continue;
    node.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
  }
  return node;
}

// A confidence tag chip: HIGH | MEDIUM | LOW | UNVERIFIED.
export function ConfidenceChip(level) {
  const key = String(level).toLowerCase();
  return el("span", { class: `chip ${key}` }, String(level).toUpperCase());
}

// A chat bubble. role is "user" or "agent".
export function MessageBubble({ role = "agent", text = "" }) {
  return el("div", { class: `bubble ${role}` }, text);
}

// A key finding: the claim, its source, and a confidence chip.
export function FindingItem({ text, source, confidence }) {
  return el(
    "div",
    { class: "finding" },
    el("div", { class: "body" }, el("div", {}, text), el("div", { class: "src" }, source)),
    ConfidenceChip(confidence)
  );
}

// A source line with its credibility tier (T1..T8).
export function SourceItem({ tier, label }) {
  return el("div", {}, el("span", { class: "tier" }, tier), label);
}

// A live status bar shown while the agent works, or service status.
export function StatusBar({ text = "Working…", spinning = true }) {
  return el(
    "div",
    { class: "statusbar" },
    spinning ? el("span", { class: "spinner" }) : el("span", { class: "led on" }),
    el("span", {}, text)
  );
}
