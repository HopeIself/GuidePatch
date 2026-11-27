import argparse, json, sys
from core import read, normalize, Invalid
if __name__=='__main__':
    p=argparse.ArgumentParser(description='Validate structured, redacted tutorial data (not OCR)'); p.add_argument('case'); a=p.parse_args()
    try: print(json.dumps(normalize(read(a.case)),ensure_ascii=False,indent=2))
    except (ValueError,OSError,KeyError,TypeError) as e: sys.exit('Invalid input: '+str(e))
