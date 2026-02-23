export const animations = Object.freeze({
  durations: {
    fast: "170ms",
    normal: "290ms",
    slow: "520ms",
    breathing: "8s",
  },
  easing: {
    standard: "cubic-bezier(0.22, 1, 0.36, 1)",
    smooth: "cubic-bezier(0.2, 0.8, 0.2, 1)",
    gentle: "cubic-bezier(0.25, 0.46, 0.45, 0.94)",
  },
  utilities: {
    fadeInUp: "motion-fade-in-up",
    scaleHover: "motion-scale-hover",
    pulseGlow: "motion-pulse-glow",
    breathing: "motion-breathing",
    smoothCollapse: "motion-collapse",
    typingDots: "motion-typing-dots",
  },
});

export function applyMotion(element, utilityName) {
  if (!element || !utilityName) return;
  const className = animations.utilities[utilityName];
  if (className) {
    element.classList.add(className);
  }
}

export function getMotionVars() {
  return {
    "--motion-duration-fast": animations.durations.fast,
    "--motion-duration-normal": animations.durations.normal,
    "--motion-duration-slow": animations.durations.slow,
    "--motion-duration-breathing": animations.durations.breathing,
    "--motion-ease-standard": animations.easing.standard,
    "--motion-ease-smooth": animations.easing.smooth,
    "--motion-ease-gentle": animations.easing.gentle,
  };
}
