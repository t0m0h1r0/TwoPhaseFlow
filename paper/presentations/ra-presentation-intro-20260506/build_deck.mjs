import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const slidesDir = path.join(here, "slides");
const outputDir = path.join(here, "output");

const slides = [
  {
    no: 1,
    kind: "title",
    title: "CCD/FCCD/UCCD6を核にした二相流数値法",
    lead: "保存形界面追跡・Balanced-Force・pressure-jump分相PPEを、CCDファミリの面幾何で閉じる。",
    kicker: "流体力学会向け 研究内容紹介",
    source: "Abstract; Introduction",
    sourceFiles: ["paper/sections/00_abstract.tex", "paper/sections/01_introduction.tex"],
    tags: ["CCD node derivatives", "FCCD face flux", "UCCD6 momentum", "DCCD damping"],
  },
  {
    no: 2,
    title: "二相流の難しさは、界面が方程式の全項を同時に壊すことにある",
    lead: "密度・粘性・曲率・圧力ジャンプが同じ場所で不連続になるため、単相流の高次化だけでは寄生流れを止められない。",
    source: "Introduction",
    sourceFiles: ["paper/sections/01_introduction.tex"],
    visual: "problemMatrix",
    bullets: [
      ["物性ジャンプ", "rho_l/rho_g は水/空気で約1000"],
      ["界面追跡", "質量保存と鮮鋭性を同時に要求"],
      ["曲率", "二階微分誤差が表面張力へ増幅"],
      ["圧力", "PPEと速度補正が界面条件を共有する必要"],
    ],
  },
  {
    no: 3,
    title: "計算コアはCCDファミリ：微分・面フラックス・運動量対流",
    lead: "CCDが節点微分、FCCDが面値/面勾配、UCCD6が運動量対流を担い、その上に圧力閉包と界面追跡を載せる。",
    source: "Introduction; collocated face geometry; full algorithm",
    sourceFiles: ["paper/sections/01_introduction.tex", "paper/sections/08_collocate.tex", "paper/sections/11_full_algorithm.tex"],
    visual: "threePillars",
    pillars: [
      ["CCD/FCCD/UCCD6", "節点微分・面フラックス・運動量対流"],
      ["圧力ジャンプ閉包", "phase-separated PPE + HFE + DC k=3"],
      ["面幾何共有", "FCCD face jet + projection-native face velocity"],
    ],
  },
  {
    no: 4,
    title: "One-Fluid 表現は入口であり、圧力ジャンプの扱いが出口を決める",
    lead: "CLS は界面を保存形に追跡し、Young--Laplace ジャンプは CSF 体積力ではなく pressure-jump として PPE に渡す。",
    source: "Governing equations; surface tension jump; CLS; split PPE",
    sourceFiles: ["paper/sections/02_governing.tex", "paper/sections/02b_surface_tension.tex", "paper/sections/03_levelset.tex", "paper/sections/09b1_split_ppe.tex"],
    visual: "equationFlow",
    flow: [
      ["psi = H_e(-phi)", "保存形界面変数"],
      ["kappa_lg", "HFE / direct-psi 曲率"],
      ["j_gl = p_g - p_l", "-sigma kappa_lg"],
      ["G(p) - B(j)", "affine jump corrector"],
    ],
  },
  {
    no: 5,
    title: "CCD -> FCCD/UCCD6 が、この数値法の演算子コア",
    lead: "CCDの高次微分を、FCCDの保存形face fluxとUCCD6の運動量対流へ展開する。DCCDは補助的な高波数制御に限定する。",
    source: "CCD, DCCD, UCCD6, and FCCD operator derivations",
    sourceFiles: ["paper/sections/04_ccd.tex", "paper/sections/04c_dccd_derivation.tex", "paper/sections/04d_uccd6.tex", "paper/sections/04e_fccd.tex"],
    visual: "operatorStack",
    metrics: [
      ["CCD", "h^6.0", "内点微分"],
      ["FCCD", "h^4.00", "面値/面勾配"],
      ["UCCD6", "h^7.00", "対流スーパー収束"],
      ["DCCD", "H(pi)=0", "Nyquist 抑制"],
    ],
    image: "dccd_waveforms_panel.png",
  },
  {
    no: 6,
    title: "界面追跡は、保存形輸送と距離関数修復を分けて設計する",
    lead: "FCCD flux-form で質量を運び、Ridge--Eikonal 再初期化で距離関数品質を戻す。",
    source: "CLS transport; Ridge-Eikonal; CLS stages; component verification",
    sourceFiles: ["paper/sections/03b_cls_transport.tex", "paper/sections/03d_ridge_eikonal.tex", "paper/sections/05b_cls_stages.tex", "paper/sections/12_component_verification.tex"],
    visual: "stageRail",
    stages: ["移流", "クランプ", "逆変換", "Eikonal", "DGR", "曲率"],
    metricCallout: "epsilon_eff / epsilon_*: 2.0 → 1.0000033",
  },
  {
    no: 7,
    title: "高密度比では、一括PPEではなく分相PPEとして圧力を閉じる",
    lead: "相内Poisson、HFE場延長、欠陥補正DCを組み合わせ、ジャンプ条件をPPEとcorrectorが共有する。",
    source: "Split PPE; HFE; defect correction; component verification",
    sourceFiles: ["paper/sections/09b1_split_ppe.tex", "paper/sections/09c_hfe.tex", "paper/sections/09d_defect_correction.tex", "paper/sections/12u6_split_ppe_dc_hfe.tex"],
    visual: "pressureClosure",
    metrics: [
      ["HFE 1D", "h^5.91", "Hermite 場延長"],
      ["DC k=3", "h^6.90", "Dirichlet production"],
      ["残差", "7e-6", "split PPE + DC"],
    ],
  },
  {
    no: 8,
    title: "Balanced-Force の条件は、同じface footprintを共有することに落ちる",
    lead: "圧力勾配、表面張力、HFE上流点、GFMジャンプを別々に作ると、同じ式を使っても釣合いは崩れる。",
    source: "Collocated face geometry; full algorithm; benchmark conditions",
    sourceFiles: ["paper/sections/08_collocate.tex", "paper/sections/11_full_algorithm.tex", "paper/sections/14_benchmarks.tex"],
    visual: "faceContract",
    center: "FCCD face jet J_f(u)",
    spokes: ["pressure gradient", "surface tension", "HFE upwind", "GFM jump", "projection face velocity"],
  },
  {
    no: 9,
    title: "1タイムステップは、界面面幾何を先に閉じてからNS更新へ渡す",
    lead: "7段更新は部品表ではなく、psi・phi・rho・mu・kappa・face-state の受け渡し契約である。",
    source: "Full algorithm",
    sourceFiles: ["paper/sections/11_full_algorithm.tex"],
    visual: "sevenStep",
    stages: ["CLS移流", "再初期化", "物性更新", "曲率", "予測", "PPE", "補正"],
  },
  {
    no: 10,
    title: "単体検証は、CCDファミリと圧力閉包が単独で働くことを確認",
    lead: "基礎演算・非一様格子・静止液滴・圧力DCCD禁止を、式と観測指標の対応で確認した。",
    source: "Component verification summary",
    sourceFiles: ["paper/sections/12_component_verification.tex", "paper/sections/12h_summary.tex"],
    visual: "uTests",
    metrics: [
      ["CCD演算子", "h^6.0", "節点微分"],
      ["非一様格子", "GCL 2.13e-13", "metric consistency"],
      ["静止液滴", "0.61%", "Laplace error"],
      ["圧力DCCD", "禁止", "pressureには適用しない"],
    ],
  },
  {
    no: 11,
    title: "統合検証は、合格領域・構造修正・設計限界を分けて読む",
    lead: "単に「全ケース合格」と言わず、通常合格、質量補正での合格、理論的限界に分解した。",
    source: "Integrated verification; error budget",
    sourceFiles: ["paper/sections/13_verification.tex", "paper/sections/13f_error_budget.tex"],
    visual: "verdictBars",
    bars: [
      ["通常合格 / 文献基準", 8, "#1B998B"],
      ["質量補正で合格", 2, "#F0B429"],
      ["設計限界として記録", 3, "#D95D39"],
      ["保証範囲外", 0, "#9CA3AF"],
    ],
  },
  {
    no: 12,
    title: "寄生流れは、FD基準より小さい絶対スケールへ抑制",
    lead: "静止液滴と密度比sweepでは、CCD/BF構成とpressure-jump stackの安定性を別々の指標で確認した。",
    source: "Static droplet; density-ratio sweep; error budget",
    sourceFiles: ["paper/sections/13b_twophase_static.tex", "paper/sections/13d_density_ratio.tex", "paper/sections/13f_error_budget.tex"],
    visual: "evidenceCards",
    metrics: [
      ["静止液滴", "0.97%", "Laplace pressure error at N=128"],
      ["寄生流れ", "1.93e-2", "u_inf end at rho_r=1,N=32"],
      ["密度比", "rho_r <= 833", "no blow-up"],
      ["体積保存", "6.4e-16", "volume drift floor"],
    ],
  },
  {
    no: 13,
    title: "設計限界は、テストIDではなく物理的な誤差源として読む",
    lead: "時間精度は毛管圧力ジャンプとprojectionの界面帯に律速され、強変形CLSは固定格子の位相・細線解像限界に当たる。",
    source: "Error budget; conclusion",
    sourceFiles: ["paper/sections/13f_error_budget.tex", "paper/sections/15_conclusion.tex"],
    visual: "limitMap",
    limits: [
      ["二相時間精度", "slope 1.48", "毛管pressure-jump/projection界面帯が支配"],
      ["Zalesak形状", "centroid 4.911e-3", "slot under-resolution"],
      ["単一渦形状", "L1 2.248e-2", "folded filament の固定格子限界"],
    ],
  },
  {
    no: 14,
    title: "物理ベンチマークは、毛管波の符号検証から次のゲートへ進む",
    lead: "向き付き affine jump は短時間の復元力符号を通したが、気泡上昇とRayleigh--Taylorは未完了検証として分離する。",
    source: "Benchmark gates; conclusion",
    sourceFiles: ["paper/sections/14_benchmarks.tex", "paper/sections/15_conclusion.tex"],
    visual: "benchmarkRoadmap",
    stages: [
      ["毛管波", "A''符号・大きさを確認", "進行中"],
      ["気泡上昇", "yc(t), rise velocity, deformation", "未完了gate"],
      ["Rayleigh--Taylor", "線形成長率とmushroom形成", "未完了gate"],
    ],
  },
  {
    no: 15,
    title: "結論：高次化の本体は、演算子次数ではなく界面面契約の整合である",
    lead: "本研究は、CCD/FCCD/UCCD6を核に分相PPE+HFE+DC・Balanced-Force face subsystemを統合し、合格範囲と未解決範囲を検証軸として固定した。",
    source: "Conclusion",
    sourceFiles: ["paper/sections/15_conclusion.tex"],
    visual: "takeaways",
    takeaways: [
      "寄生流れの離散化起因成分を構造的に低減",
      "密度比 <= 833 まで pressure-jump stack の有界性を確認",
      "二相時間精度と強変形CLSの設計限界を次の研究ゲートとして明示",
    ],
  },
];

function slideModule(slide) {
  const { sourceFiles, ...slidePayload } = slide;
  return `import { makeSlide } from "./common.mjs";

const data = ${JSON.stringify(slidePayload, null, 2)};

export async function slide${String(slide.no).padStart(2, "0")}(presentation, ctx) {
  return makeSlide(presentation, ctx, data);
}
`;
}

const common = String.raw`
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const figDir = path.resolve(here, "../../../figures");

const C = {
  ink: "#17212B",
  muted: "#53606D",
  bg: "#F7F8F5",
  paper: "#FFFFFF",
  teal: "#1B998B",
  blue: "#234E70",
  red: "#D95D39",
  amber: "#F0B429",
  line: "#D6DBD2",
  paleTeal: "#E6F3F0",
  paleBlue: "#E8EEF5",
  paleAmber: "#FBF0D1",
};

function addText(ctx, slide, text, x, y, w, h, opts = {}) {
  return ctx.addText(slide, {
    text,
    left: x,
    top: y,
    width: w,
    height: h,
    fontSize: opts.size ?? 24,
    color: opts.color ?? C.ink,
    bold: opts.bold ?? false,
    typeface: opts.face ?? "Hiragino Sans",
    align: opts.align ?? "left",
    valign: opts.valign ?? "top",
    fill: opts.fill ?? "#00000000",
    line: opts.line ?? ctx.line("#00000000", 0),
    insets: opts.insets ?? { left: 0, right: 0, top: 0, bottom: 0 },
  });
}

function rect(ctx, slide, x, y, w, h, fill, line = C.line) {
  return ctx.addShape(slide, {
    left: x,
    top: y,
    width: w,
    height: h,
    fill,
    line: ctx.line(line, line === "#00000000" ? 0 : 1),
  });
}

function bar(ctx, slide, x, y, w, h, fill) {
  return ctx.addShape(slide, {
    left: x,
    top: y,
    width: w,
    height: h,
    fill,
    line: ctx.line("#00000000", 0),
  });
}

function footer(ctx, slide, source, no) {
  bar(ctx, slide, 56, 666, 1168, 1.5, C.line);
  addText(ctx, slide, "source: " + source, 56, 674, 980, 18, { size: 10, color: "#69737E" });
  addText(ctx, slide, String(no).padStart(2, "0"), 1180, 672, 44, 24, { size: 14, color: C.muted, align: "right", bold: true });
}

function frame(ctx, slide, data) {
  rect(ctx, slide, 0, 0, 1280, 720, C.bg, "#00000000");
  bar(ctx, slide, 0, 0, 1280, 8, C.blue);
  if (data.kind === "title") return;
  addText(ctx, slide, data.title, 56, 38, 790, 70, { size: 25, bold: true, color: C.ink });
  addText(ctx, slide, data.lead, 56, 112, 1010, 58, { size: 21, color: C.blue, bold: true });
}

function pill(ctx, slide, text, x, y, w, fill = C.paleBlue, color = C.blue) {
  rect(ctx, slide, x, y, w, 34, fill, "#00000000");
  addText(ctx, slide, text, x + 14, y + 7, w - 28, 18, { size: 12, bold: true, color });
}

function metric(ctx, slide, m, x, y, w, color = C.teal) {
  rect(ctx, slide, x, y, w, 112, C.paper, C.line);
  addText(ctx, slide, m[0], x + 16, y + 13, w - 32, 18, { size: 12, color: C.muted, bold: true });
  addText(ctx, slide, m[1], x + 16, y + 34, w - 32, 30, { size: 23, color, bold: true });
  addText(ctx, slide, m[2], x + 16, y + 68, w - 32, 25, { size: 12, color: C.ink });
}

function node(ctx, slide, title, body, x, y, w, h, fill = C.paper) {
  rect(ctx, slide, x, y, w, h, fill, C.line);
  addText(ctx, slide, title, x + 18, y + 14, w - 36, 24, { size: 15, bold: true, color: C.blue });
  addText(ctx, slide, body, x + 18, y + 45, w - 36, h - 55, { size: 13, color: C.ink });
}

async function image(ctx, slide, name, x, y, w, h) {
  await ctx.addImage(slide, {
    path: path.join(figDir, name),
    left: x,
    top: y,
    width: w,
    height: h,
    fit: "contain",
    alt: name,
  });
}

function problemMatrix(ctx, slide, data) {
  const x0 = 78, y0 = 220, gap = 22, w = 260, h = 130;
  data.bullets.forEach((b, i) => {
    const x = x0 + (i % 2) * (w + gap);
    const y = y0 + Math.floor(i / 2) * (h + gap);
    node(ctx, slide, b[0], b[1], x, y, w, h, i % 2 ? C.paleAmber : C.paper);
  });
  rect(ctx, slide, 720, 210, 420, 304, C.paleBlue, "#00000000");
  addText(ctx, slide, "界面が作る連鎖", 752, 240, 360, 28, { size: 18, bold: true, color: C.blue });
  ["不連続", "曲率誤差", "圧力不整合", "寄生流れ"].forEach((t, i) => {
    const y = 296 + i * 48;
    pill(ctx, slide, t, 762, y, 178, i === 3 ? "#FBE6DF" : C.paper, i === 3 ? C.red : C.blue);
    if (i < 3) bar(ctx, slide, 850, y + 38, 2, 12, C.muted);
  });
}

function threePillars(ctx, slide, data) {
  const xs = [86, 452, 818];
  data.pillars.forEach((p, i) => {
    rect(ctx, slide, xs[i], 234, 300, 230, i === 1 ? C.paleAmber : C.paper, C.line);
    addText(ctx, slide, "0" + (i + 1), xs[i] + 18, 252, 48, 34, { size: 24, bold: true, color: i === 1 ? C.amber : C.teal });
    addText(ctx, slide, p[0], xs[i] + 18, 308, 250, 32, { size: 22, bold: true, color: C.blue });
    addText(ctx, slide, p[1], xs[i] + 18, 356, 250, 60, { size: 16, color: C.ink });
  });
  addText(ctx, slide, "same face-space contract", 406, 510, 460, 30, { size: 22, bold: true, color: C.red, align: "center" });
}

function equationFlow(ctx, slide, data) {
  const x0 = 88, y = 275, w = 220;
  data.flow.forEach((f, i) => {
    node(ctx, slide, f[0], f[1], x0 + i * 270, y, w, 128, i % 2 ? C.paleBlue : C.paper);
    if (i < data.flow.length - 1) addText(ctx, slide, "→", x0 + i * 270 + w + 24, y + 45, 42, 35, { size: 28, color: C.teal, bold: true });
  });
  addText(ctx, slide, "CSFの体積力近似で閉じず、圧力ジャンプとしてprojectionへ入れる", 205, 468, 850, 32, { size: 19, color: C.blue, bold: true, align: "center" });
}

async function operatorStack(ctx, slide, data) {
  data.metrics.forEach((m, i) => metric(ctx, slide, m, 70 + i * 214, 210, 190, i === 3 ? C.red : C.teal));
  await image(ctx, slide, data.image, 196, 356, 720, 210);
  rect(ctx, slide, 936, 370, 244, 170, C.paleAmber, "#00000000");
  addText(ctx, slide, "設計原理", 960, 392, 180, 24, { size: 17, bold: true, color: C.blue });
  addText(ctx, slide, "面値・勾配・散逸を同じコンパクト演算子族から作り、圧力だけはDCCD適用を禁止する。", 960, 430, 190, 80, { size: 14, color: C.ink });
}

function stageRail(ctx, slide, data) {
  data.stages.forEach((s, i) => {
    const x = 70 + i * 185;
    rect(ctx, slide, x, 280, 142, 88, i % 2 ? C.paleBlue : C.paper, C.line);
    addText(ctx, slide, s, x + 12, 310, 118, 22, { size: 17, bold: true, color: C.blue, align: "center" });
    if (i < data.stages.length - 1) addText(ctx, slide, "→", x + 148, 306, 34, 24, { size: 23, color: C.teal, bold: true, align: "center" });
  });
  rect(ctx, slide, 326, 445, 628, 58, C.paleAmber, "#00000000");
  addText(ctx, slide, data.metricCallout, 350, 462, 580, 25, { size: 22, bold: true, color: C.red, align: "center" });
}

function pressureClosure(ctx, slide, data) {
  const labels = ["相内 Poisson", "HFE 延長", "DC k=3", "jump corrector"];
  labels.forEach((t, i) => {
    node(ctx, slide, t, ["phase-separated", "Hermite triplet", "residual contract", "G(p)-B(j)"][i], 92 + i * 270, 245, 210, 116, i === 2 ? C.paleAmber : C.paper);
    if (i < labels.length - 1) addText(ctx, slide, "→", 92 + i * 270 + 222, 284, 36, 28, { size: 24, color: C.teal, bold: true });
  });
  data.metrics.forEach((m, i) => metric(ctx, slide, m, 214 + i * 290, 430, 245, i === 1 ? C.amber : C.teal));
}

function faceContract(ctx, slide, data) {
  rect(ctx, slide, 455, 275, 370, 86, C.blue, "#00000000");
  addText(ctx, slide, data.center, 478, 300, 324, 28, { size: 22, bold: true, color: "#FFFFFF", align: "center" });
  const pos = [[100,250],[118,430],[505,455],[872,430],[895,250]];
  bar(ctx, slide, 345, 285, 110, 2, C.line);
  bar(ctx, slide, 825, 285, 70, 2, C.line);
  bar(ctx, slide, 360, 333, 95, 2, C.line);
  bar(ctx, slide, 825, 333, 58, 2, C.line);
  bar(ctx, slide, 638, 361, 2, 94, C.line);
  data.spokes.forEach((s, i) => {
    rect(ctx, slide, pos[i][0], pos[i][1], 245, 58, i === 1 ? C.paleAmber : C.paper, C.line);
    addText(ctx, slide, s, pos[i][0] + 12, pos[i][1] + 19, 221, 18, { size: 13, bold: true, color: C.blue, align: "center" });
  });
  addText(ctx, slide, "同じface locus / 同じ面係数 / 同じjump向き", 308, 562, 664, 28, { size: 20, bold: true, color: C.red, align: "center" });
}

function sevenStep(ctx, slide, data) {
  data.stages.forEach((s, i) => {
    const x = 66 + i * 164;
    rect(ctx, slide, x, 268, 124, 150, i < 4 ? C.paleBlue : C.paper, C.line);
    addText(ctx, slide, String(i + 1), x + 39, 284, 46, 30, { size: 24, bold: true, color: i < 4 ? C.teal : C.amber, align: "center" });
    addText(ctx, slide, s, x + 10, 340, 104, 38, { size: 16, bold: true, color: C.blue, align: "center" });
  });
  addText(ctx, slide, "界面幾何を閉じる", 120, 460, 500, 28, { size: 19, bold: true, color: C.teal, align: "center" });
  addText(ctx, slide, "NS projectionへ渡す", 660, 460, 500, 28, { size: 19, bold: true, color: C.amber, align: "center" });
}

function uTests(ctx, slide, data) {
  data.metrics.forEach((m, i) => metric(ctx, slide, m, 90 + i * 270, 232, 230, i === 3 ? C.red : C.teal));
  rect(ctx, slide, 134, 425, 1012, 78, C.paleBlue, "#00000000");
  addText(ctx, slide, "基礎演算 → 特殊離散 → 結合系 → 否定検証", 166, 452, 948, 28, { size: 25, bold: true, color: C.blue, align: "center" });
}

function verdictBars(ctx, slide, data) {
  addText(ctx, slide, "判定軸数（強変形CLSは質量保存軸と形状軸に分割）", 390, 202, 650, 20, { size: 13, color: C.muted, bold: true });
  const total = 13;
  data.bars.forEach((b, i) => {
    const y = 230 + i * 76;
    addText(ctx, slide, b[0], 120, y + 10, 260, 24, { size: 16, bold: true, color: C.blue });
    rect(ctx, slide, 390, y, 650, 42, "#EEF1ED", "#00000000");
    bar(ctx, slide, 390, y, 650 * b[1] / total, 42, b[2]);
    addText(ctx, slide, String(b[1]), 1060, y + 9, 50, 24, { size: 17, bold: true, color: C.ink, align: "right" });
  });
}

function evidenceCards(ctx, slide, data) {
  data.metrics.forEach((m, i) => metric(ctx, slide, m, 94 + (i % 2) * 540, 224 + Math.floor(i / 2) * 144, 440, i === 1 ? C.red : C.teal));
}

function limitMap(ctx, slide, data) {
  data.limits.forEach((m, i) => {
    rect(ctx, slide, 104, 228 + i * 116, 1072, 82, i === 0 ? C.paleAmber : C.paper, C.line);
    addText(ctx, slide, m[0], 126, 250 + i * 116, 142, 24, { size: 16, bold: true, color: C.red });
    addText(ctx, slide, m[1], 300, 247 + i * 116, 190, 30, { size: 22, bold: true, color: C.blue });
    addText(ctx, slide, m[2], 520, 251 + i * 116, 580, 24, { size: 16, color: C.ink });
  });
}

function benchmarkRoadmap(ctx, slide, data) {
  data.stages.forEach((m, i) => {
    rect(ctx, slide, 112 + i * 360, 250, 290, 210, i === 0 ? C.paleBlue : C.paper, C.line);
    addText(ctx, slide, m[0], 136 + i * 360, 276, 242, 28, { size: 22, bold: true, color: C.blue });
    addText(ctx, slide, m[1], 136 + i * 360, 328, 226, 56, { size: 15, color: C.ink });
    pill(ctx, slide, m[2], 136 + i * 360, 404, 190, i === 0 ? C.paleAmber : "#FBE6DF", i === 0 ? C.blue : C.red);
  });
}

function takeaways(ctx, slide, data) {
  data.takeaways.forEach((t, i) => {
    rect(ctx, slide, 142, 230 + i * 98, 996, 66, i === 1 ? C.paleBlue : C.paper, C.line);
    addText(ctx, slide, String(i + 1), 170, 246 + i * 98, 40, 28, { size: 22, bold: true, color: C.teal, align: "center" });
    addText(ctx, slide, t, 236, 248 + i * 98, 840, 24, { size: 19, bold: true, color: C.blue });
  });
}

export async function makeSlide(presentation, ctx, data) {
  const slide = presentation.slides.add();
  frame(ctx, slide, data);

  if (data.kind === "title") {
    addText(ctx, slide, data.kicker, 72, 86, 760, 28, { size: 18, color: C.teal, bold: true });
    addText(ctx, slide, data.title, 72, 168, 780, 112, { size: 34, bold: true, color: C.ink });
    addText(ctx, slide, data.lead, 76, 306, 760, 74, { size: 24, color: C.blue, bold: true });
    data.tags.forEach((t, i) => pill(ctx, slide, t, 80 + (i % 2) * 285, 440 + Math.floor(i / 2) * 52, 255, i % 2 ? C.paleAmber : C.paleBlue, i % 2 ? C.red : C.blue));
    rect(ctx, slide, 900, 95, 260, 510, C.paleBlue, "#00000000");
    addText(ctx, slide, "face-space\ncontract", 930, 230, 200, 104, { size: 28, bold: true, color: C.blue, align: "center" });
    footer(ctx, slide, data.source, data.no);
    return slide;
  }

  if (data.visual === "problemMatrix") problemMatrix(ctx, slide, data);
  if (data.visual === "threePillars") threePillars(ctx, slide, data);
  if (data.visual === "equationFlow") equationFlow(ctx, slide, data);
  if (data.visual === "operatorStack") await operatorStack(ctx, slide, data);
  if (data.visual === "stageRail") stageRail(ctx, slide, data);
  if (data.visual === "pressureClosure") pressureClosure(ctx, slide, data);
  if (data.visual === "faceContract") faceContract(ctx, slide, data);
  if (data.visual === "sevenStep") sevenStep(ctx, slide, data);
  if (data.visual === "uTests") uTests(ctx, slide, data);
  if (data.visual === "verdictBars") verdictBars(ctx, slide, data);
  if (data.visual === "evidenceCards") evidenceCards(ctx, slide, data);
  if (data.visual === "limitMap") limitMap(ctx, slide, data);
  if (data.visual === "benchmarkRoadmap") benchmarkRoadmap(ctx, slide, data);
  if (data.visual === "takeaways") takeaways(ctx, slide, data);
  footer(ctx, slide, data.source, data.no);
  return slide;
}
`;

function readme() {
  return `# Research Introduction Deck

- Task: fluid-mechanics conference style introduction based on the manuscript.
- Slide count: 15.
- Primary audience: researchers familiar with CFD / multiphase flow.
- Narrative spine: interface discontinuity problem -> face-space contract insight -> operator stack -> verification evidence -> limits and next gates.
- Build output: \`output/twophaseflow-research-introduction.pptx\`.

## Source Discipline

Each slide carries a human-readable source footer. Claims are limited to manuscript sections and paper figures under \`paper/sections\` and \`paper/figures\`; exact manuscript files are tracked in \`source_map.md\`.
`;
}

function sourceMap() {
  const rows = slides.map((s) => `| ${s.no} | ${s.title.replaceAll("|", "/")} | ${s.source} | ${(s.sourceFiles ?? []).join("; ")} |`);
  return `# Slide Source Map

| Slide | Lead claim | Audience source label | Manuscript source files |
|---:|---|---|---|
${rows.join("\n")}
`;
}

function speakerNotes() {
  return `# Speaker Notes

${slides.map((s) => `## ${s.no}. ${s.title}

${s.lead}

Source: ${s.source}
`).join("\n")}
`;
}

async function main() {
  await fs.mkdir(slidesDir, { recursive: true });
  await fs.mkdir(outputDir, { recursive: true });
  await fs.writeFile(path.join(slidesDir, "common.mjs"), common, "utf8");
  for (const s of slides) {
    await fs.writeFile(path.join(slidesDir, `slide-${String(s.no).padStart(2, "0")}.mjs`), slideModule(s), "utf8");
  }
  await fs.writeFile(path.join(here, "README.md"), readme(), "utf8");
  await fs.writeFile(path.join(here, "source_map.md"), sourceMap(), "utf8");
  await fs.writeFile(path.join(here, "speaker_notes.md"), speakerNotes(), "utf8");
  await fs.writeFile(path.join(here, "deck_manifest.json"), `${JSON.stringify({ slide_count: slides.length, slides }, null, 2)}\n`, "utf8");
}

main().catch((error) => {
  console.error(error.stack || error.message || String(error));
  process.exit(1);
});
