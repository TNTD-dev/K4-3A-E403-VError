// Course catalogue for the prototype. Only Day 04 has a real reviewed deck + VError items.
const DAY04_DECK = {
  file: "prompt-engineering-tool-calling",
  pdf: "/prompt-engineering-tool-calling.pdf",
  title: "Prompt Engineering & Tool Calling",
  lab: {
    title: "Lab 04 — Prompt & Tool Calling",
    // Pages of the hands-on part inside the deck.
    steps: [
      { label: "Hands-on 4: Cách chạy lab", page: 36 },
      { label: "Lab skeleton — Python", page: 37 },
      { label: "Lab #4 · Deliverable", page: 38 },
    ],
  },
};

export const ACTIVE_DAY = "D04";

export const LESSONS = [
  { day: "D01", lesson: 1, label: "Buổi 1: Day01", short: "Day01" },
  { day: "D02", lesson: 2, label: "Buổi 2: DAY02", short: "Day02" },
  { day: "D03", lesson: 3, label: "Buổi 3: DAY03", short: "Day03" },
  { day: "D04", lesson: 4, label: "Buổi 4: DAY04", short: "Day04", deck: DAY04_DECK },
  { day: "D16", lesson: 16, label: "Buổi 16: MINI HACKATHON", short: "Mini Hackathon" },
  { day: "D05", lesson: 5, label: "Buổi 5: Day05", short: "Day05" },
  { day: "D06", lesson: 6, label: "Buổi 6: Day06", short: "Day06" },
  { day: "D07", lesson: 7, label: "Buổi 7: Day07", short: "Day07" },
  { day: "D08", lesson: 8, label: "Buổi 8: Day08", short: "Day08" },
  { day: "D09", lesson: 9, label: "Buổi 9: Day09", short: "Day09" },
  { day: "D10", lesson: 10, label: "Buổi 10: Day10", short: "Day10" },
];

export function lessonByDay(day) {
  return LESSONS.find(item => item.day === day) || null;
}
