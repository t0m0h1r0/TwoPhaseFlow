import { makeSlide } from "./common.mjs";

const data = {
  "no": 1,
  "kind": "title",
  "title": "CCD/FCCD/UCCD6を核にした二相流数値法",
  "lead": "保存形界面追跡・Balanced-Force・pressure-jump分相PPEを、CCDファミリの面幾何で閉じる。",
  "kicker": "流体力学会向け 研究内容紹介",
  "source": "Abstract; Introduction",
  "tags": [
    "CCD node derivatives",
    "FCCD face flux",
    "UCCD6 momentum",
    "DCCD damping"
  ]
};

export async function slide01(presentation, ctx) {
  return makeSlide(presentation, ctx, data);
}
