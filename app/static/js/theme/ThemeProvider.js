import { getMotionVars } from "./animations.js";
import { baseTheme } from "./baseTheme.js";
import { emotionThemes, resolveEmotion } from "./emotionThemes.js";

function toCssVariableLines(tokenMap) {
  return Object.entries(tokenMap)
    .map(([key, value]) => `${key}: ${value};`)
    .join("\n");
}

function baseTokenVars(themeMode, emotionKey) {
  const mode = baseTheme.modes[themeMode] || baseTheme.modes.dark;
  const emotion = emotionThemes[emotionKey] || emotionThemes.neutral;
  const { colors, shadows } = mode;

  return {
    "--space-xs": baseTheme.spacing.xs,
    "--space-sm": baseTheme.spacing.sm,
    "--space-md": baseTheme.spacing.md,
    "--space-lg": baseTheme.spacing.lg,
    "--space-xl": baseTheme.spacing.xl,
    "--space-xxl": baseTheme.spacing.xxl,
    "--font-display": baseTheme.typography.familyDisplay,
    "--font-body": baseTheme.typography.familyBody,
    "--text-heading-size": baseTheme.typography.heading.size,
    "--text-heading-weight": baseTheme.typography.heading.weight,
    "--text-heading-line": baseTheme.typography.heading.lineHeight,
    "--text-heading-spacing": baseTheme.typography.heading.letterSpacing,
    "--text-subheading-size": baseTheme.typography.subheading.size,
    "--text-subheading-weight": baseTheme.typography.subheading.weight,
    "--text-subheading-line": baseTheme.typography.subheading.lineHeight,
    "--text-body-size": baseTheme.typography.body.size,
    "--text-body-weight": baseTheme.typography.body.weight,
    "--text-body-line": baseTheme.typography.body.lineHeight,
    "--text-caption-size": baseTheme.typography.caption.size,
    "--text-caption-weight": baseTheme.typography.caption.weight,
    "--text-caption-line": baseTheme.typography.caption.lineHeight,
    "--color-bg-base": colors.bgBase,
    "--color-bg-radial-a": colors.bgRadialA,
    "--color-bg-radial-b": colors.bgRadialB,
    "--color-bg-radial-c": colors.bgRadialC,
    "--color-grain": colors.grain,
    "--color-vignette": colors.vignette,
    "--color-surface-glass": colors.surfaceGlass,
    "--color-surface-glass-strong": colors.surfaceGlassStrong,
    "--color-surface-border": colors.surfaceBorder,
    "--color-text-primary": colors.textPrimary,
    "--color-text-secondary": colors.textSecondary,
    "--color-text-muted": colors.textMuted,
    "--color-text-inverse": colors.textInverse,
    "--color-focus-ring": colors.focusRing,
    "--color-user-bubble-start": colors.userBubbleStart,
    "--color-user-bubble-end": colors.userBubbleEnd,
    "--color-button-surface": colors.buttonSurface,
    "--color-button-surface-active": colors.buttonSurfaceActive,
    "--color-danger": colors.danger,
    "--shadow-panel": shadows.panel,
    "--shadow-bubble": shadows.bubble,
    "--shadow-floating": shadows.floating,
    "--color-accent": emotion.accent,
    "--color-accent-soft": emotion.accentSoft,
    "--color-emotion-glow": emotion.ambientGlow,
    "--color-bot-bubble-start": emotion.bubbleBotStart,
    "--color-bot-bubble-end": emotion.bubbleBotEnd,
    ...getMotionVars(),
  };
}

export class ThemeProvider {
  constructor({ storageKey = "happybot_theme", styleTagId = "runtime-theme-vars" } = {}) {
    this.storageKey = storageKey;
    this.styleTagId = styleTagId;
    this.mode = "dark";
    this.emotion = "neutral";
    this.listeners = new Set();
  }

  init() {
    const savedMode = localStorage.getItem(this.storageKey);
    if (savedMode === "dark" || savedMode === "light") {
      this.mode = savedMode;
    } else {
      const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
      this.mode = prefersDark ? "dark" : "light";
    }
    this.apply();
  }

  subscribe(listener) {
    if (typeof listener !== "function") return () => {};
    this.listeners.add(listener);
    listener(this.getSnapshot());
    return () => {
      this.listeners.delete(listener);
    };
  }

  getSnapshot() {
    return {
      mode: this.mode,
      emotion: this.emotion,
      meta: baseTheme.meta,
      icons: baseTheme.icons,
    };
  }

  setEmotionSignals(signals = {}) {
    const resolved = resolveEmotion(signals);
    if (resolved === this.emotion) return;
    this.emotion = resolved;
    this.apply();
  }

  toggleMode() {
    this.mode = this.mode === "dark" ? "light" : "dark";
    localStorage.setItem(this.storageKey, this.mode);
    this.apply();
  }

  apply() {
    const vars = baseTokenVars(this.mode, this.emotion);
    const styleBlock = `:root {\n${toCssVariableLines(vars)}\n}`;
    let styleTag = document.getElementById(this.styleTagId);
    if (!styleTag) {
      styleTag = document.createElement("style");
      styleTag.id = this.styleTagId;
      document.head.appendChild(styleTag);
    }
    styleTag.textContent = styleBlock;
    document.documentElement.setAttribute("data-theme-mode", this.mode);
    document.documentElement.setAttribute("data-emotion", this.emotion);
    for (const listener of this.listeners) {
      listener(this.getSnapshot());
    }
  }
}
