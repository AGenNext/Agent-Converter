// Storybook stories for the Research Agent chat UI components.
import "./theme.css";
import {
  ConfidenceChip,
  MessageBubble,
  FindingItem,
  SourceItem,
  StatusBar,
} from "./components.js";

export default {
  title: "Research Agent/Components",
};

export const ConfidenceChips = () => {
  const wrap = document.createElement("div");
  wrap.style.display = "flex";
  wrap.style.gap = "8px";
  ["HIGH", "MEDIUM", "LOW", "UNVERIFIED"].forEach((l) =>
    wrap.appendChild(ConfidenceChip(l))
  );
  return wrap;
};

export const UserMessage = () =>
  MessageBubble({
    role: "user",
    text: "Research Parkwalk Advisors for a UK aerospace seed. Fit + red flags.",
  });

export const AgentMessage = () =>
  MessageBubble({
    role: "agent",
    text: "Strong thematic fit. Parkwalk focuses on UK university spin-outs in deep tech.",
  });

export const Finding = () =>
  FindingItem({
    text: "Typical seed cheque roughly £1M–£3M, often with co-investors.",
    source: "PitchBook deal history · 2 recent rounds",
    confidence: "HIGH",
  });

export const Source = () =>
  SourceItem({ tier: "T5", label: "PitchBook — fund & deal data" });

export const Status = () =>
  StatusBar({ text: "Delegating to a specialist pack…", spinning: true });

export const ReadyStatus = () =>
  StatusBar({ text: "Agent ready", spinning: false });
