import json,base64
from pathlib import Path
p=Path('data/khutab_written.json')
data=json.load(p.open(encoding='utf-8'))

def make_slug(item):
    iso=''.join([c for c in (item.get('date',{}).get('iso','') or item.get('date_iso','')) if c.isdigit()])[:8]
    seed=str(item.get('id') or item.get('title') or 'khutba').strip()
    b=base64.b64encode(seed.encode('utf-8')).decode('ascii').replace('+','-').replace('/','_').rstrip('=').lower()[:12]
    return (f"k-{iso}-{b}" if iso else f"k-{b}")

print('Expected filenames for target khutbahs:')
for item in data:
    if item.get('id') in ('local-2026-03-17-eid-fitr','local-2026-03-15-bir-alwaldayn'):
        print(item.get('id'), make_slug(item)+'.html')
print('\nActual files in khutab/:')
import os
for fn in sorted(os.listdir('khutab')):
    if fn.startswith('k-202603'):
        print(fn)
