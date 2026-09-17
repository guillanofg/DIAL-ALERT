# DIAL-ALERT Step 6: Final Presentation and Communication

This submission contains two audience-specific PowerPoint decks.

## Deliverables

- `reports/Franklin_Guillano_DIAL_ALERT_Technical_Presentation.pptx`
  Twelve slides for technical peers covering problem framing, cohort construction, leakage control, patient-grouped evaluation, model comparison, held-out performance, alert capacity, explainability, fairness, mitigation, reproducibility, and validation gates.

- `reports/Franklin_Guillano_DIAL_ALERT_Business_Presentation.pptx`
  Ten slides for clinical and executive leaders covering the proposed workflow, evidence strength, operational impact, an ROI measurement framework, risks, governance, a 90-day pilot, and the requested decision.

Both decks include presenter notes with talking points and source citations. Native PowerPoint charts remain editable.

## Evidence boundary

DIAL-ALERT is a retrospective academic clinical decision support prototype. The study shows risk ranking and operational concentration of observed events. It does not show that alerts prevent events, improve patient outcomes, save costs, or transfer to another centre. The business deck therefore presents an ROI framework and pilot measurement plan rather than invented savings.

## Rebuild the decks

The presentation builder is `src/create_step6_presentations.mjs`. It uses the project artifacts produced in Steps 2 through 5. Run it with the presentation runtime and environment paths documented by the project environment.

## Main data source

Lin CJ, Chen YY, Pan CF, Wu VC, and Wu CJ. Dataset supporting blood pressure prediction for the management of chronic hemodialysis. *Scientific Data*. 2019;6:313. https://doi.org/10.1038/s41597-019-0319-8
