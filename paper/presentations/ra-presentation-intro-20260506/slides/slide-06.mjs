import { makeSlide } from "./common.mjs";

const data = {
  "no": 6,
  "title": "界面追跡は、保存形輸送と距離関数修復を分けて設計する",
  "lead": "FCCD flux-form で質量を運び、Ridge--Eikonal 再初期化で距離関数品質を戻す。",
  "source": "CLS transport; Ridge-Eikonal; CLS stages; component verification",
  "visual": "stageRail",
  "stages": [
    "移流",
    "クランプ",
    "逆変換",
    "Eikonal",
    "DGR",
    "曲率"
  ],
  "metricCallout": "epsilon_eff / epsilon_*: 2.0 → 1.0000033"
};

export async function slide06(presentation, ctx) {
  return makeSlide(presentation, ctx, data);
}
