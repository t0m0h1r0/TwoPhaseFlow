import { makeSlide } from "./common.mjs";

const data = {
  "no": 8,
  "title": "Balanced-Force の条件は、同じface footprintを共有することに落ちる",
  "lead": "圧力勾配、表面張力、HFE上流点、GFMジャンプを別々に作ると、同じ式を使っても釣合いは崩れる。",
  "source": "paper/sections/08_collocate.tex; 11_full_algorithm.tex; 14_benchmarks.tex",
  "visual": "faceContract",
  "center": "FCCD face jet J_f(u)",
  "spokes": [
    "pressure gradient",
    "surface tension",
    "HFE upwind",
    "GFM jump",
    "projection face velocity"
  ]
};

export async function slide08(presentation, ctx) {
  return makeSlide(presentation, ctx, data);
}
