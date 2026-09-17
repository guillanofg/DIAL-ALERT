import fs from "node:fs/promises";
import path from "node:path";
import { execFileSync } from "node:child_process";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const root = process.env.DIAL_ALERT_PROJECT_ROOT
  ? path.resolve(process.env.DIAL_ALERT_PROJECT_ROOT)
  : path.resolve(path.dirname(new URL(import.meta.url).pathname), "..");
const audit = JSON.parse(await fs.readFile(path.join(root, "artifacts", "step2_dataset_audit.json"), "utf8"));
const dictionary = JSON.parse(await fs.readFile(path.join(root, "artifacts", "step2_dictionary_rows.json"), "utf8"));

const outputDir = path.join(root, "reports");
const previewDir = path.join(root, "tmp", "step2_workbook_preview");
await fs.mkdir(outputDir, { recursive: true });
await fs.mkdir(previewDir, { recursive: true });

const outputPath = path.join(outputDir, "Franklin_Guillano_DIAL_ALERT_Data_Dictionary.xlsx");
const font = "Arial";
const colors = {
  navy: "#0B5C8E",
  blue: "#DCECF5",
  paleBlue: "#F2F8FB",
  teal: "#2A9D8F",
  orange: "#E07A35",
  paleOrange: "#FCEBDD",
  gray: "#5F6B76",
  lightGray: "#D9D9D9",
  paleGray: "#F5F6F7",
  black: "#111827",
  white: "#FFFFFF",
  red: "#B42318",
  paleRed: "#FEE4E2",
};

function baseSheet(sheet) {
  sheet.showGridLines = false;
  sheet.getRange("A1:Z200").format.font = { name: font, size: 10, color: colors.black };
  sheet.getRange("A1:Z200").format.verticalAlignment = "center";
}

function titleBlock(sheet, title, subtitle) {
  sheet.getRange("A2").values = [[title]];
  sheet.getRange("A2").format.font = { name: font, size: 16, bold: true, color: colors.black };
  sheet.getRange("A3").values = [[subtitle]];
  sheet.getRange("A3").format.font = { name: font, size: 10, italic: true, color: colors.gray };
  sheet.getRange("A4:L4").format.borders = { bottom: { style: "thin", color: colors.lightGray } };
}

function sectionHeader(sheet, range, label) {
  const r = sheet.getRange(range);
  r.format.fill = colors.navy;
  r.format.font = { name: font, size: 10, bold: true, color: colors.white };
  r.format.rowHeight = 22;
  sheet.getRange(range.split(":")[0]).values = [[label]];
}

function styleHeader(range) {
  range.format.fill = colors.navy;
  range.format.font = { name: font, size: 10, bold: true, color: colors.white };
  range.format.horizontalAlignment = "center";
  range.format.verticalAlignment = "center";
  range.format.wrapText = true;
  range.format.rowHeight = 32;
  range.format.borders = { preset: "all", style: "thin", color: colors.white };
}

function styleBody(range) {
  range.format.font = { name: font, size: 10, color: colors.black };
  range.format.verticalAlignment = "center";
  range.format.wrapText = true;
  range.format.borders = {
    insideHorizontal: { style: "thin", color: colors.lightGray },
    bottom: { style: "thin", color: colors.lightGray },
  };
}

function zebraRows(sheet, startRow, endRow, startCol, endCol) {
  for (let row = startRow; row <= endRow; row += 1) {
    if ((row - startRow) % 2 === 1) {
      sheet.getRangeByIndexes(row - 1, startCol - 1, 1, endCol - startCol + 1).format.fill = colors.paleBlue;
    }
  }
}

function dictionarySheet(workbook, name, rows, tableName, subtitle) {
  const sheet = workbook.worksheets.add(name);
  baseSheet(sheet);
  titleBlock(sheet, `DIAL ALERT ${name}`, subtitle);
  sheet.getRange("A5:K5").values = [[
    "Table",
    "Variable",
    "Data type",
    "Unit",
    "Allowed or observed values",
    "Missing n",
    "Missing percent",
    "Definition",
    "Provenance",
    "Analysis role and timing",
    "Quality notes",
  ]];
  styleHeader(sheet.getRange("A5:K5"));
  const matrix = rows.map((r) => [
    r.table,
    r.variable,
    r.data_type,
    r.unit,
    r.allowed_or_observed_values,
    r.missing_n,
    r.missing_pct / 100,
    r.definition,
    r.provenance,
    `${r.analysis_role}. ${r.prediction_availability}.`,
    r.quality_notes,
  ]);
  const endRow = 5 + matrix.length;
  sheet.getRange(`A6:K${endRow}`).values = matrix;
  styleBody(sheet.getRange(`A6:K${endRow}`));
  zebraRows(sheet, 6, endRow, 1, 11);
  sheet.getRange(`F6:F${endRow}`).format.numberFormat = "#,##0";
  sheet.getRange(`G6:G${endRow}`).format.numberFormat = "0.00%";
  sheet.getRange(`F6:G${endRow}`).format.horizontalAlignment = "right";
  sheet.getRange(`A6:E${endRow}`).format.horizontalAlignment = "left";
  sheet.getRange(`H6:K${endRow}`).format.horizontalAlignment = "left";
  sheet.getRange(`H6:K${endRow}`).format.verticalAlignment = "top";
  sheet.getRange(`A6:K${endRow}`).format.autofitRows();

  const widths = [19, 28, 15, 18, 32, 12, 15, 43, 36, 43, 48];
  const letters = "ABCDEFGHIJK".split("");
  letters.forEach((letter, index) => {
    sheet.getRange(`${letter}1:${letter}${endRow}`).format.columnWidth = widths[index];
  });
  sheet.freezePanes.freezeRows(5);
  sheet.freezePanes.freezeColumns(2);
  const table = sheet.tables.add(`A5:K${endRow}`, true, tableName);
  table.style = "TableStyleMedium2";
  table.showFilterButton = true;
  sheet.getRange(`G6:G${endRow}`).conditionalFormats.add("cellIs", {
    operator: "greaterThan",
    formula: 0,
    format: { fill: colors.paleOrange, font: { color: "#9A3412", bold: true } },
  });
  return sheet;
}

const workbook = Workbook.create();

const overview = workbook.worksheets.add("Overview");
baseSheet(overview);
overview.tabColor = colors.navy;
titleBlock(
  overview,
  "DIAL ALERT Data Collection and Understanding",
  "Capstone Project Step 2 prepared by Franklin Guillano"
);
overview.getRange("A6:J6").values = [["Dataset conclusion"]];
sectionHeader(overview, "A6:J6", "Dataset conclusion");
overview.getRange("A7:J9").merge();
overview.getRange("A7").values = [[
  "The public HEMOBP release is suitable for a reproducible session-level classification study. It combines patient characteristics, session records, and repeated intradialytic monitoring. The DIAL ALERT analytic table contains 106,758 eligible sessions from 830 patients. The primary blood-pressure-defined outcome occurs in 9,067 sessions (8.49%)."
]];
overview.getRange("A7:J9").format.wrapText = true;
overview.getRange("A7:J9").format.verticalAlignment = "center";
overview.getRange("A7:J9").format.font = { name: font, size: 11, color: colors.black };

sectionHeader(overview, "A11:J11", "Key analytic cohort measures");
overview.getRange("A12:B17").values = [
  ["Eligible sessions", audit.analytic.rows],
  ["Patients", audit.analytic.unique_patients],
  ["Variables", audit.analytic.columns],
  ["Study dates", `${audit.analytic.date_min} to ${audit.analytic.date_max}`],
  ["Primary IDH events", audit.analytic.outcome_events],
  ["Primary IDH prevalence", audit.analytic.outcome_prevalence],
];
styleBody(overview.getRange("A12:B17"));
overview.getRange("A12:A17").format.font = { name: font, size: 10, bold: true, color: colors.black };
overview.getRange("B12:B14").format.numberFormat = "#,##0";
overview.getRange("B16").format.numberFormat = "#,##0";
overview.getRange("B17").format.numberFormat = "0.00%";
overview.getRange("A12:A17").format.fill = colors.paleBlue;

overview.getRange("D12:E17").values = [
  ["Complete variables", audit.analytic.complete_columns],
  ["Highest missingness", audit.analytic.missing[0].missing_pct / 100],
  ["Index at minute zero", audit.analytic.index_at_zero_pct / 100],
  ["Index within five minutes", audit.analytic.index_by_five_pct / 100],
  ["Alternative drop outcome", audit.analytic.drop20_prevalence],
  ["Baseline-adjusted outcome", audit.analytic.flythe_prevalence],
];
styleBody(overview.getRange("D12:E17"));
overview.getRange("D12:D17").format.font = { name: font, size: 10, bold: true, color: colors.black };
overview.getRange("D12:D17").format.fill = colors.paleBlue;
overview.getRange("E12").format.numberFormat = "#,##0";
overview.getRange("E13:E17").format.numberFormat = "0.00%";

sectionHeader(overview, "A19:J19", "Public source tables");
overview.getRange("A20:J20").values = [[
  "Table", "File", "Unit of observation", "Rows", "Columns", "Patients", "Date range", "Missing cells", "Duplicate note", "Checksum"
]];
styleHeader(overview.getRange("A20:J20"));
const tableMatrix = audit.tables.map((r) => [
  r.table,
  r.file,
  r.grain,
  r.rows,
  r.columns,
  r.unique_patients,
  r.date_range,
  r.missing_cells,
  r.duplicate_note,
  r.checksum_status,
]);
overview.getRange("A21:J23").values = tableMatrix;
styleBody(overview.getRange("A21:J23"));
zebraRows(overview, 21, 23, 1, 10);
overview.getRange("D21:F23").format.numberFormat = "#,##0";
overview.getRange("H21:H23").format.numberFormat = "#,##0";
overview.getRange("D21:H23").format.horizontalAlignment = "right";
overview.getRange("J21:J23").format.horizontalAlignment = "center";

sectionHeader(overview, "A25:J25", "Data quality findings");
overview.getRange("A26:C26").values = [["Finding", "Observed result", "Handling"]];
styleHeader(overview.getRange("A26:C26"));
overview.getRange("A27:C31").values = [
  ["Published patient count", "The article reports 1,075 patients; the public files contain 1,072 patient rows.", "Use the public file count and disclose the three-patient difference."],
  ["Raw missingness", "Idp and VIP contain no blank fields. D1 has 128 placeholder rows with all session fields missing.", "Remove rows without a session date before linkage."],
  ["Duplicate keys", "D1 has nine duplicate patient-date records, including five exact duplicate rows.", "Use stable sorting and retain the first record for each patient-date key."],
  ["Analytic missingness", "Dialysis vintage is missing in 1.37%; three prior-session features are missing in 0.78% each.", "Impute inside each training fold; retain explicit history-count information."],
  ["Extreme values", "IQR flags occur most often for conductivity, prior IDH rate, and fluid excess.", "Apply physiologic bounds to raw monitor data; retain plausible extremes and test sensitivity."],
];
styleBody(overview.getRange("A27:C31"));
zebraRows(overview, 27, 31, 1, 3);
overview.getRange("A27:A31").format.font = { name: font, size: 10, bold: true, color: colors.black };
overview.getRange("A26:C31").format.autofitRows();

sectionHeader(overview, "A33:J33", "Sources and licence");
overview.getRange("A34:C37").values = [
  ["Article", "Lin CJ, Chen YY, Pan CF, Wu V, Wu CJ. Scientific Data. 2019;6:313.", "https://doi.org/10.1038/s41597-019-0319-8"],
  ["Dataset", "Chien CY. HEMOBP. Figshare. Version 3.", "https://doi.org/10.6084/m9.figshare.6260654.v3"],
  ["Licence", "Creative Commons Attribution 4.0", "https://creativecommons.org/licenses/by/4.0/"],
  ["Integrity", "The MD5 checksum of each local CSV matches the checksum published in Figshare metadata.", "Verified 2026-09-16"],
];
styleBody(overview.getRange("A34:C37"));
overview.getRange("A34:A37").format.font = { name: font, size: 10, bold: true, color: colors.black };
overview.getRange("A34:A37").format.fill = colors.paleBlue;
overview.getRange("A34:C37").format.autofitRows();

const overviewWidths = [24, 42, 58, 18, 18, 16, 38, 18, 46, 14];
"ABCDEFGHIJ".split("").forEach((letter, i) => {
  overview.getRange(`${letter}1:${letter}40`).format.columnWidth = overviewWidths[i];
});
overview.freezePanes.freezeRows(4);

const rawRows = dictionary.filter((r) => r.dataset_layer === "Raw source");
const analyticRows = dictionary.filter((r) => r.dataset_layer === "Analytic session table");
const rawSheet = dictionarySheet(
  workbook,
  "Raw Dictionary",
  rawRows,
  "RawDictionaryTable",
  "Original variables in the three public HEMOBP source files"
);
rawSheet.tabColor = colors.teal;
const analyticSheet = dictionarySheet(
  workbook,
  "Analytic Dictionary",
  analyticRows,
  "AnalyticDictionaryTable",
  "Session-level variables used for cohort audit, modelling, outcomes, and leakage control"
);
analyticSheet.tabColor = colors.orange;

const quality = workbook.worksheets.add("Quality Audit");
baseSheet(quality);
quality.tabColor = colors.gray;
titleBlock(quality, "DIAL ALERT Data Quality Audit", "Cohort construction, missingness, outlier flags, and file integrity");

sectionHeader(quality, "A6:F6", "Cohort construction");
quality.getRange("A7:C7").values = [["Stage", "Records or sessions", "Action"]];
styleHeader(quality.getRange("A7:C7"));
const cleaningStages = [
  ["Raw patient table", audit.cohort_flow.patient_rows, "Retained as the source of patient-level characteristics"],
  ["Raw session table", audit.cohort_flow.d1_rows, "Removed missing dates and collapsed duplicate patient-date keys"],
  ["Valid unique patient-days", audit.cohort_flow.d1_valid_unique_patient_days, "Used as the session linkage frame"],
  ["Raw monitoring records", audit.cohort_flow.vip_rows, "Linked by patient and calendar date"],
  ["Linked monitoring records", audit.cohort_flow.vip_rows_linked_to_d1, "Applied physiologic and elapsed-time bounds"],
  ["Linked patient-days", audit.cohort_flow.linked_patient_days, "Required a valid active-dialysis index record"],
  ["Patient-days with index", audit.cohort_flow.patient_days_with_index_record, "Required baseline SBP of at least 90 and adequate later follow-up"],
  ["Final eligible sessions", audit.cohort_flow.final_eligible_sessions, "Used for EDA and modelling"],
];
quality.getRange("A8:C15").values = cleaningStages;
styleBody(quality.getRange("A8:C15"));
zebraRows(quality, 8, 15, 1, 3);
quality.getRange("B8:B15").format.numberFormat = "#,##0";
quality.getRange("B8:B15").format.horizontalAlignment = "right";

sectionHeader(quality, "A17:F17", "Missingness in the eligible session table");
quality.getRange("A18:C18").values = [["Variable", "Missing n", "Missing percent"]];
styleHeader(quality.getRange("A18:C18"));
const missingRows = audit.analytic.missing.filter((r) => r.missing_n > 0).map((r) => [r.variable, r.missing_n, r.missing_pct / 100]);
quality.getRange(`A19:C${18 + missingRows.length}`).values = missingRows;
styleBody(quality.getRange(`A19:C${18 + missingRows.length}`));
zebraRows(quality, 19, 18 + missingRows.length, 1, 3);
quality.getRange(`B19:B${18 + missingRows.length}`).format.numberFormat = "#,##0";
quality.getRange(`C19:C${18 + missingRows.length}`).format.numberFormat = "0.00%";

const outlierStart = 25;
sectionHeader(quality, `A${outlierStart}:H${outlierStart}`, "IQR outlier flags for analytic predictors");
quality.getRange(`A${outlierStart + 1}:H${outlierStart + 1}`).values = [[
  "Feature", "Minimum", "Q1", "Median", "Q3", "Maximum", "Flagged n", "Flagged percent"
]];
styleHeader(quality.getRange(`A${outlierStart + 1}:H${outlierStart + 1}`));
const outlierRows = audit.outliers.map((r) => [
  r.feature, r.minimum, r.q1, r.median, r.q3, r.maximum, r.iqr_flagged_n, r.iqr_flagged_pct / 100,
]);
const outlierEnd = outlierStart + 1 + outlierRows.length;
quality.getRange(`A${outlierStart + 2}:H${outlierEnd}`).values = outlierRows;
styleBody(quality.getRange(`A${outlierStart + 2}:H${outlierEnd}`));
zebraRows(quality, outlierStart + 2, outlierEnd, 1, 8);
quality.getRange(`B${outlierStart + 2}:F${outlierEnd}`).format.numberFormat = "0.00";
quality.getRange(`G${outlierStart + 2}:G${outlierEnd}`).format.numberFormat = "#,##0";
quality.getRange(`H${outlierStart + 2}:H${outlierEnd}`).format.numberFormat = "0.00%";

const integrityStart = outlierEnd + 2;
sectionHeader(quality, `A${integrityStart}:F${integrityStart}`, "File integrity");
quality.getRange(`A${integrityStart + 1}:F${integrityStart + 1}`).values = [[
  "File", "Size bytes", "Observed MD5", "Source MD5", "Status", "Source version"
]];
styleHeader(quality.getRange(`A${integrityStart + 1}:F${integrityStart + 1}`));
const integrityRows = audit.tables.map((r) => [
  r.file, r.size_bytes, r.observed_md5, r.source_md5, r.checksum_status, "Figshare 6260654 version 3",
]);
quality.getRange(`A${integrityStart + 2}:F${integrityStart + 4}`).values = integrityRows;
styleBody(quality.getRange(`A${integrityStart + 2}:F${integrityStart + 4}`));
zebraRows(quality, integrityStart + 2, integrityStart + 4, 1, 6);
quality.getRange(`B${integrityStart + 2}:B${integrityStart + 4}`).format.numberFormat = "#,##0";
quality.getRange(`E${integrityStart + 2}:E${integrityStart + 4}`).format.horizontalAlignment = "center";
quality.getRange(`E${integrityStart + 2}:E${integrityStart + 4}`).conditionalFormats.add("containsText", {
  text: "Mismatch",
  format: { fill: colors.paleRed, font: { color: colors.red, bold: true } },
});

const qualityWidths = [32, 18, 46, 46, 16, 34, 16, 18];
"ABCDEFGH".split("").forEach((letter, i) => {
  quality.getRange(`${letter}1:${letter}${integrityStart + 5}`).format.columnWidth = qualityWidths[i];
});
quality.getRange(`A7:H${integrityStart + 4}`).format.autofitRows();
quality.freezePanes.freezeRows(4);

workbook.recalculate();

const overviewCheck = await workbook.inspect({
  kind: "table",
  sheetId: "Overview",
  range: "A11:J23",
  include: "values,formulas",
  tableMaxRows: 20,
  tableMaxCols: 10,
  maxChars: 5000,
});
const dictionaryCheck = await workbook.inspect({
  kind: "table",
  sheetId: "Analytic Dictionary",
  range: "A5:K12",
  include: "values,formulas",
  tableMaxRows: 12,
  tableMaxCols: 11,
  maxChars: 7000,
});
const errorCheck = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!",
  options: { useRegex: true, maxResults: 100 },
  summary: "final formula error scan",
  maxChars: 3000,
});

const previews = [
  ["overview.png", "Overview", "A1:J38"],
  ["raw_dictionary.png", "Raw Dictionary", "A1:K28"],
  ["analytic_dictionary_top.png", "Analytic Dictionary", "A1:K25"],
  ["analytic_dictionary_bottom.png", "Analytic Dictionary", "A26:K45"],
  ["quality_audit_top.png", "Quality Audit", "A1:H26"],
  ["quality_audit_bottom.png", "Quality Audit", `A27:H${integrityStart + 5}`],
];
for (const [filename, sheetName, range] of previews) {
  const image = await workbook.render({ sheetName, range, scale: 1.25, format: "png" });
  await fs.writeFile(path.join(previewDir, filename), new Uint8Array(await image.arrayBuffer()));
}

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
const python = process.env.PYTHON ?? "python";
execFileSync(python, [
  path.join(root, "src", "sanitize_office_metadata.py"),
  outputPath,
  "--author",
  "Franklin B. Guillano",
  "--title",
  "DIAL-ALERT Data Dictionary",
], { stdio: "inherit" });

console.log(JSON.stringify({
  outputPath,
  sheets: ["Overview", "Raw Dictionary", "Analytic Dictionary", "Quality Audit"],
  rowCounts: { raw: rawRows.length, analytic: analyticRows.length },
  overviewCheck: overviewCheck.ndjson,
  dictionaryCheck: dictionaryCheck.ndjson,
  errorCheck: errorCheck.ndjson,
}, null, 2));
