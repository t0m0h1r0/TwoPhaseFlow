import { makeSlide } from "./common.mjs";

const data = {
  "no": 3,
  "title": "本研究の主張は、寄生流れを「調整」ではなく離散契約で抑えること",
  "lead": "曲率・圧力・速度補正・界面輸送を face-space contract に集約し、Balanced-Force 条件を演算子レベルで保つ。",
  "source": "paper/sections/01_introduction.tex; 08_collocate.tex; 11_full_algorithm.tex",
  "visual": "threePillars",
  "pillars": [
    [
      "高次演算子群",
      "CCD / DCCD / UCCD6 / FCCD"
    ],
    [
      "圧力閉包",
      "phase-separated PPE + HFE + DC k=3"
    ],
    [
      "面幾何共有",
      "FCCD face jet + projection-native face velocity"
    ]
  ]
};

export async function slide03(presentation, ctx) {
  return makeSlide(presentation, ctx, data);
}
