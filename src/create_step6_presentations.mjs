import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const execFileAsync = promisify(execFile);

const {
  SKILL_DIR,
  WORKSPACE_DIR,
  TMP_DIR,
  OUTPUT_DIR,
  RUNTIME_PYTHON,
} = process.env;

for (const [key, value] of Object.entries({
  SKILL_DIR,
  WORKSPACE_DIR,
  TMP_DIR,
  OUTPUT_DIR,
  RUNTIME_PYTHON,
})) {
  if (!value || !path.isAbsolute(value)) {
    throw new Error(`${key} must be an absolute path`);
  }
}

const {
  resolvePresentationFont,
  applyPresentationChartFont,
  finalizePresentation,
} = await import(
  pathToFileURL(path.join(SKILL_DIR, "container_tools/artifact_tool_utils.mjs")).href
);

const FONT = resolvePresentationFont({ fontFamily: "Nimbus Sans" });
const MONO = "Nimbus Mono PS";
const W = 1280;
const H = 720;
const SLIDE_SIZE_EMU = "12192000,6858000";

const C = {
  ink: "#102A43",
  ink2: "#243B53",
  muted: "#627D98",
  pale: "#D9E2EC",
  paper: "#F7F5EF",
  white: "#FFFFFF",
  teal: "#0E7C7B",
  teal2: "#2A9D8F",
  tealPale: "#DCEFEB",
  coral: "#E76F51",
  orange: "#F4A261",
  gold: "#E9C46A",
  purple: "#765A9E",
  red: "#B23A48",
  green: "#287D5A",
  gray: "#95A4B3",
};

const PROJECT = WORKSPACE_DIR;
const ART = path.join(PROJECT, "artifacts");

await fs.mkdir(TMP_DIR, { recursive: true });
await fs.mkdir(OUTPUT_DIR, { recursive: true });

const limeMetadata = JSON.parse(
  await fs.readFile(path.join(ART, "step5_lime_local_metadata.json"), "utf8"),
);

function shape(slide, geometry, position, fill = "none", line = { fill: "none", width: 0 }, name) {
  return slide.shapes.add({ geometry, position, fill, line, ...(name ? { name } : {}) });
}

function box(slide, position, fill, lineFill = "none", lineWidth = 0, radius = 0, name) {
  const s = shape(
    slide,
    radius ? "roundRect" : "rect",
    position,
    fill,
    { style: "solid", fill: lineFill, width: lineWidth },
    name,
  );
  if (radius) s.borderRadius = radius;
  return s;
}

function rule(slide, x, y, width, color = C.pale, thickness = 2) {
  return shape(
    slide,
    "line",
    { left: x, top: y, width, height: 0 },
    "none",
    { style: "solid", fill: color, width: thickness },
  );
}

function vRule(slide, x, y, height, color = C.pale, thickness = 2) {
  return shape(
    slide,
    "line",
    { left: x, top: y, width: 0, height },
    "none",
    { style: "solid", fill: color, width: thickness },
  );
}

function textBox(slide, text, position, opts = {}) {
  const t = shape(slide, "textbox", position, opts.fill ?? "none", {
    style: "solid",
    fill: opts.lineFill ?? "none",
    width: opts.lineWidth ?? 0,
  }, opts.name);
  t.text = text;
  t.text.style = {
    typeface: opts.typeface ?? FONT,
    fontSize: opts.fontSize ?? 24,
    bold: opts.bold ?? false,
    italic: opts.italic ?? false,
    color: opts.color ?? C.ink,
    alignment: opts.align ?? "left",
    verticalAlignment: opts.valign ?? "top",
    autoFit: opts.autoFit ?? "none",
    wrap: opts.wrap ?? "square",
    insets: opts.insets ?? { top: 0, right: 0, bottom: 0, left: 0 },
  };
  return t;
}

function richTextBox(slide, paragraphs, position, opts = {}) {
  const t = shape(slide, "textbox", position, opts.fill ?? "none", {
    style: "solid",
    fill: opts.lineFill ?? "none",
    width: opts.lineWidth ?? 0,
  }, opts.name);
  t.text.set(paragraphs);
  t.text.style = {
    typeface: opts.typeface ?? FONT,
    fontSize: opts.fontSize ?? 24,
    color: opts.color ?? C.ink,
    alignment: opts.align ?? "left",
    verticalAlignment: opts.valign ?? "top",
    autoFit: opts.autoFit ?? "none",
    wrap: "square",
    insets: opts.insets ?? { top: 0, right: 0, bottom: 0, left: 0 },
  };
  return t;
}

function addSlideTitle(slide, title, subtitle, options = {}) {
  const dark = options.dark ?? false;
  const accent = options.accent ?? C.teal;
  const titleSize = title.length > 65 ? 31 : title.length > 58 ? 33 : title.length > 50 ? 36 : title.length > 45 ? 39 : 43;
  box(slide, { left: 54, top: 42, width: 8, height: subtitle ? 82 : 52 }, accent);
  textBox(slide, title, { left: 82, top: 35, width: 1128, height: 58 }, {
    fontSize: titleSize,
    bold: true,
    color: dark ? C.white : C.ink,
    autoFit: "none",
    wrap: "none",
  });
  if (subtitle) {
    textBox(slide, subtitle, { left: 84, top: 91, width: 1112, height: 32 }, {
      fontSize: 19,
      color: dark ? C.pale : C.muted,
    });
  }
}

function addFooter(slide, label, number, dark = false) {
  rule(slide, 54, 682, 1172, dark ? "#3A5268" : C.pale, 1);
  textBox(slide, `${label}  /  ${String(number).padStart(2, "0")}`, { left: 54, top: 689, width: 1172, height: 20 }, {
    fontSize: 13,
    color: dark ? "#B8C8D6" : C.muted,
    align: "right",
  });
}

function addSource(slide, source, dark = false) {
  textBox(slide, source, { left: 58, top: 654, width: 1120, height: 21 }, {
    fontSize: 13,
    color: dark ? "#B8C8D6" : C.muted,
    italic: true,
  });
}

function addNotes(slide, talkingPoints, sources = []) {
  const lines = [
    "Presenter notes",
    ...talkingPoints.map((s) => `• ${s}`),
  ];
  if (sources.length) {
    lines.push("", "Sources", ...sources.map((s) => `• ${s}`));
  }
  slide.speakerNotes.textFrame.setText(lines);
  slide.speakerNotes.setVisible(true);
}

function addBigMetric(slide, value, label, x, y, w, color = C.teal, dark = false) {
  textBox(slide, value, { left: x, top: y, width: w, height: 72 }, {
    fontSize: 56,
    bold: true,
    color: dark ? C.white : color,
  });
  textBox(slide, label, { left: x, top: y + 72, width: w, height: 54 }, {
    fontSize: 19,
    color: dark ? C.pale : C.ink2,
  });
}

function addLabelValue(slide, label, value, x, y, w, options = {}) {
  textBox(slide, label.toUpperCase(), { left: x, top: y, width: w, height: 22 }, {
    fontSize: 14,
    bold: true,
    color: options.labelColor ?? C.teal,
  });
  textBox(slide, value, { left: x, top: y + 26, width: w, height: options.height ?? 66 }, {
    fontSize: options.fontSize ?? 24,
    bold: options.bold ?? false,
    color: options.color ?? C.ink,
  });
}

async function addPng(slide, filename, position, alt, fit = "contain") {
  const bytes = new Uint8Array(await fs.readFile(path.join(ART, filename)));
  return slide.images.add({
    blob: bytes,
    contentType: "image/png",
    alt,
    fit,
    position,
  });
}

function basePresentation() {
  return Presentation.create({ slideSize: { width: W, height: H } });
}

function newSlide(presentation, dark = false) {
  const slide = presentation.slides.add();
  slide.background.fill = dark ? C.ink : C.paper;
  return slide;
}

function styleChart(chart) {
  applyPresentationChartFont(chart, { fontFamily: FONT });
  return chart;
}

function processBox(slide, text, x, y, w, h, color, darkText = true) {
  const s = box(slide, { left: x, top: y, width: w, height: h }, color, "none", 0, 10);
  s.text = text;
  s.text.style = {
    typeface: FONT,
    fontSize: 21,
    bold: true,
    color: darkText ? C.ink : C.white,
    alignment: "center",
    verticalAlignment: "middle",
    autoFit: "none",
    insets: { left: 12, right: 12, top: 8, bottom: 8 },
  };
  return s;
}

function connect(slide, from, to, color = C.muted) {
  return slide.shapes.connect(from, to, {
    kind: "straight",
    fromSide: "right",
    toSide: "left",
    line: { style: "solid", fill: color, width: 2 },
    tail: { type: "triangle", width: "sm", length: "sm" },
  });
}

function richLine(label, body, labelColor = C.teal, size = 22) {
  return [
    { run: label, textStyle: { bold: true, color: labelColor, fontSize: `${size}px`, typeface: FONT } },
    { run: body, textStyle: { color: C.ink2, fontSize: `${size}px`, typeface: FONT } },
  ];
}

async function buildTechnicalDeck() {
  const p = basePresentation();

  // 1. Cover
  {
    const s = newSlide(p, true);
    box(s, { left: 0, top: 0, width: 20, height: H }, C.teal2);
    textBox(s, "TECHNICAL PRESENTATION", { left: 82, top: 80, width: 500, height: 32 }, {
      fontSize: 18,
      bold: true,
      color: C.gold,
    });
    textBox(s, "DIAL-ALERT", { left: 78, top: 145, width: 850, height: 105 }, {
      fontSize: 76,
      bold: true,
      color: C.white,
    });
    textBox(s, "Early prediction of blood pressure defined\nintradialytic hypotension", { left: 82, top: 265, width: 900, height: 115 }, {
      fontSize: 34,
      color: C.pale,
    });
    rule(s, 82, 432, 360, C.teal2, 4);
    textBox(s, "Franklin Guillano\nCapstone Project, Step 6\nSeptember 2026", { left: 82, top: 465, width: 520, height: 120 }, {
      fontSize: 21,
      color: C.pale,
    });
    textBox(s, "Academic clinical decision support prototype", { left: 790, top: 585, width: 390, height: 48 }, {
      fontSize: 18,
      bold: true,
      color: C.orange,
      align: "right",
    });
    addFooter(s, "DIAL-ALERT technical presentation", 1, true);
    addNotes(s, [
      "Open with the prediction question and emphasize that this is a retrospective academic prototype.",
      "The presentation follows the machine-learning workflow from data construction to governance. Current verification covers installation and saved-model inference; raw-data retraining could not run after HTTP 403 from source acquisition.",
    ]);
  }

  // 2. Framing
  {
    const s = newSlide(p);
    addSlideTitle(s, "Prediction question and evaluation measures", "A supervised binary-classification task with a fixed prediction boundary");
    textBox(s, "Can information available near the start of haemodialysis identify sessions that later record systolic blood pressure below 90 mmHg?", { left: 82, top: 150, width: 1110, height: 98 }, {
      fontSize: 31,
      bold: true,
      color: C.ink,
    });
    rule(s, 82, 270, 1110, C.pale, 2);
    const cols = [82, 355, 628, 901];
    const labels = ["Population", "Prediction time", "Target", "Decision use"];
    const values = [
      "Eligible adult haemodialysis sessions",
      "Earliest valid active record within minutes 0 to 30",
      "Any later SBP below 90 mmHg",
      "Risk ranking for clinician review",
    ];
    for (let i = 0; i < 4; i++) {
      if (i) vRule(s, cols[i] - 26, 302, 108, C.pale, 2);
      addLabelValue(s, labels[i], values[i], cols[i], 304, 230, { fontSize: 21, height: 76 });
    }
    textBox(s, "Evaluation hierarchy", { left: 82, top: 450, width: 240, height: 30 }, {
      fontSize: 20,
      bold: true,
      color: C.teal,
    });
    const metrics = [
      ["Primary ranking", "Average precision"],
      ["Discrimination", "ROC AUC"],
      ["Probability quality", "Brier score"],
      ["Workflow utility", "Recall and PPV at alert capacity"],
    ];
    metrics.forEach(([a, b], i) => {
      const x = 82 + i * 278;
      textBox(s, a, { left: x, top: 500, width: 245, height: 22 }, { fontSize: 15, bold: true, color: C.muted });
      textBox(s, b, { left: x, top: 528, width: 245, height: 58 }, { fontSize: 22, bold: true, color: C.ink });
    });
    addSource(s, "Outcome and feature boundary: DIAL-ALERT Steps 2–4");
    addFooter(s, "DIAL-ALERT technical presentation", 2);
    addNotes(s, [
      "Average precision is the primary ranking metric because only about 8.5% of sessions meet the event definition.",
      "Business utility is assessed as event recall, positive predictive value, lift, and false alerts at a fixed review capacity.",
      "The target is a blood-pressure event, not a complete clinical diagnosis because symptoms and treatments are unavailable.",
    ], [
      "DIAL-ALERT Step 2 report and Step 4 model report.",
      "Saito T, Rehmsmeier M. PLoS ONE. 2015. https://doi.org/10.1371/journal.pone.0118432",
    ]);
  }

  // 3. Data and cohort
  {
    const s = newSlide(p);
    addSlideTitle(s, "HEMOBP cohort and eligibility", "Public longitudinal data link patient, session, and monitor records");
    const chart = s.charts.add("bar", {
      position: { left: 64, top: 152, width: 710, height: 430 },
      categories: [
        "Valid D1 patient-days",
        "Linked to monitor data",
        "Valid index record",
        "Final eligible sessions",
      ],
      series: [{
        name: "Records",
        values: [165849, 110790, 108781, 106758],
        valuesFormatCode: "#,##0",
        fill: C.teal,
        points: [
          { idx: 0, fill: C.purple },
          { idx: 1, fill: C.orange },
          { idx: 2, fill: C.ink2 },
          { idx: 3, fill: C.teal2 },
        ],
      }],
      barOptions: { direction: "bar", grouping: "clustered", gapWidth: 42 },
      hasLegend: false,
      chartFill: C.paper,
      plotAreaFill: C.paper,
      plotAreaLine: { fill: "none", width: 0 },
      xAxis: {
        visible: false,
        majorGridlines: null,
      },
      yAxis: {
        visible: true,
        tickLabelPosition: "none",
        textStyle: { fill: C.ink2, fontSize: 17 },
        line: { fill: "none", width: 0 },
        majorGridlines: null,
      },
      dataLabels: {
        showValue: true,
        position: "outEnd",
        textStyle: { fill: C.ink, fontSize: 15, bold: true },
      },
    });
    styleChart(chart);
    addBigMetric(s, "106,758", "eligible sessions", 842, 160, 330, C.teal);
    addBigMetric(s, "830", "unique patients", 842, 284, 330, C.purple);
    addBigMetric(s, "8.49%", "primary outcome prevalence", 842, 408, 330, C.coral);
    textBox(s, "4.37 million monitor states in the raw source", { left: 842, top: 544, width: 335, height: 42 }, {
      fontSize: 19,
      bold: true,
      color: C.ink2,
    });
    textBox(s, "Eligibility: baseline SBP ≥90, two later measurement minutes, last dialysis minute ≥120", { left: 76, top: 602, width: 1130, height: 38 }, { fontSize: 21, color: C.ink2 });
    addSource(s, "Minute 120 is elapsed dialysis time, not 120 minutes after the index reading");
    addFooter(s, "DIAL-ALERT technical presentation", 3);
    addNotes(s, [
      "The analytic unit is a session, while the effective independent sample is the patient.",
      "The public files contain 1,072 patient rows, compared with 1,075 reported in the source paper. All analyses use the observed release and disclose the difference.",
      "Cohort restrictions improve target validity but may introduce selection bias.",
    ], [
      "Lin CJ et al. Scientific Data. 2019. https://doi.org/10.1038/s41597-019-0319-8",
      "HEMOBP v3. https://doi.org/10.6084/m9.figshare.6260654.v3",
      "Project report: reports/Franklin_Guillano_DIAL_ALERT_Data_Collection_and_Understanding_Report.pdf",
    ]);
  }

  // 4. Leakage control and features
  {
    const s = newSlide(p);
    addSlideTitle(s, "Prediction features stop at the index time", "The outcome uses later measurements only, preventing temporal leakage");
    const a = processBox(s, "Earlier sessions\nand patient history", 76, 150, 280, 90, C.tealPale);
    const b = processBox(s, "Index record\nminutes 0 to 30", 500, 150, 280, 90, "#D9E8F3");
    const c = processBox(s, "Later BP records\ndefine the target", 924, 150, 280, 90, "#F8DDCF");
    connect(s, a, b);
    connect(s, b, c);
    textBox(s, "22 model inputs", { left: 76, top: 286, width: 250, height: 34 }, {
      fontSize: 24,
      bold: true,
      color: C.teal,
    });
    const families = [
      ["Haemodynamic state", "Baseline SBP, DBP, MAP, pulse pressure"],
      ["Fluid and treatment", "Fluid excess, UF rate, blood flow, dialysate settings"],
      ["Longitudinal history", "Prior nadir SBP, prior IDH rate, prior session event"],
      ["Patient context", "Age, recorded sex, diabetes, dialysis vintage"],
    ];
    families.forEach(([head, body], i) => {
      const x = 76 + (i % 2) * 560;
      const y = 338 + Math.floor(i / 2) * 118;
      box(s, { left: x, top: y + 4, width: 6, height: 78 }, i < 2 ? C.teal2 : C.purple);
      textBox(s, head, { left: x + 22, top: y, width: 500, height: 28 }, { fontSize: 21, bold: true, color: C.ink });
      textBox(s, body, { left: x + 22, top: y + 34, width: 500, height: 54 }, { fontSize: 18, color: C.ink2 });
    });
    rule(s, 76, 585, 1128, C.pale, 2);
    textBox(s, "Excluded from predictors: later blood pressure, outcome fields, post-dialysis weight, dialysis end time, identifiers, and audit variables", { left: 76, top: 600, width: 1128, height: 44 }, {
      fontSize: 19,
      bold: true,
      color: C.red,
    });
    addSource(s, "Source: preprocessing specification and feature engineering dictionary");
    addFooter(s, "DIAL-ALERT technical presentation", 4);
    addNotes(s, [
      "The earliest valid active-treatment record within 30 minutes forms the prediction index.",
      "Sessions already below 90 mmHg at the index time are excluded.",
      "Missing values enter model pipelines through median and most-frequent imputation. Unusual but plausible values remain after explicit range checks.",
    ], [
      "Project files: docs/preprocessing_specification.csv and docs/feature_engineering_dictionary.csv",
    ]);
  }

  // 5. Evaluation design
  {
    const s = newSlide(p);
    addSlideTitle(s, "Patient-level separation protects the evaluation", "No patient appears in more than one development partition");
    addBigMetric(s, "496", "training patients\n64,053 sessions", 90, 150, 290, C.teal);
    vRule(s, 418, 160, 126, C.pale, 2);
    addBigMetric(s, "164", "validation patients\n21,351 sessions", 455, 150, 290, C.purple);
    vRule(s, 783, 160, 126, C.pale, 2);
    addBigMetric(s, "170", "test patients\n21,354 sessions", 820, 150, 290, C.coral);
    textBox(s, "0 patient overlap", { left: 90, top: 306, width: 1020, height: 44 }, {
      fontSize: 26,
      bold: true,
      color: C.green,
      align: "center",
    });
    rule(s, 90, 372, 1020, C.pale, 2);
    const steps = [
      ["1", "Grouped 3-fold CV", "Tune candidate pipelines on training patients"],
      ["2", "Validation decisions", "Choose calibration and F2 threshold"],
      ["3", "Locked test", "Evaluate once after all choices"],
      ["4", "Patient bootstrap", "500 resamples for uncertainty"],
    ];
    steps.forEach(([n, head, body], i) => {
      const x = 76 + i * 300;
      textBox(s, n, { left: x, top: 412, width: 46, height: 46 }, {
        fontSize: 26,
        bold: true,
        color: C.white,
        align: "center",
        valign: "middle",
        fill: i === 2 ? C.coral : C.teal,
        insets: { left: 0, right: 0, top: 5, bottom: 0 },
      });
      textBox(s, head, { left: x + 62, top: 408, width: 215, height: 30 }, { fontSize: 21, bold: true, color: C.ink });
      textBox(s, body, { left: x + 62, top: 444, width: 215, height: 66 }, { fontSize: 17, color: C.ink2 });
    });
    textBox(s, "Why it matters", { left: 76, top: 556, width: 200, height: 28 }, { fontSize: 19, bold: true, color: C.teal });
    textBox(s, "Repeated sessions from the same patient can make random session splits look more accurate than true generalisation to new patients.", { left: 76, top: 588, width: 1100, height: 52 }, { fontSize: 20, color: C.ink2 });
    addSource(s, "Source: split_summary.csv, split_assignments.csv.gz, model_config.json");
    addFooter(s, "DIAL-ALERT technical presentation", 5);
    addNotes(s, [
      "Patient-disjoint splitting is the central protection against repeated-measures leakage.",
      "The validation set handles calibration and threshold choice. The test set remains untouched until the final evaluation.",
      "Bootstrap resampling occurs at the patient level to preserve within-patient dependence.",
    ]);
  }

  // 6. Model comparison
  {
    const s = newSlide(p);
    addSlideTitle(s, "Why random forest was selected", "Selection rule: highest grouped-CV average precision, then lower validation Brier score within 0.01");
    const chart = s.charts.add("bar", {
      position: { left: 58, top: 148, width: 760, height: 455 },
      categories: [
        "Hist. gradient boosting",
        "Random forest",
        "Logistic regression",
        "PCA logistic regression",
        "L1 feature selection",
        "Decision tree",
        "Prevalence baseline",
      ],
      series: [{
        name: "Grouped-CV AP",
        values: [0.445885, 0.440447, 0.418580, 0.409788, 0.403691, 0.388189, 0.084930],
        valuesFormatCode: "0.000",
        fill: C.ink2,
        points: [
          { idx: 0, fill: C.purple },
          { idx: 1, fill: C.teal2 },
          { idx: 6, fill: C.gray },
        ],
      }],
      barOptions: { direction: "bar", grouping: "clustered", gapWidth: 32 },
      hasLegend: false,
      chartFill: C.paper,
      plotAreaFill: C.paper,
      plotAreaLine: { fill: "none", width: 0 },
      xAxis: {
        visible: true,
        min: 0,
        max: 0.5,
        majorUnit: 0.1,
        numberFormatCode: "0.0",
        textStyle: { fill: C.muted, fontSize: 15 },
        line: { fill: C.pale, width: 1 },
        majorGridlines: { style: "solid", fill: C.pale, width: 1 },
      },
      yAxis: {
        visible: true,
        textStyle: { fill: C.ink2, fontSize: 16 },
        line: { fill: "none", width: 0 },
        majorGridlines: null,
      },
      dataLabels: {
        showValue: true,
        position: "outEnd",
        textStyle: { fill: C.ink, fontSize: 14, bold: true },
      },
    });
    styleChart(chart);
    textBox(s, "Why random forest", { left: 870, top: 162, width: 320, height: 34 }, { fontSize: 24, bold: true, color: C.teal });
    addLabelValue(s, "CV average precision", "0.440", 870, 218, 300, { fontSize: 36, bold: true, color: C.teal, height: 48 });
    addLabelValue(s, "Validation Brier score", "0.058", 870, 316, 300, { fontSize: 36, bold: true, color: C.purple, height: 48 });
    textBox(s, "Histogram boosting ranked slightly higher on CV AP (0.446), but its validation Brier score was 0.134. The difference in AP was within the predefined 0.01 tolerance.", { left: 870, top: 424, width: 320, height: 142 }, {
      fontSize: 19,
      color: C.ink2,
    });
    textBox(s, "Selected model: 250-tree random forest, minimum leaf size 15", { left: 870, top: 578, width: 320, height: 54 }, {
      fontSize: 18,
      bold: true,
      color: C.ink,
    });
    addSource(s, "Source: model_comparison.csv and final_test_metrics.json");
    addFooter(s, "DIAL-ALERT technical presentation", 6);
    textBox(s, "PCA and prevalence baseline are comparison benchmarks outside the final selection pool", { left: 76, top: 608, width: 1110, height: 32 }, { fontSize: 18, color: C.muted });
    addNotes(s, [
      "Seven configurations include linear, tree, boosted, PCA, embedded-selection, and prevalence baselines.",
      "The locked selection rule considers ranking first and probability quality when models are practically tied.",
      "Deep learning was not justified for a compact tabular snapshot with only 830 independent patient groups.",
    ], [
      "Breiman L. Random Forests. Machine Learning. 2001. https://doi.org/10.1023/A:1010933404324",
      "Project artifact: artifacts/model_comparison.csv",
    ]);
  }

  // 7. Test performance
  {
    const s = newSlide(p);
    addSlideTitle(s, "Test performance and uncertainty", "Locked assessment on 21,354 sessions from 170 previously unseen patients");
    await addPng(s, "test_performance_intervals.png", { left: 58, top: 145, width: 760, height: 470 }, "Patient-cluster confidence intervals for final test metrics");
    addBigMetric(s, "0.852", "ROC AUC", 858, 150, 300, C.teal);
    addBigMetric(s, "0.395", "average precision", 858, 268, 300, C.purple);
    addBigMetric(s, "0.062", "Brier score", 858, 386, 300, C.coral);
    rule(s, 858, 520, 300, C.pale, 2);
    textBox(s, "Operating threshold 0.143", { left: 858, top: 538, width: 300, height: 28 }, { fontSize: 19, bold: true, color: C.ink });
    textBox(s, "Sensitivity 66.1%\nSpecificity 86.1%\nPrecision 30.6%", { left: 858, top: 574, width: 300, height: 76 }, { fontSize: 19, color: C.ink2 });
    addSource(s, "Intervals: 500 patient-cluster bootstrap resamples");
    addFooter(s, "DIAL-ALERT technical presentation", 7);
    addNotes(s, [
      "At the validation-selected threshold, the test set contains 1,199 true positives, 615 false negatives, 2,719 false positives, and 16,821 true negatives.",
      "Average precision must be read against the 8.49% prevalence baseline.",
      "Wide intervals reflect only 170 test patients despite the large number of sessions.",
    ], [
      "Project artifacts: artifacts/final_test_metrics.json and artifacts/test_metric_confidence_intervals.csv",
    ]);
  }

  // 8. Capacity
  {
    const s = newSlide(p);
    addSlideTitle(s, "Review capacity and event detection", "Ranking utility shown across the proportion of sessions selected for review");
    const capacities = ["5", "10", "15", "20", "25", "30", "35", "40", "45", "50"];
    const chart = s.charts.add("line", {
      position: { left: 58, top: 155, width: 790, height: 430 },
      categories: capacities,
      series: [
        {
          name: "Observed events captured",
          values: [0.2993, 0.4807, 0.6064, 0.6913, 0.7580, 0.8026, 0.8396, 0.8721, 0.8969, 0.9173],
          valuesFormatCode: "0%",
          line: { style: "solid", fill: C.teal, width: 4 },
          marker: { symbol: "circle", size: 8 },
        },
        {
          name: "Positive predictive value",
          values: [0.5084, 0.4082, 0.3433, 0.2936, 0.2575, 0.2273, 0.2038, 0.1852, 0.1693, 0.1558],
          valuesFormatCode: "0%",
          line: { style: "solid", fill: C.coral, width: 4 },
          marker: { symbol: "square", size: 8 },
        },
      ],
      hasLegend: true,
      legend: { position: "bottom", overlay: false, textStyle: { fill: C.ink2, fontSize: 15 } },
      chartFill: C.paper,
      plotAreaFill: C.paper,
      plotAreaLine: { fill: "none", width: 0 },
      xAxis: {
        visible: true,
        title: "Sessions selected for review (%)",
        textStyle: { fill: C.muted, fontSize: 14 },
        line: { fill: C.pale, width: 1 },
        majorGridlines: null,
      },
      yAxis: {
        visible: true,
        min: 0,
        max: 1,
        majorUnit: 0.2,
        numberFormatCode: "0%",
        textStyle: { fill: C.muted, fontSize: 14 },
        line: { fill: C.pale, width: 1 },
        majorGridlines: { style: "solid", fill: C.pale, width: 1 },
      },
    });
    styleChart(chart);
    textBox(s, "20% review capacity", { left: 900, top: 164, width: 292, height: 34 }, { fontSize: 25, bold: true, color: C.teal });
    addLabelValue(s, "Event recall", "69.1%", 900, 228, 270, { fontSize: 37, bold: true, color: C.teal, height: 46 });
    addLabelValue(s, "Positive predictive value", "29.4%", 900, 332, 270, { fontSize: 37, bold: true, color: C.coral, height: 46 });
    addLabelValue(s, "Lift over prevalence", "3.46×", 900, 436, 270, { fontSize: 37, bold: true, color: C.purple, height: 46 });
    textBox(s, "14.1 false alerts per 100 sessions", { left: 900, top: 548, width: 280, height: 56 }, { fontSize: 20, bold: true, color: C.red });
    addSource(s, "Separate fixed threshold 0.143: 18.35% flagged, 66.1% sensitivity, 30.6% precision");
    addFooter(s, "DIAL-ALERT technical presentation", 8);
    addNotes(s, [
      "The highest-risk 20% analysis ranks a retrospective batch. A local batch window and tie rule must be defined before live use. At the separate fixed threshold 0.143, 18.35% of test sessions are flagged, sensitivity is 66.1%, precision 30.6%, and false alerts 12.73 per 100 sessions.",
      "At 20% capacity the model identifies about 69% of observed events, but most reviewed sessions do not have the event.",
      "No clinical benefit follows automatically from ranking performance. A prospective intervention study is required.",
    ], [
      "Project artifact: artifacts/capacity_metrics.csv",
    ]);
  }

  // 9. Explainability
  {
    const s = newSlide(p);
    addSlideTitle(s, "Model explanations and their limits", "Aggregate SHAP with a separately declared synthetic local scenario");
    await addPng(s, "step5_shap_summary.png", { left: 54, top: 142, width: 780, height: 485 }, "Aggregate approximate SHAP importance for the DIAL-ALERT random forest");
    textBox(s, "Consistent signals", { left: 870, top: 160, width: 300, height: 30 }, { fontSize: 24, bold: true, color: C.teal });
    richTextBox(s, [
      richLine("Lower prior nadir SBP: ", "higher predicted risk"),
      richLine("Higher prior IDH rate: ", "higher predicted risk"),
      richLine("Greater fluid excess: ", "higher predicted risk"),
      richLine("Lower baseline pressure: ", "higher predicted risk"),
    ], { left: 870, top: 212, width: 330, height: 210 }, { fontSize: 20 });
    rule(s, 870, 442, 300, C.pale, 2);
    textBox(s, "Explanation limits", { left: 870, top: 462, width: 300, height: 30 }, { fontSize: 22, bold: true, color: C.coral });
    textBox(s, `Monte Carlo SHAP is approximate. For the synthetic local scenario, the LIME-style surrogate had weighted R² ${Number(limeMetadata.weighted_r2).toFixed(3)} and absolute probability error ${Number(limeMetadata.absolute_prediction_error).toFixed(3)}. Neither method establishes causality or a treatment target.`, { left: 870, top: 505, width: 320, height: 128 }, { fontSize: 18, color: C.ink2 });
    addSource(s, "Source: Step 5 explainability audit");
    addFooter(s, "DIAL-ALERT technical presentation", 9);
    addNotes(s, [
      "Permutation importance, aggregate SHAP, and synthetic-profile dependence curves agree that prior instability and fluid status dominate the model.",
      "The explanation describes the fitted model, not a causal mechanism.",
      "The local SHAP and LIME example is a manually constructed synthetic scenario, not an observed patient session.",
      "Local LIME output requires a fidelity warning because the surrogate only moderately approximates the random forest near that synthetic scenario.",
    ], [
      "Lundberg SM, Lee SI. NeurIPS 2017. https://papers.neurips.cc/paper/7062-a-unified-approach-to-interpreting-model-predictions",
      "Ribeiro MT et al. KDD 2016. https://doi.org/10.1145/2939672.2939778",
      "Project artifacts: artifacts/step5_shap_summary.png, artifacts/step5_shap_local_synthetic.csv, and artifacts/step5_lime_local_metadata.json",
    ]);
  }

  // 10. Fairness
  {
    const s = newSlide(p);
    addSlideTitle(s, "Fairness mitigation results", "Held-out fairness metrics must be reviewed with clinical utility and uncertainty");
    await addPng(s, "step5_mitigation_tradeoff.png", { left: 54, top: 142, width: 1170, height: 360 }, "Comparison of fairness mitigation strategies and average precision");
    const xs = [76, 450, 824];
    const heads = ["Reweighting retained", "Threshold strategy rejected", "Unmeasured fairness"];
    const bodies = [
      "Sex disparate-impact ratio 0.705 to 0.764. Equalized-odds gap 0.076 to 0.058. AP 0.395 to 0.394.",
      "Sex-specific thresholds worsened the equalized-odds gap to 0.139 and lowered precision to 27.8%.",
      "Race, ethnicity, socioeconomic status, and gender identity are unavailable. Age-group DI ratio is 0.541.",
    ];
    heads.forEach((head, i) => {
      textBox(s, head, { left: xs[i], top: 530, width: 330, height: 30 }, { fontSize: 20, bold: true, color: i === 0 ? C.green : i === 1 ? C.red : C.purple });
      textBox(s, bodies[i], { left: xs[i], top: 568, width: 330, height: 76 }, { fontSize: 17, color: C.ink2 });
    });
    addSource(s, "0.80 disparate-impact ratio is a descriptive screen, not a fairness certificate");
    addFooter(s, "DIAL-ALERT technical presentation", 10);
    addNotes(s, [
      "The recorded-sex mitigation improved two summary gaps with essentially unchanged average precision.",
      "The improvement does not eliminate disparity and may not transfer to another centre.",
      "Patient-equal weighting changes some estimates, intersections are unstable, and bootstrap intervals are wide.",
      "Sex-specific thresholds use a protected attribute at inference and performed worse on test patients, so they are rejected.",
    ], [
      "Hardt M, Price E, Srebro N. NeurIPS 2016. https://arxiv.org/abs/1610.02413",
      "Project artifacts: artifacts/step5_mitigation_comparison.csv and artifacts/step5_disparities.csv",
    ]);
  }

  // 11. Reproducibility
  {
    const s = newSlide(p);
    addSlideTitle(s, "Reproduction instructions and verification status", "Saved-model inference verified; full training reproduction blocked at source download");
    textBox(s, "Project structure", { left: 76, top: 154, width: 400, height: 34 }, { fontSize: 25, bold: true, color: C.teal });
    const treeLines = [
      ["data/raw", "Download locally; excluded from Git"],
      ["data/processed", "Leakage-controlled session table"],
      ["src", "Build, train, evaluate, audit, and report scripts"],
      ["configs", "Seeds, features, CV, bootstrap, capacity"],
      ["models", "Selected predictor; candidates regenerate"],
      ["artifacts", "Aggregate metrics; assignments regenerate"],
      ["reports", "Step 2 through Step 6 deliverables"],
    ];
    treeLines.forEach(([folder, desc], i) => {
      const y = 210 + i * 54;
      textBox(s, folder, { left: 76, top: y, width: 235, height: 30 }, { fontSize: 20, bold: true, color: C.purple, typeface: MONO });
      textBox(s, desc, { left: 320, top: y, width: 450, height: 34 }, { fontSize: 18, color: C.ink2 });
      rule(s, 76, y + 40, 694, C.pale, 1);
    });
    vRule(s, 812, 160, 430, C.pale, 2);
    textBox(s, "Reproduction sequence", { left: 850, top: 154, width: 340, height: 34 }, { fontSize: 25, bold: true, color: C.teal });
    const commands = [
      "build_session_dataset.py",
      "train_evaluate.py",
      "generate_eda.py",
      "audit_bias_fairness.py",
    ];
    commands.forEach((cmd, i) => {
      textBox(s, `${i + 1}`, { left: 850, top: 218 + i * 76, width: 38, height: 38 }, {
        fontSize: 21,
        bold: true,
        color: C.white,
        fill: C.teal,
        align: "center",
        valign: "middle",
        insets: { left: 0, right: 0, top: 5, bottom: 0 },
      });
      textBox(s, `python src/${cmd}`, { left: 910, top: 220 + i * 76, width: 300, height: 48 }, { fontSize: 17, color: C.ink, typeface: MONO });
    });
    textBox(s, "Model manifest records package versions, file hashes, random seeds, feature order, and threshold metadata.", { left: 850, top: 542, width: 350, height: 76 }, { fontSize: 19, bold: true, color: C.ink2 });
    addSource(s, "Source: project repository and Step 4–5 manifests");
    addFooter(s, "DIAL-ALERT technical presentation", 11);
    addNotes(s, [
      "This slide connects the analytic results to the rubric requirement for saved configurations and artifacts.",
      "Patient-level assignments regenerate locally. The shipped model, threshold, configuration and aggregate metrics support auditability. Source download returned HTTP 403 in the fresh-environment check; training reproduction remains incomplete.",
      "The public source data remain subject to their original license and citation requirements. The manifest separates shipped files from historical generated candidates. Presentation rebuilding requires the external authoring runtime; see docs/reproduction_guide.md.",
    ]);
  }

  // 12. Conclusion
  {
    const s = newSlide(p, true);
    addSlideTitle(s, "Internal validation supports a governed next study", "The evidence is promising for risk ranking and insufficient for clinical deployment", { dark: true, accent: C.gold });
    textBox(s, "Evidence supports", { left: 76, top: 158, width: 480, height: 38 }, { fontSize: 28, bold: true, color: C.teal2 });
    richTextBox(s, [
      richLine("Risk ranking: ", "ROC AUC 0.852 and AP 0.395", C.teal2, 22),
      richLine("Capacity planning: ", "69.1% event recall at 20% review", C.teal2, 22),
      richLine("Interpretability: ", "clinically coherent history and fluid signals", C.teal2, 22),
      richLine("Mitigation candidate: ", "sex-outcome reweighting", C.teal2, 22),
    ], { left: 76, top: 220, width: 510, height: 230 }, { color: C.white, fontSize: 22 });
    vRule(s, 634, 160, 320, "#3A5268", 2);
    textBox(s, "Evidence does not support", { left: 680, top: 158, width: 500, height: 38 }, { fontSize: 28, bold: true, color: C.orange });
    const noItems = [
      "Clinical benefit or cost savings",
      "Autonomous diagnosis or treatment",
      "Fairness across unavailable attributes",
      "Transfer to another centre or future protocol",
    ];
    noItems.forEach((item, i) => {
      box(s, { left: 680, top: 224 + i * 55, width: 6, height: 32 }, C.coral);
      textBox(s, item, { left: 704, top: 219 + i * 55, width: 470, height: 40 }, { fontSize: 21, color: C.white });
    });
    rule(s, 76, 506, 1104, "#3A5268", 2);
    textBox(s, "Next validation gates", { left: 76, top: 530, width: 260, height: 32 }, { fontSize: 23, bold: true, color: C.gold });
    textBox(s, "External temporal and geographic validation, prospective silent mode, human factors, subgroup calibration, monitoring, and rollback", { left: 76, top: 575, width: 1100, height: 62 }, { fontSize: 21, bold: true, color: C.pale });
    addFooter(s, "DIAL-ALERT technical presentation", 12, true);
    addNotes(s, [
      "End with a precise claim: the project completes the machine-learning lifecycle and justifies a governed validation study.",
      "It does not show that an alert changes treatment or improves outcomes.",
      "The next scientific question is transportability and prospective workflow safety.",
    ], [
      "WHO. Ethics and governance of AI for health. 2021. https://www.who.int/publications/i/item/9789240029200",
      "TRIPOD+AI. BMJ. 2024. https://doi.org/10.1136/bmj-2023-078378",
    ]);
  }

  return p;
}

async function buildBusinessDeck() {
  const p = basePresentation();

  // 1. Cover
  {
    const s = newSlide(p, true);
    box(s, { left: 0, top: 0, width: 20, height: H }, C.coral);
    textBox(s, "EXECUTIVE PRESENTATION", { left: 82, top: 80, width: 500, height: 32 }, {
      fontSize: 18,
      bold: true,
      color: C.gold,
    });
    textBox(s, "DIAL-ALERT", { left: 78, top: 145, width: 850, height: 105 }, {
      fontSize: 76,
      bold: true,
      color: C.white,
    });
    textBox(s, "A governed path to earlier review of\nintradialytic hypotension risk", { left: 82, top: 265, width: 950, height: 115 }, {
      fontSize: 34,
      color: C.pale,
    });
    rule(s, 82, 432, 360, C.coral, 4);
    textBox(s, "Franklin Guillano\nCapstone Project, Step 6\nSeptember 2026", { left: 82, top: 465, width: 520, height: 120 }, {
      fontSize: 21,
      color: C.pale,
    });
    textBox(s, "Decision brief: value, risk, and pilot strategy", { left: 700, top: 585, width: 480, height: 48 }, {
      fontSize: 18,
      bold: true,
      color: C.orange,
      align: "right",
    });
    addFooter(s, "DIAL-ALERT executive presentation", 1, true);
    addNotes(s, [
      "Frame DIAL-ALERT as a decision support research program, not a finished clinical product.",
      "The executive question is whether the evidence justifies a controlled local validation and pilot.",
    ]);
  }

  // 2. Executive decision
  {
    const s = newSlide(p, true);
    addSlideTitle(s, "Potential value and remaining evidence", "Internal test performance supports a governed pilot decision", { dark: true, accent: C.gold });
    textBox(s, "69.1%", { left: 72, top: 155, width: 430, height: 120 }, { fontSize: 92, bold: true, color: C.white });
    textBox(s, "of observed events appear in the highest-risk 20% of sessions", { left: 76, top: 278, width: 500, height: 90 }, { fontSize: 29, color: C.pale });
    vRule(s, 638, 158, 230, "#3A5268", 2);
    addBigMetric(s, "29.4%", "positive predictive value\nat 20% review capacity", 700, 160, 420, C.teal2, true);
    addBigMetric(s, "3.46×", "lift over event prevalence", 700, 300, 420, C.purple, true);
    rule(s, 76, 440, 1100, "#3A5268", 2);
    textBox(s, "Recommendation", { left: 76, top: 470, width: 260, height: 34 }, { fontSize: 24, bold: true, color: C.gold });
    textBox(s, "Approve external validation and a prospective silent mode study. Do not use DIAL-ALERT to guide treatment until clinical benefit, workflow safety, and subgroup performance are demonstrated locally.", { left: 76, top: 520, width: 1100, height: 108 }, { fontSize: 27, bold: true, color: C.white });
    addFooter(s, "DIAL-ALERT executive presentation", 2, true);
    addNotes(s, [
      "The 69.1% figure describes retrospective ranking at a fixed review capacity.",
      "It does not mean that 69.1% of events would be prevented.",
      "The requested decision is funding for evidence generation, not clinical rollout.",
    ], [
      "Project artifact: artifacts/capacity_metrics.csv",
    ]);
  }

  // 3. Workflow
  {
    const s = newSlide(p);
    addSlideTitle(s, "Proposed workflow for clinician review", "The clinician retains responsibility for assessment and action");
    const steps = [
      ["1", "Session begins", "Index data available within the first 30 minutes", C.tealPale],
      ["2", "Risk score", "Model estimates later SBP below 90 mmHg", "#D9E8F3"],
      ["3", "Clinical review", "Staff confirm context, symptoms, and current treatment", "#F7E5C4"],
      ["4", "Usual protocol", "Any action follows approved clinical policy", "#F8DDCF"],
    ];
    const nodes = [];
    steps.forEach(([n, head, body, fill], i) => {
      const x = 58 + i * 305;
      const node = box(s, { left: x, top: 190, width: 255, height: 250 }, fill, "none", 0, 12);
      textBox(s, n, { left: x + 20, top: 210, width: 48, height: 48 }, {
        fontSize: 26,
        bold: true,
        color: C.white,
        fill: i < 2 ? C.teal : i === 2 ? C.gold : C.coral,
        align: "center",
        valign: "middle",
        insets: { left: 0, right: 0, top: 5, bottom: 0 },
      });
      textBox(s, head, { left: x + 20, top: 280, width: 215, height: 36 }, { fontSize: 23, bold: true, color: C.ink });
      textBox(s, body, { left: x + 20, top: 334, width: 215, height: 92 }, { fontSize: 19, color: C.ink2 });
      nodes.push(node);
    });
    for (let i = 0; i < nodes.length - 1; i++) connect(s, nodes[i], nodes[i + 1], C.muted);
    rule(s, 76, 500, 1128, C.pale, 2);
    textBox(s, "Human controls", { left: 76, top: 528, width: 220, height: 30 }, { fontSize: 22, bold: true, color: C.teal });
    textBox(s, "Decision support label, clinician override, reason for override, no autonomous prescription, and an audit trail", { left: 76, top: 574, width: 1128, height: 48 }, { fontSize: 22, bold: true, color: C.ink2 });
    addSource(s, "Proposed workflow for evaluation, not an approved clinical process");
    addFooter(s, "DIAL-ALERT executive presentation", 3);
    addNotes(s, [
      "DIAL-ALERT would create a review cue, not a diagnosis or treatment order.",
      "The pilot must measure how clinicians interpret, override, and act on the score.",
      "Integration should use the minimum necessary data and preserve an auditable human decision.",
    ]);
  }

  // 4. Evidence base
  {
    const s = newSlide(p);
    addSlideTitle(s, "Evidence from one retrospective setting", "Public HEMOBP data provide strong longitudinal depth from one retrospective source");
    await addPng(s, "cohort_flow.png", { left: 54, top: 146, width: 690, height: 465 }, "DIAL-ALERT cohort construction");
    addBigMetric(s, "106,758", "eligible sessions", 806, 150, 330, C.teal);
    addBigMetric(s, "830", "unique patients", 806, 266, 330, C.purple);
    addBigMetric(s, "8.49%", "event prevalence", 806, 382, 330, C.coral);
    rule(s, 806, 510, 330, C.pale, 2);
    textBox(s, "Test set", { left: 806, top: 530, width: 120, height: 28 }, { fontSize: 18, bold: true, color: C.teal });
    textBox(s, "21,354 sessions from 170 patients with zero overlap with development patients", { left: 806, top: 566, width: 350, height: 76 }, { fontSize: 19, bold: true, color: C.ink2 });
    addSource(s, "Source: HEMOBP v3 and DIAL-ALERT cohort audit");
    addFooter(s, "DIAL-ALERT executive presentation", 4);
    addNotes(s, [
      "The dataset is large enough to compare several tabular models and examine operational ranking.",
      "Generalisation remains uncertain because the data come from a single public retrospective source and only 170 patients form the test partition.",
      "The outcome is a blood-pressure threshold and does not include symptoms, interventions, or clinician assessments.",
    ], [
      "Lin CJ et al. Scientific Data. 2019. https://doi.org/10.1038/s41597-019-0319-8",
      "Project report: reports/Franklin_Guillano_DIAL_ALERT_Data_Collection_and_Understanding_Report.pdf",
    ]);
  }

  // 5. Operational impact per 100 sessions
  {
    const s = newSlide(p);
    addSlideTitle(s, "Workload at 20% review capacity", "Expected counts per 100 sessions in the internal test population");
    const capture = s.charts.add("doughnut", {
      position: { left: 65, top: 170, width: 500, height: 350 },
      categories: ["Captured in alert group", "Outside alert group"],
      series: [{
        name: "Observed events",
        values: [5.87, 2.62],
        valuesFormatCode: "0.0",
        points: [{ idx: 0, fill: C.teal2 }, { idx: 1, fill: C.pale }],
      }],
      doughnutOptions: { holeSize: 62 },
      hasLegend: true,
      legend: { position: "bottom", overlay: false, textStyle: { fill: C.ink2, fontSize: 16 } },
      dataLabels: { showPercent: true, position: "outEnd", textStyle: { fill: C.ink, fontSize: 17, bold: true } },
      chartFill: C.paper,
      chartLine: { fill: "none", width: 0 },
      plotAreaFill: C.paper,
      plotAreaLine: { fill: "none", width: 0 },
    });
    capture.hasLegend = false;
    styleChart(capture);
    const reviews = s.charts.add("doughnut", {
      position: { left: 715, top: 170, width: 500, height: 350 },
      categories: ["Observed event", "No observed event"],
      series: [{
        name: "Alert reviews",
        values: [5.87, 14.13],
        valuesFormatCode: "0.0",
        points: [{ idx: 0, fill: C.coral }, { idx: 1, fill: C.gold }],
      }],
      doughnutOptions: { holeSize: 62 },
      hasLegend: true,
      legend: { position: "bottom", overlay: false, textStyle: { fill: C.ink2, fontSize: 16 } },
      dataLabels: { showPercent: true, position: "outEnd", textStyle: { fill: C.ink, fontSize: 17, bold: true } },
      chartFill: C.paper,
      chartLine: { fill: "none", width: 0 },
      plotAreaFill: C.paper,
      plotAreaLine: { fill: "none", width: 0 },
    });
    reviews.hasLegend = false;
    styleChart(reviews);
    textBox(s, "Teal: captured 69.1%    Gray: missed 30.9%", { left: 75, top: 491, width: 565, height: 32 }, { fontSize: 18, color: C.ink2 });
    textBox(s, "Coral: event 29.4%    Gold: no event 70.6%", { left: 698, top: 491, width: 530, height: 32 }, { fontSize: 18, color: C.ink2 });
    textBox(s, "8.5 observed events", { left: 120, top: 530, width: 390, height: 38 }, { fontSize: 25, bold: true, color: C.teal, align: "center" });
    textBox(s, "20 alert reviews", { left: 770, top: 530, width: 390, height: 38 }, { fontSize: 25, bold: true, color: C.coral, align: "center" });
    textBox(s, "These counts describe retrospective concentration of events. They do not estimate events prevented by clinical action.", { left: 130, top: 592, width: 1020, height: 44 }, { fontSize: 21, bold: true, color: C.red, align: "center" });
    addSource(s, "Calculated from 8.49% prevalence, 69.13% recall, and 20% review capacity");
    addFooter(s, "DIAL-ALERT executive presentation", 5);
    addNotes(s, [
      "Per 100 sessions, the model places approximately 5.9 of 8.5 observed events in the 20-session review group.",
      "The same review group contains approximately 14.1 sessions without the event, which creates staff workload and potential alert fatigue.",
      "A prospective study must determine whether review changes treatment safely and prevents meaningful outcomes.",
    ], [
      "Project artifacts: artifacts/capacity_metrics.csv and artifacts/final_test_metrics.json",
    ]);
  }

  // 6. ROI
  {
    const s = newSlide(p);
    addSlideTitle(s, "ROI measurement framework", "The pilot should estimate benefits and costs before any investment claim");
    box(s, { left: 72, top: 148, width: 1136, height: 104 }, "#E8F2F0", "none", 0, 10);
    textBox(s, "Net value = events avoided × cost of an avoidable event − review labor − intervention cost − integration and monitoring", { left: 105, top: 176, width: 1070, height: 58 }, {
      fontSize: 28,
      bold: true,
      color: C.ink,
      align: "center",
      valign: "middle",
    });
    textBox(s, "Benefit evidence", { left: 82, top: 300, width: 460, height: 34 }, { fontSize: 25, bold: true, color: C.teal });
    const benefits = [
      "Change in clinically meaningful IDH events",
      "Avoided treatment interruption or escalation",
      "Downstream utilisation linked to the event",
      "Patient experience and recovery time",
    ];
    benefits.forEach((item, i) => {
      box(s, { left: 82, top: 356 + i * 55, width: 6, height: 30 }, C.teal2);
      textBox(s, item, { left: 106, top: 350 + i * 55, width: 470, height: 40 }, { fontSize: 20, color: C.ink2 });
    });
    vRule(s, 640, 300, 270, C.pale, 2);
    textBox(s, "Cost evidence", { left: 688, top: 300, width: 460, height: 34 }, { fontSize: 25, bold: true, color: C.coral });
    const costs = [
      "Minutes of clinical review per alert",
      "Action rate and unintended intervention burden",
      "Data integration, training, and support",
      "Ongoing monitoring, audit, and incident response",
    ];
    costs.forEach((item, i) => {
      box(s, { left: 688, top: 356 + i * 55, width: 6, height: 30 }, C.coral);
      textBox(s, item, { left: 712, top: 350 + i * 55, width: 470, height: 40 }, { fontSize: 20, color: C.ink2 });
    });
    rule(s, 82, 606, 1100, C.pale, 2);
    textBox(s, "Break-even decision: proceed only when measured benefit exceeds the full operating cost at an acceptable safety and equity profile.", { left: 82, top: 622, width: 1100, height: 34 }, { fontSize: 21, bold: true, color: C.ink });
    addFooter(s, "DIAL-ALERT executive presentation", 6);
    addNotes(s, [
      "No cost savings are claimed because the retrospective data contain neither intervention effects nor reliable cost data.",
      "The pilot should record alert review time, action, adverse consequences, and downstream events.",
      "The economic evaluation must compare DIAL-ALERT with current practice, including implementation and governance costs.",
    ]);
  }

  // 7. Risk and fairness
  {
    const s = newSlide(p);
    addSlideTitle(s, "Clinical, workload and fairness risks", "Fairness varies by metric and several protected attributes are unavailable");
    textBox(s, "Risk register", { left: 66, top: 150, width: 330, height: 34 }, { fontSize: 25, bold: true, color: C.teal });
    const risks = [
      ["Missed high-risk session", "False negatives remain at every threshold"],
      ["Alert fatigue", "20% capacity produces 14.1 false alerts per 100 sessions"],
      ["Unequal performance", "Recorded sex and age group gaps require review"],
      ["Automation and privacy", "Human override and minimum necessary data are mandatory"],
    ];
    risks.forEach(([head, body], i) => {
      const y = 208 + i * 100;
      box(s, { left: 66, top: y + 4, width: 7, height: 72 }, i < 2 ? C.coral : C.purple);
      textBox(s, head, { left: 92, top: y, width: 365, height: 28 }, { fontSize: 20, bold: true, color: C.ink });
      textBox(s, body, { left: 92, top: y + 36, width: 365, height: 50 }, { fontSize: 17, color: C.ink2 });
    });
    await addPng(s, "step5_fairness_overview.png", { left: 500, top: 152, width: 720, height: 420 }, "Subgroup alert selection, sensitivity, and false-positive rates");
    box(s, { left: 500, top: 586, width: 720, height: 55 }, "#F3E9E3", "none", 0, 8);
    textBox(s, "Race, ethnicity, socioeconomic status, and gender identity cannot be audited from the source data.", { left: 520, top: 600, width: 680, height: 30 }, { fontSize: 19, bold: true, color: C.red, align: "center" });
    addSource(s, "Source: Step 5 ethical AI and bias audit");
    addFooter(s, "DIAL-ALERT executive presentation", 7);
    addNotes(s, [
      "Recorded sex shows a disparate-impact ratio of 0.705 and equalized-odds gap of 0.076 in the original model.",
      "Sex-outcome reweighting improves these summaries but does not eliminate disparity.",
      "Age-group disparate impact is 0.541. Diabetes selection rates are similar, but sensitivity differs.",
      "Unavailable attributes must be collected prospectively with consent and governance rather than inferred through proxies.",
    ], [
      "Project artifacts: artifacts/step5_disparities.csv and artifacts/step5_attribute_availability.csv",
      "WHO. Ethics and governance of AI for health. 2021. https://www.who.int/publications/i/item/9789240029200",
    ]);
  }

  // 8. Governance gates
  {
    const s = newSlide(p);
    addSlideTitle(s, "Governance controls must precede live alerts", "Each gate requires documented evidence and an accountable owner");
    const rows = [
      ["1", "External validity", "Performance and calibration on current local patients", "Clinical analytics lead"],
      ["2", "Silent workflow", "Alert volume, timing, data quality, and drift without influencing care", "Dialysis operations"],
      ["3", "Human factors", "Comprehension, overrides, action patterns, and automation bias", "Clinical safety lead"],
      ["4", "Equity and privacy", "Subgroup errors, broader attributes, access controls, and retention", "Governance board"],
      ["5", "Monitoring and rollback", "Thresholds for drift, harm, downtime, and model withdrawal", "Model owner"],
    ];
    textBox(s, "Gate", { left: 76, top: 156, width: 90, height: 26 }, { fontSize: 15, bold: true, color: C.muted });
    textBox(s, "Evidence required", { left: 260, top: 156, width: 650, height: 26 }, { fontSize: 15, bold: true, color: C.muted });
    textBox(s, "Accountable owner", { left: 970, top: 156, width: 230, height: 26 }, { fontSize: 15, bold: true, color: C.muted });
    rows.forEach(([n, gate, evidence, owner], i) => {
      const y = 196 + i * 86;
      rule(s, 76, y - 10, 1124, C.pale, 1);
      textBox(s, n, { left: 76, top: y, width: 44, height: 44 }, {
        fontSize: 22,
        bold: true,
        color: C.white,
        fill: i === 4 ? C.coral : C.teal,
        align: "center",
        valign: "middle",
        insets: { left: 0, right: 0, top: 5, bottom: 0 },
      });
      textBox(s, gate, { left: 142, top: y + 2, width: 105, height: 52 }, { fontSize: 20, bold: true, color: C.ink });
      textBox(s, evidence, { left: 260, top: y + 2, width: 660, height: 54 }, { fontSize: 18, color: C.ink2 });
      textBox(s, owner, { left: 970, top: y + 2, width: 220, height: 54 }, { fontSize: 18, bold: true, color: C.purple });
    });
    addSource(s, "Governance position from the Step 5 ethical risk register");
    addFooter(s, "DIAL-ALERT executive presentation", 8);
    addNotes(s, [
      "A model should not move to live alerts because a retrospective AUC appears strong.",
      "Each gate has evidence, ownership, and an explicit stop condition.",
      "The rollback plan should identify who disables the model, how clinicians are notified, and how affected decisions are reviewed.",
    ], [
      "Project artifact: artifacts/step5_ethical_risk_register.csv",
    ]);
  }

  // 9. 90-day pilot
  {
    const s = newSlide(p);
    addSlideTitle(s, "Proposed pilot phases and feasibility targets", "Progression depends on evidence at the end of each phase");
    const phases = [
      ["Weeks 0–4", "Local validation", "Check features, calibration, subgroup errors and workload"],
      ["Weeks 5–8", "Silent evaluation", "Score without displaying alerts; time simulated reviews"],
      ["Weeks 9–12", "Conditional supervised study", "Proceed only after agreed safety and governance gates"],
    ];
    phases.forEach(([period, head, body], i) => {
      const y = 165 + i * 103;
      textBox(s, period, { left: 80, top: y, width: 175, height: 42 }, { fontSize: 24, bold: true, color: C.teal });
      textBox(s, head, { left: 275, top: y, width: 890, height: 38 }, { fontSize: 26, bold: true, color: C.ink });
      textBox(s, body, { left: 275, top: y+43, width: 890, height: 40 }, { fontSize: 22, color: C.ink2 });
    });
    textBox(s, "Draft targets for a future fixed-threshold evaluation", { left: 80, top: 495, width: 1100, height: 38 }, { fontSize: 25, bold: true, color: C.teal });
    textBox(s, "Sensitivity ≥65%, ≤20 alerts and ≤15 false alerts per 100 sessions", { left: 80, top: 542, width: 1100, height: 36 }, { fontSize: 23, color: C.ink });
    textBox(s, "Median active review ≤2 min per alert; local approval and uncertainty review required", { left: 80, top: 582, width: 1120, height: 50 }, { fontSize: 22, color: C.ink2 });
    addSource(s, "Post-study proposals, not achieved results or approved standards; docs/evaluation_protocol.md");
    addFooter(s, "DIAL-ALERT executive presentation", 9);
    addNotes(s, [
      "The 90-day schedule is illustrative and conditional. Targets were drafted after the retrospective study and were not original prespecified study criteria. They concern feasibility, not demonstrated clinical benefit. Clinical and operational leads must approve the strategy, sample size, confidence-interval requirements and stop rules before collecting pilot outcomes.",
      "Silent mode evaluates data delivery and score behavior without displaying alerts. Time review work in simulation first. The separate draft total-review budget is at most 40 minutes per 100 sessions. A median of two minutes does not imply a two-minute mean; measure total time and tail times directly.",
      "The supervised pilot begins only if external validity, operational feasibility, privacy, and equity gates pass.",
    ]);
  }

  // 10. Decision
  {
    const s = newSlide(p, true);
    addSlideTitle(s, "Decision requested: further validation", "The next investment should reduce uncertainty before introducing live alerts", { dark: true, accent: C.gold });
    textBox(s, "Approve", { left: 78, top: 165, width: 240, height: 42 }, { fontSize: 30, bold: true, color: C.teal2 });
    const approve = [
      "A local data and validation partner",
      "Clinical, informatics, privacy, and equity owners",
      "A prospective silent mode study",
      "A predefined go or stop review at 90 days",
    ];
    approve.forEach((item, i) => {
      box(s, { left: 82, top: 235 + i * 62, width: 8, height: 34 }, C.teal2);
      textBox(s, item, { left: 110, top: 229 + i * 62, width: 470, height: 45 }, { fontSize: 22, color: C.white });
    });
    vRule(s, 634, 166, 340, "#3A5268", 2);
    textBox(s, "Stop if", { left: 690, top: 165, width: 240, height: 42 }, { fontSize: 30, bold: true, color: C.orange });
    const stop = [
      "Performance does not transport locally",
      "Alert burden exceeds safe staffing capacity",
      "Subgroup error or calibration gaps are unacceptable",
      "Clinician behavior creates new safety risk",
    ];
    stop.forEach((item, i) => {
      box(s, { left: 694, top: 235 + i * 62, width: 8, height: 34 }, C.coral);
      textBox(s, item, { left: 722, top: 229 + i * 62, width: 470, height: 45 }, { fontSize: 22, color: C.white });
    });
    rule(s, 78, 525, 1110, "#3A5268", 2);
    textBox(s, "Until these gates are met, DIAL-ALERT remains an academic decision support prototype and must not determine treatment.", { left: 90, top: 560, width: 1090, height: 70 }, { fontSize: 27, bold: true, color: C.gold, align: "center" });
    addFooter(s, "DIAL-ALERT executive presentation", 10, true);
    addNotes(s, [
      "Ask leaders to approve the evidence-generating pathway and named governance ownership.",
      "Do not frame the decision as approval of a clinical tool.",
      "The 90-day review should decide whether a larger prospective effectiveness study is justified.",
    ]);
  }

  return p;
}

async function exportDraft(presentation, deckKey) {
  const deckDir = path.join(TMP_DIR, deckKey);
  await fs.mkdir(deckDir, { recursive: true });
  const candidatePath = path.join(deckDir, `${deckKey}-candidate.pptx`);
  await (await PresentationFile.exportPptx(presentation)).save(candidatePath);
  for (let i = 0; i < presentation.slides.count; i++) {
    const slide = presentation.slides.getItem(i);
    const png = await presentation.export({ slide, format: "png", scale: 1 });
    await fs.writeFile(path.join(deckDir, `slide-${String(i + 1).padStart(2, "0")}.png`), new Uint8Array(await png.arrayBuffer()));
    const layout = await slide.export({ format: "layout" });
    await fs.writeFile(path.join(deckDir, `slide-${String(i + 1).padStart(2, "0")}.layout.json`), await layout.text());
  }
  const montage = await presentation.export({ format: "webp", montage: true, scale: 0.6 });
  await fs.writeFile(path.join(deckDir, `${deckKey}-montage.webp`), new Uint8Array(await montage.arrayBuffer()));
  return candidatePath;
}

async function finalizeDeck(presentation, deckKey, filename, slideCount, chartSlides) {
  const deckDir = path.join(TMP_DIR, deckKey);
  const stagingDir = path.join(deckDir, ".presentation-finalizer");
  await fs.mkdir(stagingDir, { recursive: true });
  const candidatePath = path.join(stagingDir, `${deckKey}-candidate.pptx`);
  await (await PresentationFile.exportPptx(presentation)).save(candidatePath);
  const finalPath = path.join(OUTPUT_DIR, filename);
  const result = await finalizePresentation({
    explicitTotalSlideCount: slideCount,
    requiredNativeTableOwnerSlides: [],
    requiredNativeChartOwnerSlides: chartSlides,
    materializeLiteralChartWorkbooks: true,
    workspaceDir: WORKSPACE_DIR,
    candidatePath,
    finalPath,
    pythonExecutable: RUNTIME_PYTHON,
    integrityValidatorPath: path.join(SKILL_DIR, "container_tools/inspect_presentation_package_integrity.py"),
    layoutValidatorPath: path.join(SKILL_DIR, "container_tools/inspect_presentation_layout_geometry.py"),
    layoutArgs: [
      "--expected-slide-size-emu", SLIDE_SIZE_EMU,
      "--validate-bullet-geometry",
      "--validate-heading-fit",
    ],
    fontPolicy: { basis: "design", families: [FONT, MONO] },
    verifyArtifactToolImport: true,
    receiptPath: path.join(stagingDir, `${filename}.validation.json`),
  });
  await execFileAsync(RUNTIME_PYTHON, [
    path.join(PROJECT, "src", "sanitize_office_metadata.py"),
    finalPath,
    "--author",
    "Franklin B. Guillano",
    "--title",
    deckKey === "technical"
      ? "DIAL-ALERT Technical Presentation"
      : "DIAL-ALERT Business Presentation",
  ]);
  return { finalPath, result };
}

const finalize = process.argv.includes("--finalize");
const technical = await buildTechnicalDeck();
const business = await buildBusinessDeck();

if (!finalize) {
  const technicalCandidate = await exportDraft(technical, "technical");
  const businessCandidate = await exportDraft(business, "business");
  console.log(JSON.stringify({ mode: "draft", technicalCandidate, businessCandidate }, null, 2));
} else {
  const technicalResult = await finalizeDeck(
    technical,
    "technical",
    "Franklin_Guillano_DIAL_ALERT_Technical_Presentation.pptx",
    12,
    [3, 6, 8],
  );
  const businessResult = await finalizeDeck(
    business,
    "business",
    "Franklin_Guillano_DIAL_ALERT_Business_Presentation.pptx",
    10,
    [5],
  );
  console.log(JSON.stringify({ mode: "final", technicalResult, businessResult }, null, 2));
}
