import { makeSlide } from "./common.mjs";

const data = {
  "no": 15,
  "title": "結論：高次化の本体は、演算子次数ではなく界面面契約の整合である",
  "lead": "本研究は、CCD/FCCD/UCCD6を核に分相PPE+HFE+DC・Balanced-Force face subsystemを統合し、合格範囲と未解決範囲を検証軸として固定した。",
  "source": "Conclusion",
  "visual": "takeaways",
  "takeaways": [
    "寄生流れの離散化起因成分を構造的に低減",
    "密度比 <= 833 まで pressure-jump stack の有界性を確認",
    "二相時間精度と強変形CLSの設計限界を次の研究ゲートとして明示"
  ]
};

export async function slide15(presentation, ctx) {
  return makeSlide(presentation, ctx, data);
}
