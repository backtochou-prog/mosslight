"""UI assets: the Mossbook pixel typeface (body and heading faces)."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from pixelart import font
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); OUT = os.path.join(ROOT, 'assets/ui'); os.makedirs(OUT, exist_ok=True)
n = font.build(os.path.join(OUT, 'mossbook.png'), os.path.join(OUT, 'mossbook.json')); font.build_heading(os.path.join(OUT, 'mossbook2.png'), os.path.join(OUT, 'mossbook2.json')); print(n, 'glyphs, two faces')
