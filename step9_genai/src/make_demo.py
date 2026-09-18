"""Render a captioned video of actual saved-draft replay output (not a screencast).
Requires Pillow 12.3.0 and ffmpeg on PATH; no dependencies needed for replay itself.
"""
import json
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]

def main():
    run = subprocess.run([sys.executable, str(ROOT/'src/replay_summary.py')], capture_output=True, text=True, check=True)
    tests = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', str(ROOT/'tests'), '-p', 'test_summary.py', '-v'], capture_output=True, text=True, check=True)
    # Keep frozen evidence unchanged; this run verifies the eight summary tests.
    facts = json.loads((ROOT/'examples/aggregate_facts.json').read_text())
    paragraphs = run.stdout.split('\n\n')
    cohort = next(p for p in paragraphs if p.startswith('The analytic'))
    results = next(p for p in paragraphs if p.startswith('The selected'))
    slides = [
        ('Generative AI, used transparently', 'DIAL-ALERT | AIM Capstone | Step 9\n\nAI-assisted documentation and source checking.\n\nRecorded-output walkthrough: saved draft replay.\nNo live LLM call. No patient-level records.'),
        ('1 / Begin with source facts', f"Aggregate facts from the existing project:\n\nSessions: {facts['cohort_sessions']:,}\nPatients: {facts['cohort_patients']:,}\nEvent prevalence: {facts['event_prevalence_pct']}%\n\nSource: frozen Step 8 model card and metrics."),
        ('2 / Run the saved example', '$ python3 src/replay_summary.py\n\n'+ '\n'.join(run.stdout.splitlines()[:4])+'\n\nThe language was AI-drafted during authoring.\nNumbers are filled from checked source fields.'),
        ('3 / Read the cohort summary', cohort+'\n\nAI-drafted example; investigator review pending.'),
        ('4 / Check the model results', results),
        ('5 / Test failure cases', '$ python3 -m unittest discover -s tests -v\n\nEight local tests passed.\n\nAltered numbers, unknown fields and unsupported\nplaceholders are rejected.\n\nUnsupported prose can still pass: human review matters.'),
        ('What this demonstrates', 'Generative AI helps communicate existing results.\nThe random forest still estimates risk.\n\nNo clinical benefit or time saving was measured.\nNo automated treatment recommendation.\n\nCode + sources + example + test evidence are included.')
    ]
    font_path = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    bold_path = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
    title = ImageFont.truetype(bold_path, 39)
    body = ImageFont.truetype(font_path, 29)
    small = ImageFont.truetype(font_path, 20)
    target = ROOT/'demo/DIAL_ALERT_Step9_Demo.mp4'
    target.parent.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        for index, (heading, content) in enumerate(slides):
            im = Image.new('RGB', (1280,720), '#0b1829')
            d = ImageDraw.Draw(im)
            d.rectangle((0,0,1280,12), fill='#39d6b3')
            d.text((64,46), 'DIAL-ALERT / STEP 9', font=small, fill='#39d6b3')
            d.text((64,97), heading, font=title, fill='white')
            y = 186
            for paragraph in content.split('\n'):
                lines = textwrap.wrap(paragraph, width=73) or ['']
                for line in lines:
                    d.text((64,y), line, font=body, fill='#d6e2ed')
                    y += 40
            if y > 660:
                raise RuntimeError('Slide text overflows: '+heading)
            d.text((64,678), 'Rendered local-output walkthrough | Academic prototype', font=small, fill='#9cacbf')
            d.text((1160,678), f'{index+1} / 7', font=small, fill='#9cacbf')
            im.save(tmp/f'{index:02}.png')
            if index == 4:
                im.save(ROOT/'demo/preview.png')
        subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate','1/9','-i',str(tmp/'%02d.png'),'-c:v','libx264','-r','24','-pix_fmt','yuv420p','-movflags','+faststart',str(target)], check=True)
    print('Created 63-second captioned MP4 from executed output.')

if __name__ == '__main__':
    main()
