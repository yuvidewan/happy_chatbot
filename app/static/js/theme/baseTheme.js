import { animations } from "./animations.js";
import { spacing } from "./spacing.js";
import { typography } from "./typography.js";

export const baseTheme = Object.freeze({
  meta: {
    appTitle: "HappyBot",
    appSubtitle: "A warm conversation space for clarity, support, and momentum.",
    supportPanelTitle: "Support Toolkit",
    supportPanelSubtitle: "Practical suggestions that adapt with each reply.",
    welcomeMessage: "Hi, I am HappyBot. Share what is on your mind, ask for a joke, or ask for help sorting your next step.",
    inputLabel: "Type your message",
    inputPlaceholder: "Share what is on your mind",
    sendLabel: "Send",
    sendingLabel: "Sending",
    retryLabel: "Retry",
    thinkingLabel: "HappyBot is thinking",
    unavailableSupportMessage: "Support suggestions are temporarily unavailable.",
    chatErrorMessage: "I hit a connection issue. Please try again.",
    supportRetryMessage: "Chat is still available. Send another message to refresh support cards.",
    modeToggle: {
      light: "Light",
      dark: "Dark",
    },
  },
  icons: {
    send:
      "<svg viewBox=\"0 0 24 24\" aria-hidden=\"true\" focusable=\"false\"><path d=\"M3 12.8L20.2 4c.8-.4 1.6.3 1.4 1.2l-2.5 13.2c-.2.9-1.2 1.2-1.8.7l-4.2-3.3-3.5 3.7c-.4.4-1 .3-1.2-.2l-1.1-3.7-4.4-1.3c-.9-.2-1-1.4-.1-1.9zm4.4.2l3.2 1 6.5-6.6-9.7 5.6z\"/></svg>",
    collapseOpen:
      "<svg viewBox=\"0 0 24 24\" aria-hidden=\"true\" focusable=\"false\"><path d=\"M7 10l5 5 5-5\"/></svg>",
    collapseClosed:
      "<svg viewBox=\"0 0 24 24\" aria-hidden=\"true\" focusable=\"false\"><path d=\"M7 14l5-5 5 5\"/></svg>",
    supportCardSymbols: ["spark", "path", "bloom", "focus", "resource"],
  },
  modes: {
    dark: {
      colors: {
        bgBase: "#070d17",
        bgRadialA: "rgba(31, 54, 81, 0.72)",
        bgRadialB: "rgba(14, 47, 51, 0.7)",
        bgRadialC: "rgba(34, 30, 64, 0.6)",
        grain: "rgba(250, 252, 255, 0.07)",
        vignette: "rgba(4, 8, 15, 0.72)",
        surfaceGlass: "rgba(13, 22, 35, 0.62)",
        surfaceGlassStrong: "rgba(12, 20, 32, 0.7)",
        surfaceBorder: "rgba(232, 242, 255, 0.09)",
        textPrimary: "#edf4ff",
        textSecondary: "#d0dceb",
        textMuted: "#9cb0c8",
        textInverse: "#f4f8ff",
        focusRing: "rgba(154, 214, 255, 0.4)",
        userBubbleStart: "rgba(66, 136, 255, 0.95)",
        userBubbleEnd: "rgba(107, 92, 255, 0.92)",
        buttonSurface: "rgba(20, 30, 44, 0.82)",
        buttonSurfaceActive: "rgba(26, 40, 58, 0.9)",
        danger: "#ff8f8f",
      },
      shadows: {
        panel: "0 22px 70px rgba(2, 7, 16, 0.48)",
        bubble: "0 14px 34px rgba(4, 8, 17, 0.35)",
        floating: "0 20px 44px rgba(3, 8, 15, 0.42)",
      },
    },
    light: {
      colors: {
        bgBase: "#f2f7ff",
        bgRadialA: "rgba(198, 224, 255, 0.84)",
        bgRadialB: "rgba(202, 237, 238, 0.84)",
        bgRadialC: "rgba(222, 216, 255, 0.78)",
        grain: "rgba(25, 39, 62, 0.08)",
        vignette: "rgba(201, 214, 232, 0.55)",
        surfaceGlass: "rgba(248, 252, 255, 0.68)",
        surfaceGlassStrong: "rgba(245, 250, 255, 0.75)",
        surfaceBorder: "rgba(22, 56, 96, 0.14)",
        textPrimary: "#11243b",
        textSecondary: "#203851",
        textMuted: "#4f6886",
        textInverse: "#f6faff",
        focusRing: "rgba(61, 126, 199, 0.32)",
        userBubbleStart: "rgba(57, 119, 241, 0.92)",
        userBubbleEnd: "rgba(93, 86, 223, 0.88)",
        buttonSurface: "rgba(231, 238, 247, 0.9)",
        buttonSurfaceActive: "rgba(217, 227, 239, 0.95)",
        danger: "#d96f6f",
      },
      shadows: {
        panel: "0 20px 58px rgba(78, 105, 141, 0.18)",
        bubble: "0 10px 30px rgba(80, 106, 141, 0.18)",
        floating: "0 20px 44px rgba(79, 110, 146, 0.24)",
      },
    },
  },
  spacing,
  typography,
  animations,
});
