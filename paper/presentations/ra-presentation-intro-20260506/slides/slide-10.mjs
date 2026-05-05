import { makeSlide } from "./common.mjs";

const data = {
  "no": 10,
  "title": "単体検証は、各primitiveが単独で設計どおり働くことを確認した",
  "lead": "U1--U9は、基礎演算から否定検証までをトポロジカルに並べ、式・離散化・観測指標を一対一に結んだ。",
  "source": "paper/sections/12_component_verification.tex; 12h_summary.tex",
  "visual": "uTests",
  "metrics": [
    [
      "U1",
      "CCD h^6.0",
      "operator"
    ],
    [
      "U3",
      "GCL 2.13e-13",
      "nonuniform"
    ],
    [
      "U7",
      "0.61%",
      "Laplace error"
    ],
    [
      "U9",
      "禁止",
      "DCCD on pressure"
    ]
  ]
};

export async function slide10(presentation, ctx) {
  return makeSlide(presentation, ctx, data);
}
