"""Refresh DIAL-ALERT presentations without duplicating slides or text boxes.

Run with --check to validate changes without saving anything.
A normal run backs up both inputs outside the repository before saving.
No model training is performed.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
import shutil
import tempfile

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
INK = '102A43'
TEAL = '0E7C7B'
PAPER = 'F7F5EF'
MUTED = '627D98'


def normalize(text: str) -> str:
    return ' '.join(text.split())


def slides_with_title(p, title: str) -> list:
    return [s for s in p.slides if any(
        sh.has_text_frame and normalize(sh.text) == normalize(title)
        for sh in s.shapes
    )]


def put(s, text: str, x: float, y: float, w: float, h: float,
        size: float = 21, color: str = INK, bold: bool = False):
    """Update a managed text box, or add it once if it is absent.

    Existing untagged boxes from the original revision script are located
    by position. Stable names identify them on subsequent runs.
    Ambiguous duplicates cause an error rather than deleting user content.
    """
    name = f'DIAL_ALERT_revision_{x:.3f}_{y:.3f}'
    tolerance = Inches(0.02)
    matches = [sh for sh in s.shapes if sh.has_text_frame and (
        sh.name == name or (
            sh.shape_type == MSO_SHAPE_TYPE.TEXT_BOX
            and abs(sh.left - Inches(x)) <= tolerance
            and abs(sh.top - Inches(y)) <= tolerance
        )
    )]
    if len(matches) > 1:
        raise ValueError(
            f'Multiple text boxes at ({x}, {y}). Review duplicates before saving.'
        )
    shape = matches[0] if matches else s.shapes.add_textbox(
        Inches(x), Inches(y), Inches(w), Inches(h)
    )
    shape.name = name
    shape.left, shape.top = Inches(x), Inches(y)
    shape.width, shape.height = Inches(w), Inches(h)
    tf = shape.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = 0
    tf.margin_top = tf.margin_bottom = Inches(0.05)
    tf.clear()
    p = tf.paragraphs[0]
    p.text = text
    for r in p.runs:
        r.font.name = 'Nimbus Sans'
        r.font.size = Pt(size)
        r.font.bold = bold
        r.font.color.rgb = RGBColor.from_string(color)
    return shape


def add_slide(p, title: str, subtitle: str, rows: list[tuple[str, str]]):
    """Refresh an existing evidence slide; create it only when absent."""
    matches = slides_with_title(p, title)
    if len(matches) > 1:
        raise ValueError(f'Duplicate evidence slides: {title!r}. No file saved.')
    if matches:
        s = matches[0]  # Preserve the slide ID, position, notes and other objects.
    else:
        if not len(p.slides):
            raise ValueError('Expected an existing deck with a conclusion slide.')
        layout = min(p.slide_layouts, key=lambda item: len(item.placeholders))
        # Normalize existing part names before adding a missing slide; this
        # also prevents name collisions after prior deletions or reordering.
        p.part.rename_slide_parts([entry.rId for entry in p.slides._sldIdLst])
        s = p.slides.add_slide(layout)
        # python-pptx has no public slide-reorder method. Move only the new
        # slide, keeping the original decision/conclusion last.
        ids = p.slides._sldIdLst
        new = ids[-1]
        ids.remove(new)
        ids.insert(len(ids) - 1, new)
        s.notes_slide.notes_text_frame.text = (
            '[Sources]\n'
            '- docs/model_card.md\n'
            '- docs/REPRODUCIBILITY_RECORD.md\n'
            '- docs/ARTIFACT_INVENTORY.md\n'
            '- step9_assistant/evidence/LIVE_REVIEW.md\n'
            '[/Sources]'
        )
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = RGBColor.from_string(PAPER)
    put(s, title, .85, .35, 11.7, .65, 29, bold=True)
    put(s, subtitle, .85, 1.08, 11.7, .55, 16, MUTED)
    y = 1.95
    for heading, body in rows:
        put(s, heading, .85, y, 11.5, .42, 21, TEAL, True)
        # The Step 9 explanation includes limitations; give it space without
        # encroaching on the reproduction heading below it.
        is_step9 = heading.startswith('Step 9:')
        put(s, body, .85, y + .48, 11.5,
            .97 if is_step9 else .82, 18 if is_step9 else 20)
        y += 1.55
    put(s, 'DIAL-ALERT | Academic prototype', .85, 7.05, 11.5, .25, 10, MUTED)
    return s


def replace(p, old: str, new: str) -> None:
    for s in p.slides:
        for sh in s.shapes:
            if not sh.has_text_frame:
                continue
            for para in sh.text_frame.paragraphs:
                if old in para.text:
                    text = para.text.replace(old, new)
                    if para.runs:
                        para.runs[0].text = text
                        for r in list(para.runs)[1:]:
                            r.text = ''
                    else:
                        para.text = text


def update_business_fairness(p) -> None:
    """Locate the risk slide by its title, not by a fixed slide number."""
    title = 'The main risks are clinical, operational, and equity related'
    matches = slides_with_title(p, title)
    if len(matches) != 1:
        raise ValueError(f'Expected one business risk slide named {title!r}.')
    s = matches[0]
    # Remove only a large picture occupying the original fairness-panel area.
    # Leave pictures elsewhere, the risk register, footer and notes unchanged.
    for sh in list(s.shapes):
        if (sh.shape_type == MSO_SHAPE_TYPE.PICTURE
                and sh.left >= Inches(5.0) and sh.top >= Inches(1.3)
                and sh.width >= Inches(4.0)
                and sh.top + sh.height <= Inches(6.1)):
            sh._element.getparent().remove(sh._element)
    put(s, 'Exploratory fairness audit', 5.4, 1.8, 6.7, .5, 23, TEAL, True)
    put(s, 'Recorded-sex selection ratio: 0.705\n'
           'Reweighting candidate: 0.764\n'
           'Age-group selection ratio: 0.541', 5.4, 2.5, 6.7, 1.7, 23)
    put(s, 'Confirm on fresh patients before adopting mitigation.',
        5.4, 4.5, 6.4, .9, 22, bold=True)


def revise(p, kind: str) -> None:
    replacements = {
        'Random forest balances ranking and probability quality': 'Random forest met the prespecified selection rule',
        'Reweighting improves recorded-sex gaps but does not resolve fairness': 'Fairness mitigation findings remain exploratory',
        'Reweighting retained': 'Reweighting explored',
        'The analysis is reproducible from source data to locked model': 'End-to-end reproduction successfully completed',
        'Configurations, partitions, trained pipelines, metrics, and integrity hashes are saved': 'Fresh Python 3.12 reproduction completed on 20 September 2026',
        'Candidate and selected pipelines with manifest': 'Selected predictor included; candidates regenerated',
        'Metrics, plots, assignments, audit outputs': 'Aggregate metrics and plots; assignments regenerated',
        'Public HEMOBP source files': 'Download HEMOBP source files; not bundled',
        'Leakage-controlled session table': 'Regenerate the session table; not bundled',
        'A 90-day pilot can answer the deployment question': 'A staged pilot should assess feasibility and safety',
        'Progression depends on evidence at the end of each phase': 'Illustrative timing; progression requires evidence and safety review',
        'Gate: benefit warrants a larger evaluation': 'Gate: feasibility supports a larger study',
        'Internal test performance supports a governed pilot decision': '170 test patients; 20% capacity recall 95% CI 63.2% to 74.4%',
    }
    for old, new in replacements.items():
        replace(p, old, new)
    if kind == 'Technical':
        replace(p, 'Histogram boosting ranked slightly higher on CV AP (0.446), but its validation Brier score was 0.134. The difference in AP was within the predefined 0.01 tolerance.',
                'Boosting CV AP: 0.446; RF: 0.440. Brier comparison used candidates as fitted. Equal calibration remains untested.')
        replace(p, 'Model manifest records package versions, file hashes, random seeds, feature order, and threshold metadata.',
                'HEMOBP Version 3 was reacquired and checksum-verified; the dataset was rebuilt, models retrained, outputs regenerated, and 15/15 automated tests passed.')
        add_slide(p, 'Eligibility is anchored to dialysis minute 120',
                  'Retrospective eligibility does not guarantee a 120-minute warning', [
            ('Prediction time', 'Earliest valid active-dialysis BP in minutes 0 to 30; index SBP must be at least 90 mmHg.'),
            ('Later observation', 'Require two distinct post-index measurement minutes and an observation at dialysis minute 120 or later.'),
            ('Example', 'Index at minute 20 and observation at minute 120 can qualify. Actual time to the first event has not yet been measured.'),
        ])
        add_slide(p, 'Two alert policies produce different workloads',
                  'Locked retrospective test results; define the prospective ranking batch', [
            ('Fixed probability threshold of 0.143', 'Sensitivity 66.1%; precision 30.6%; 18.3 reviews and 12.7 false alerts per 100 sessions.'),
            ('Review the highest-risk 20%', 'Recall 69.1%; precision 29.4%; 20 reviews and 14.1 false alerts per 100 sessions.'),
            ('Uncertainty comes from 170 patients', '95% CI: threshold sensitivity 55.0% to 74.5%; capacity recall 63.2% to 74.4%. Sessions are clustered within patients.'),
        ])
        add_slide(p, 'Optional steps demonstrate different capabilities',
                  'Evidence is limited to the included code, checks and media', [
            ('Step 8: local inference', 'Flask app, synthetic request, HTTP execution record and GIF demo. Local packaging does not establish clinical deployment.'),
            ('Step 9: Generative AI demonstrations', 'Earlier saved-draft replay; later live local Ollama assistant with examples, review evidence and edited video. Answer-quality limitations remain; citation and numeric checks do not establish semantic correctness.'),
            ('Reproduction boundary', 'Full source-to-training reproduction was completed on 20 September 2026. Results were numerically consistent with the locked reference rather than byte-for-byte identical.'),
        ])
    elif kind == 'Business':
        update_business_fairness(p)
    else:
        raise ValueError(f'Unknown presentation kind: {kind!r}')
    add_slide(p, 'Proposed pilot targets are not results',
              'Prespecify one alert policy and local safety stopping rules', [
        ('Event detection', 'At least 65% of later SBP-below-90 events detected in eligible sessions.'),
        ('False-alert workload', 'No more than 15 false alerts per 100 eligible sessions.'),
        ('Review time', 'Median at most 2 minutes per displayed alert. Measure outcomes and full costs before claiming benefit.'),
    ])
    for i, s in enumerate(p.slides, 1):
        for sh in s.shapes:
            if sh.has_text_frame and 'presentation  /' in sh.text:
                for para in sh.text_frame.paragraphs:
                    if para.runs:
                        para.runs[0].text = f'DIAL-ALERT {kind.lower()} presentation  /  {i:02}'
                        for r in list(para.runs)[1:]:
                            r.text = ''


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true',
                        help='Prepare and validate both decks without writing files.')
    args = parser.parse_args()
    prepared = []
    for kind in ('Technical', 'Business'):
        path = ROOT / 'reports' / f'Franklin_Guillano_DIAL_ALERT_{kind}_Presentation.pptx'
        if not path.is_file():
            raise FileNotFoundError(f'Missing presentation: {path}')
        p = Presentation(path)
        before = len(p.slides)
        revise(p, kind)
        buffer = BytesIO()
        p.save(buffer)
        data = buffer.getvalue()
        # Reopen the serialized result before allowing either input to be changed.
        checked = Presentation(BytesIO(data))
        prepared.append((path, data, before, len(checked.slides)))
    for path, _, before, after in prepared:
        print(f'{path.name}: {before} -> {after} slides')
    if args.check:
        print('CHECK ONLY: no presentation or backup files written.')
        return
    backup_root = Path.home() / 'DIAL_ALERT_presentation_backups'
    backup_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ_')
    backup_dir = Path(tempfile.mkdtemp(prefix=stamp, dir=backup_root))
    for path, _, _, _ in prepared:
        shutil.copy2(path, backup_dir / path.name)
    print(f'Original presentations backed up to: {backup_dir}')
    for path, data, _, _ in prepared:
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=path.parent, suffix='.tmp', delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(data)
            temporary.replace(path)
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()
    print('Both presentations saved. Review their layout before publishing.')


if __name__ == '__main__':
    main()
