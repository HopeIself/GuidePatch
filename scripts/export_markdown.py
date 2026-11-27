import argparse,sys
from pathlib import Path
from core import read, md
if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('patch'); p.add_argument('out'); p.add_argument('--public',action='store_true'); a=p.parse_args()
    try:
        out=Path(a.out); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(md(read(a.patch),a.public),encoding='utf-8'); print('Exported '+str(out))
    except (ValueError,OSError,KeyError,TypeError) as e: sys.exit('Rejected: '+str(e))
