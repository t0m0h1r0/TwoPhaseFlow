import { makeSlide } from "./common.mjs";

const data = {
  "no": 5,
  "title": "CCD -> FCCD/UCCD6 が、この数値法の演算子コア",
  "lead": "CCDの高次微分を、FCCDの保存形face fluxとUCCD6の運動量対流へ展開する。DCCDは補助的な高波数制御に限定する。",
  "source": "CCD, DCCD, UCCD6, and FCCD operator derivations",
  "visual": "operatorStack",
  "metrics": [
    [
      "CCD",
      "h^6.0",
      "内点微分"
    ],
    [
      "FCCD",
      "h^4.00",
      "面値/面勾配"
    ],
    [
      "UCCD6",
      "h^7.00",
      "対流スーパー収束"
    ],
    [
      "DCCD",
      "H(pi)=0",
      "Nyquist 抑制"
    ]
  ],
  "image": "dccd_waveforms_panel.png"
};

export async function slide05(presentation, ctx) {
  return makeSlide(presentation, ctx, data);
}
