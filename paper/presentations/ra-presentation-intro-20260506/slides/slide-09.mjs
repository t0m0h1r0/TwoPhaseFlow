import { makeSlide } from "./common.mjs";

const data = {
  "no": 9,
  "title": "1タイムステップは、界面面幾何を先に閉じてからNS更新へ渡す",
  "lead": "7段更新は部品表ではなく、psi・phi・rho・mu・kappa・face-state の受け渡し契約である。",
  "source": "Full algorithm",
  "visual": "sevenStep",
  "stages": [
    "CLS移流",
    "再初期化",
    "物性更新",
    "曲率",
    "予測",
    "PPE",
    "補正"
  ]
};

export async function slide09(presentation, ctx) {
  return makeSlide(presentation, ctx, data);
}
