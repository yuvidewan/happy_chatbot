export const emotionThemes = Object.freeze({
  sadness: {
    accent: "#7ca9ff",
    accentSoft: "rgba(124, 169, 255, 0.26)",
    ambientGlow: "rgba(136, 177, 255, 0.46)",
    bubbleBotStart: "rgba(41, 84, 139, 0.82)",
    bubbleBotEnd: "rgba(58, 95, 162, 0.9)",
  },
  joy: {
    accent: "#f2b866",
    accentSoft: "rgba(242, 184, 102, 0.24)",
    ambientGlow: "rgba(245, 201, 133, 0.44)",
    bubbleBotStart: "rgba(127, 96, 45, 0.84)",
    bubbleBotEnd: "rgba(164, 121, 52, 0.9)",
  },
  anxiety: {
    accent: "#9f8eff",
    accentSoft: "rgba(159, 142, 255, 0.26)",
    ambientGlow: "rgba(176, 166, 255, 0.45)",
    bubbleBotStart: "rgba(62, 53, 118, 0.84)",
    bubbleBotEnd: "rgba(84, 72, 147, 0.9)",
  },
  neutral: {
    accent: "#59c5bc",
    accentSoft: "rgba(89, 197, 188, 0.24)",
    ambientGlow: "rgba(115, 213, 205, 0.42)",
    bubbleBotStart: "rgba(26, 95, 90, 0.84)",
    bubbleBotEnd: "rgba(36, 125, 116, 0.9)",
  },
});

const emotionRules = Object.freeze({
  defaultEmotion: "neutral",
  bySentiment: {
    low: "sadness",
    high: "joy",
    neutral: "neutral",
  },
  byContext: {
    sadness: [
      "sadness",
      "sad",
      "grief",
      "heartbreak",
      "heartbroken",
      "lonely",
      "loss",
      "breakup",
      "depressed",
    ],
    anxiety: [
      "anxiety",
      "anxious",
      "stress",
      "stressed",
      "panic",
      "overwhelmed",
      "burnout",
      "nervous",
      "worry",
    ],
    joy: [
      "joy",
      "happy",
      "gratitude",
      "celebration",
      "achievement",
      "motivation",
      "excited",
    ],
    neutral: ["general", "greeting", "technical", "study", "career", "relationship", "sleep", "fitness"],
  },
});

function normalizeSignal(value) {
  return String(value || "").trim().toLowerCase();
}

export function resolveEmotion(signals = {}) {
  const contextSignal = normalizeSignal(signals.context);
  const sentimentSignal = normalizeSignal(signals.sentiment);

  for (const [emotion, aliases] of Object.entries(emotionRules.byContext)) {
    if (aliases.includes(contextSignal)) {
      return emotion;
    }
  }

  const bySentiment = emotionRules.bySentiment[sentimentSignal];
  if (bySentiment) {
    return bySentiment;
  }

  return emotionRules.defaultEmotion;
}
