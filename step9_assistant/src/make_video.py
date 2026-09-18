"""Render actual recorded HTTP evidence into a captioned silent MP4.
Build-only dependencies: Pillow and ffmpeg. Run record_demo.py first.
"""
from pathlib import Path
import json
import shutil
import subprocess
import tempfile
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1]
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BOLD='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'

def wrap(draw,text,font,width):
    lines=[]
    for para in text.split('\n'):
        line=''
        for word in para.split():
            trial=(line+' '+word).strip()
            if draw.textlength(trial,font=font)>width and line:
                lines.append(line);line=word
            else:line=trial
        lines.append(line)
    return lines

if __name__=='__main__':
    rows=json.loads((ROOT/'evidence/http_demo.json').read_text())
    if rows[5]['http_status'] != 503:
        raise RuntimeError('This renderer describes the missing-model run. Record live generation as a real screencast.')
    scenes=[('DIAL-ALERT Project Q&A Assistant',
             'Step 9: Use of Generative AI\n\nThis video shows actual source-retrieval HTTP results.\nThe local Llama model was unavailable during recording.\nFresh model generation is not demonstrated.',
             'Captioned HTTP walkthrough. No patient records. No simulated LLM success.')]
    for index in [0,1,2]:
        r=rows[index];s=r['response']['sources'][0]
        scenes.append((r['response']['question'],f"POST /ask  |  mode: sources  |  HTTP {r['http_status']}\n\n[{s['id']}] {s['title']}\n{s['text']}",
                       'Actual source-mode output. No language model called.'))
    r=rows[4]
    scenes.append(('The interface rejects extra input',
                   f"POST /ask  |  extra field supplied  |  HTTP {r['http_status']}\n\n{r['response']['error']}\n\nThe supported interface accepts only a question ID and mode.",
                   'Actual rejection response. The test field contained no patient information.'))
    r=rows[5]
    scenes.append(('Generation requires the local model',
                  f"POST /ask  |  mode: generate  |  HTTP {r['http_status']}\n\n{r['response'].get('error','See recorded response')}\n\nThe application shows no generated answer on failure.\nThe included Mac guide explains how to run and record live generation.",
                  'Actual missing-model response. Live answer quality remains unverified.'))
    scenes.append(('Code and examples accompany this demo',
                   'Included: source code, project excerpts, tests and report.\nThe presentation includes the model call and an illustrative answer.\n\nTo enable generation:\nollama pull llama3.2:3b\npython3 src/server.py\n\nCompare each generated sentence with its source.',
                   'Academic project explainer. The original random forest remains the predictor.'))
    with tempfile.TemporaryDirectory() as td:
        temp=Path(td)
        for i,(title,body,footer) in enumerate(scenes):
            im=Image.new('RGB',(1280,720),'#F3F8F8');d=ImageDraw.Draw(im)
            small=ImageFont.truetype(FONT,20);big=ImageFont.truetype(BOLD,38);normal=ImageFont.truetype(FONT,27)
            d.text((65,35),f'DIAL-ALERT   /   STEP 9   /   {i+1} OF {len(scenes)}',font=small,fill='#44616B')
            y=88
            for line in wrap(d,title,big,1150):d.text((65,y),line,font=big,fill='#096D69');y+=48
            y+=30
            for line in wrap(d,body,normal,1150):
                d.text((65,y),line,font=normal,fill='#183845');y+=38
            if y>625:raise RuntimeError(f'Video scene {i+1} exceeds safe text area: {y}')
            d.line((65,646,1210,646),fill='#CBDADB',width=2)
            d.text((65,667),footer,font=small,fill='#44616B')
            im.save(temp/f'{i:02}.png')
        concat=''.join(f"file '{i:02}.png'\nduration 12\n" for i in range(len(scenes)))+f"file '{len(scenes)-1:02}.png'\n"
        (temp/'frames.txt').write_text(concat)
        dest=ROOT/'demo/DIAL_ALERT_Step9_Project_Assistant_Demo.mp4'
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','concat','-safe','0','-i',str(temp/'frames.txt'),'-vf','fps=24','-c:v','libx264','-pix_fmt','yuv420p','-movflags','+faststart',str(dest)],check=True)
        # Keep just a private preview for the builder, not in the package.
        shutil.copyfile(temp/'01.png',ROOT.parents[1]/'video_preview.png')
        print(dest)
