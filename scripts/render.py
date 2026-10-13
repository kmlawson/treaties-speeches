"""Render PDF pages of one issue to PNG for reading.
usage: render.py <ia-id> <first-pdf-page> <last-pdf-page> [dpi=130]
PDF page = Internet Archive leaf number (the nNN in the index links) + 1.
Writes _work/pages/<ia-id>/p<NNN>.png (NNN = PDF page) and prints the paths."""
import os, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ia, a, b = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
dpi = sys.argv[4] if len(sys.argv) > 4 else '130'
pdf = f'{ROOT}/_work/pdf/{ia}/issue.pdf'
out = f'{ROOT}/_work/pages/{ia}'; os.makedirs(out, exist_ok=True)
for p in range(a, b + 1):
    dst = f'{out}/p{p:03d}.png'
    if not os.path.exists(dst):
        subprocess.run(['pdftoppm', '-r', dpi, '-gray', '-f', str(p), '-l', str(p), '-singlefile', '-png', pdf, dst[:-4]], check=True)
    print(dst)
