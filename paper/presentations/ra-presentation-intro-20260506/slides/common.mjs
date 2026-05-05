
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
  addText(ctx, slide, "判定軸数（V10は質量保存軸と形状軸に分割）", 390, 202, 650, 20, { size: 13, color: C.muted, bold: true });
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
    addText(ctx, slide, m[0], 130, 250 + i * 116, 96, 24, { size: 18, bold: true, color: C.red });
    addText(ctx, slide, m[1], 250, 247 + i * 116, 210, 30, { size: 22, bold: true, color: C.blue });
    addText(ctx, slide, m[2], 492, 251 + i * 116, 610, 24, { size: 16, color: C.ink });
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
