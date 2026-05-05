import { makeSlide } from "./common.mjs";

const data = {
  "no": 3,
  "title": "計算コアはCCDファミリ：微分・面フラックス・運動量対流",
  "lead": "CCDが節点微分、FCCDが面値/面勾配、UCCD6が運動量対流を担い、その上に圧力閉包と界面追跡を載せる。",
  "source": "Introduction; collocated face geometry; full algorithm",
  "visual": "threePillars",
  "pillars": [
    [
      "CCD/FCCD/UCCD6",
      "節点微分・面フラックス・運動量対流"
    ],
    [
      "圧力ジャンプ閉包",
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
