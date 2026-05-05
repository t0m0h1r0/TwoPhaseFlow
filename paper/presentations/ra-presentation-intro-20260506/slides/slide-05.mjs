import { makeSlide } from "./common.mjs";

const data = {
  "no": 5,
  "title": "CCDファミリは、節点中心の高次性を面中心の保存形へ広げる",
  "lead": "内点6次のCCDを起点に、DCCDで高波数を制御し、UCCD6とFCCDで運動量・界面フラックスを分担する。",
  "source": "paper/sections/04_ccd.tex; 04c_dccd_derivation.tex; 04d_uccd6.tex; 04e_fccd.tex",
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
