import { makeSlide } from "./common.mjs";

const data = {
  "no": 10,
  "title": "単体検証は、CCDファミリと圧力閉包が単独で働くことを確認",
  "lead": "基礎演算・非一様格子・静止液滴・圧力DCCD禁止を、式と観測指標の対応で確認した。",
  "source": "Component verification summary",
  "visual": "uTests",
  "metrics": [
    [
      "CCD演算子",
      "h^6.0",
      "節点微分"
    ],
    [
      "非一様格子",
      "GCL 2.13e-13",
      "metric consistency"
    ],
    [
      "静止液滴",
      "0.61%",
      "Laplace error"
    ],
    [
      "圧力DCCD",
      "禁止",
      "pressureには適用しない"
    ]
  ]
};

export async function slide10(presentation, ctx) {
  return makeSlide(presentation, ctx, data);
}
