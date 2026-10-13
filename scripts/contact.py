"""Contact sheet of a run of PDF pages, to locate where a text starts and ends cheaply.
usage: contact.py <ia-id> <first-pdf-page> <last-pdf-page> [cols=4]
Writes _work/sheets/<ia-id>/s<first>-<last>.png; each cell is captioned with its PDF page number."""
import os, subprocess, sys, tempfile
from PIL import Image, ImageDraw
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ia, a, b = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
cols = int(sys.argv[4]) if len(sys.argv) > 4 else 4
pdf = f'{ROOT}/_work/pdf/{ia}/issue.pdf'
out = f'{ROOT}/_work/sheets/{ia}'; os.makedirs(out, exist_ok=True)
W = 1560 // cols
cells = []
with tempfile.TemporaryDirectory() as t:
    for p in range(a, b + 1):
        subprocess.run(['pdftoppm', '-r', '60', '-gray', '-f', str(p), '-l', str(p), '-singlefile', '-png', pdf, f'{t}/p'], check=True)
        im = Image.open(f'{t}/p.png').convert('L'); im = im.resize((W, int(im.height * W / im.width)))
        cells.append((p, im.copy()))
H = max(im.height for _, im in cells) + 16
rows = -(-len(cells) // cols)
sheet = Image.new('L', (cols * W, rows * H), 255); d = ImageDraw.Draw(sheet)
for i, (p, im) in enumerate(cells):
    x, y = (i % cols) * W, (i // cols) * H
    sheet.paste(im, (x, y + 16)); d.text((x + 4, y + 2), f'pdf p{p}', fill=0)
dst = f'{out}/s{a:03d}-{b:03d}.png'; sheet.save(dst); print(dst)
