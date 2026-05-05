import { makeSlide } from "./common.mjs";

const data = {
  "no": 2,
  "title": "二相流の難しさは、界面が方程式の全項を同時に壊すことにある",
  "lead": "密度・粘性・曲率・圧力ジャンプが同じ場所で不連続になるため、単相流の高次化だけでは寄生流れを止められない。",
  "source": "Introduction",
  "visual": "problemMatrix",
  "bullets": [
    [
      "物性ジャンプ",
      "rho_l/rho_g は水/空気で約1000"
    ],
    [
      "界面追跡",
      "質量保存と鮮鋭性を同時に要求"
    ],
    [
      "曲率",
      "二階微分誤差が表面張力へ増幅"
    ],
    [
      "圧力",
      "PPEと速度補正が界面条件を共有する必要"
    ]
  ]
};

export async function slide02(presentation, ctx) {
  return makeSlide(presentation, ctx, data);
}
