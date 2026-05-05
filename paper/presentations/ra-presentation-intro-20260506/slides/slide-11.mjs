import { makeSlide } from "./common.mjs";

const data = {
  "no": 11,
  "title": "統合検証は、合格領域・構造修正・設計限界を分けて読む",
  "lead": "単に「全ケース合格」と言わず、通常合格、質量補正での合格、理論的限界に分解した。",
  "source": "Integrated verification; error budget",
  "visual": "verdictBars",
  "bars": [
    [
      "通常合格 / 文献基準",
      8,
      "#1B998B"
    ],
    [
      "質量補正で合格",
      2,
      "#F0B429"
    ],
    [
      "設計限界として記録",
      3,
      "#D95D39"
    ],
    [
      "保証範囲外",
      0,
      "#9CA3AF"
    ]
  ]
};

export async function slide11(presentation, ctx) {
  return makeSlide(presentation, ctx, data);
}
