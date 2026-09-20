"""Refresh existing presentation content and append readable evidence slides."""
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
ROOT=Path(__file__).resolve().parents[1]
INK='102A43';TEAL='0E7C7B';PAPER='F7F5EF';MUTED='627D98'

def put(s,text,x,y,w,h,size=21,color=INK,bold=False):
    shape=s.shapes.add_textbox(Inches(x),Inches(y),Inches(w),Inches(h))
    tf=shape.text_frame;tf.word_wrap=True
    tf.margin_left=tf.margin_right=0
    p=tf.paragraphs[0];p.text=text
    for r in p.runs:r.font.name='Nimbus Sans';r.font.size=Pt(size);r.font.bold=bold;r.font.color.rgb=RGBColor.from_string(color)
    return shape

def add_slide(p,title,subtitle,rows):
    s=p.slides.add_slide(p.slide_layouts[0])
    s.background.fill.solid();s.background.fill.fore_color.rgb=RGBColor.from_string(PAPER)
    put(s,title,.85,.35,11.7,.65,29,bold=True)
    put(s,subtitle,.85,1.08,11.7,.55,16,MUTED)
    y=1.95
    for heading,body in rows:
        put(s,heading,.85,y,11.5,.42,21,TEAL,True)
        put(s,body,.85,y+.48,11.5,.82,20)
        y+=1.55
    put(s,'DIAL-ALERT | Academic prototype',.85,7.05,11.5,.25,10,MUTED)
    # Keep the original decision/conclusion as the last slide.
    ids=p.slides._sldIdLst; new=ids[-1];ids.remove(new);ids.insert(len(ids)-1,new)
    return s

def replace(p,a,b):
    for s in p.slides:
        for sh in s.shapes:
            if not sh.has_text_frame:continue
            for para in sh.text_frame.paragraphs:
                if a in para.text:
                    txt=para.text.replace(a,b)
                    if para.runs:
                        para.runs[0].text=txt
                        for r in list(para.runs)[1:]:r.text=''
                    else:para.text=txt

def main():
 for kind in ('Technical','Business'):
    f=ROOT/'reports'/f'Franklin_Guillano_DIAL_ALERT_{kind}_Presentation.pptx'
    p=Presentation(f)
    # Idempotent on already revised binaries.
    if any(sh.has_text_frame and 'Proposed pilot targets are not results' in sh.text for s in p.slides for sh in s.shapes):continue
    replacements={
      'Random forest balances ranking and probability quality':'Random forest met the prespecified selection rule',
      'Reweighting improves recorded-sex gaps but does not resolve fairness':'Fairness mitigation findings remain exploratory',
      'Reweighting retained':'Reweighting explored',
      'The analysis is reproducible from source data to locked model':'End-to-end reproduction successfully completed',
      'Configurations, partitions, trained pipelines, metrics, and integrity hashes are saved':'Fresh Python 3.12 reproduction completed on 20 September 2026',
      'Candidate and selected pipelines with manifest':'Selected predictor included; candidates regenerated',
      'Metrics, plots, assignments, audit outputs':'Aggregate metrics and plots; assignments regenerated',
      'Public HEMOBP source files':'Download HEMOBP source files; not bundled',
      'Leakage-controlled session table':'Regenerate the session table; not bundled',
      'A 90-day pilot can answer the deployment question':'A staged pilot should assess feasibility and safety',
      'Progression depends on evidence at the end of each phase':'Illustrative timing; progression requires evidence and safety review',
      'Gate: benefit warrants a larger evaluation':'Gate: feasibility supports a larger study',
      'Internal test performance supports a governed pilot decision':'170 test patients; 20% capacity recall 95% CI 63.2% to 74.4%',
    }
    for a,b in replacements.items():replace(p,a,b)
    if kind=='Technical':
      replace(p,'Histogram boosting ranked slightly higher on CV AP (0.446), but its validation Brier score was 0.134. The difference in AP was within the predefined 0.01 tolerance.','Boosting CV AP: 0.446; RF: 0.440. Brier comparison used candidates as fitted. Equal calibration remains untested.')
      replace(p,'Model manifest records package versions, file hashes, random seeds, feature order, and threshold metadata.','HEMOBP Version 3 was reacquired and checksum-verified; the dataset was rebuilt, models retrained, outputs regenerated, and 15/15 automated tests passed.')
      add_slide(p,'Eligibility is anchored to dialysis minute 120','Retrospective eligibility does not guarantee a 120-minute warning',[('Prediction time','Earliest valid active-dialysis BP in minutes 0 to 30; index SBP must be at least 90 mmHg.'),('Later observation','Require two distinct post-index measurement minutes and an observation at dialysis minute 120 or later.'),('Example','Index at minute 20 and observation at minute 120 can qualify. Actual time to the first event has not yet been measured.')])
      add_slide(p,'Two alert policies produce different workloads','Locked retrospective test results; define the prospective ranking batch',[('Fixed probability threshold of 0.143','Sensitivity 66.1%; precision 30.6%; 18.3 reviews and 12.7 false alerts per 100 sessions.'),('Review the highest-risk 20%','Recall 69.1%; precision 29.4%; 20 reviews and 14.1 false alerts per 100 sessions.'),('Uncertainty comes from 170 patients','95% CI: threshold sensitivity 55.0% to 74.5%; capacity recall 63.2% to 74.4%. Sessions are clustered within patients.')])
      add_slide(p,'Optional steps demonstrate different capabilities','Evidence is limited to the included code, checks and media',[('Step 8: local inference','Flask app, synthetic request, HTTP execution record and GIF demo. Local packaging does not establish clinical deployment.'),('Step 9: saved-draft replay','The included demo replays a saved AI draft and validates numbers. It does not demonstrate a live LLM call.'),('Reproduction boundary','Full source-to-training reproduction was completed on 20 September 2026. Results were numerically consistent with the locked reference rather than byte-for-byte identical.')])
    else:
      # Replace unreadable multi-panel raster with the three relevant audit summaries.
      s=p.slides[6]
      for sh in list(s.shapes):
        if sh.shape_type==13:
          sh._element.getparent().remove(sh._element)
      put(s,'Exploratory fairness audit',5.4,1.8,6.7,.5,23,TEAL,True)
      put(s,'Recorded-sex selection ratio: 0.705\nReweighting candidate: 0.764\nAge-group selection ratio: 0.541',5.4,2.5,6.7,1.7,23)
      put(s,'Confirm on fresh patients before adopting mitigation.',5.4,4.5,6.4,.9,22,bold=True)
    add_slide(p,'Proposed pilot targets are not results','Prespecify one alert policy and local safety stopping rules',[('Event detection','At least 65% of later SBP-below-90 events detected in eligible sessions.'),('False-alert workload','No more than 15 false alerts per 100 eligible sessions.'),('Review time','Median at most 2 minutes per displayed alert. Measure outcomes and full costs before claiming benefit.')])
    # Label all slide order footers consistently after insertion.
    for i,s in enumerate(p.slides,1):
      for sh in s.shapes:
        if sh.has_text_frame and ('presentation  /' in sh.text):
          for para in sh.text_frame.paragraphs:
            if para.runs:
              para.runs[0].text=f'DIAL-ALERT {kind.lower()} presentation  /  {i:02}'
              for r in list(para.runs)[1:]:r.text=''
    p.save(f);print(f.name,len(p.slides))

if __name__=='__main__':main()
