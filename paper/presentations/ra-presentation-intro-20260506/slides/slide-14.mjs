import { makeSlide } from "./common.mjs";

const data = {
  "no": 14,
  "title": "物理ベンチマークは、毛管波の符号検証から次のゲートへ進む",
  "lead": "向き付き affine jump は短時間の復元力符号を通したが、気泡上昇とRayleigh--Taylorは未完了検証として分離する。",
  "source": "paper/sections/14_benchmarks.tex; 15_conclusion.tex",
  "visual": "benchmarkRoadmap",
  "stages": [
    [
      "毛管波",
      "A''符号・大きさを確認",
      "進行中"
    ],
    [
      "気泡上昇",
      "yc(t), rise velocity, deformation",
      "未完了gate"
    ],
    [
      "Rayleigh--Taylor",
      "線形成長率とmushroom形成",
      "未完了gate"
    ]
  ]
};

export async function slide14(presentation, ctx) {
  return makeSlide(presentation, ctx, data);
}
