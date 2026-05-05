import { makeSlide } from "./common.mjs";

const data = {
  "no": 7,
  "title": "高密度比では、一括PPEではなく分相PPEとして圧力を閉じる",
  "lead": "相内Poisson、HFE場延長、欠陥補正DCを組み合わせ、ジャンプ条件をPPEとcorrectorが共有する。",
  "source": "Split PPE; HFE; defect correction; component verification",
  "visual": "pressureClosure",
  "metrics": [
    [
      "HFE 1D",
      "h^5.91",
      "Hermite 場延長"
    ],
    [
      "DC k=3",
      "h^6.90",
      "Dirichlet production"
    ],
    [
      "残差",
      "7e-6",
      "split PPE + DC"
    ]
  ]
};

export async function slide07(presentation, ctx) {
  return makeSlide(presentation, ctx, data);
}
