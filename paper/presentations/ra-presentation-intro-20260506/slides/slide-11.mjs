import { makeSlide } from "./common.mjs";

const data = {
  "no": 11,
  "title": "統合検証は、合格領域と条件付き領域を分けて読む",
  "lead": "V1--V10は x ゼロだが、V7とV10の形状軸はType-Dとして設計限界を明示した。",
  "source": "paper/sections/13_verification.tex; 13f_error_budget.tex",
  "visual": "verdictBars",
  "bars": [
    [
      "Design / Type-A",
      8,
      "#1B998B"
    ],
    [
      "Type-B",
      2,
      "#F0B429"
    ],
    [
      "Type-D",
      3,
      "#D95D39"
    ],
    [
      "Out of scope",
      0,
      "#9CA3AF"
    ]
  ]
};

export async function slide11(presentation, ctx) {
  return makeSlide(presentation, ctx, data);
}
