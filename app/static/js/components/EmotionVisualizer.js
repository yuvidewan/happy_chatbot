import { applyMotion } from "../theme/animations.js";

export function EmotionVisualizer() {
  const element = document.createElement("div");
  element.className = "emotion-visualizer";
  element.setAttribute("aria-hidden", "true");

  const orbMain = document.createElement("div");
  orbMain.className = "emotion-visualizer__orb emotion-visualizer__orb--primary";
  applyMotion(orbMain, "breathing");

  const orbSecondary = document.createElement("div");
  orbSecondary.className = "emotion-visualizer__orb emotion-visualizer__orb--secondary";
  applyMotion(orbSecondary, "breathing");

  element.append(orbMain, orbSecondary);

  return { element };
}
