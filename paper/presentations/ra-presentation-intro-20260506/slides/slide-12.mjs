import { makeSlide } from "./common.mjs";

const data = {
  "no": 12,
  "title": "寄生流れは、FD基準より小さい絶対スケールへ抑制",
  "lead": "静止液滴と密度比sweepでは、CCD/BF構成とpressure-jump stackの安定性を別々の指標で確認した。",
  "source": "Static droplet; density-ratio sweep; error budget",
  "visual": "evidenceCards",
  "metrics": [
    [
      "静止液滴",
      "0.97%",
      "Laplace pressure error at N=128"
    ],
    [
      "寄生流れ",
      "1.93e-2",
      "u_inf end at rho_r=1,N=32"
    ],
    [
      "密度比",
      "rho_r <= 833",
      "no blow-up"
    ],
    [
      "体積保存",
      "6.4e-16",
      "volume drift floor"
    ]
  ]
};

export async function slide12(presentation, ctx) {
  return makeSlide(presentation, ctx, data);
}
