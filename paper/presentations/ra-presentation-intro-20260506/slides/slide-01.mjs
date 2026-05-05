import { makeSlide } from "./common.mjs";

const data = {
  "no": 1,
  "kind": "title",
  "title": "高次コンパクト差分に基づく気液二相流数値法",
  "lead": "保存形界面追跡・Balanced-Force・pressure-jump 分相PPEを、同じ面幾何で閉じる。",
  "kicker": "流体力学会向け 研究内容紹介",
  "source": "paper/sections/00_abstract.tex; 01_introduction.tex",
  "tags": [
    "Conservative Level Set",
    "FCCD face jet",
    "Phase-separated PPE",
    "HFE + DC"
  ]
};

export async function slide01(presentation, ctx) {
  return makeSlide(presentation, ctx, data);
}
