"""Reproduce ten cases and the simulated full verification workflow; never create real user evidence."""
import argparse, json
from pathlib import Path
from core import read, write, build, apply, md, validate_patch
ROOT=Path(__file__).resolve().parents[1]
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',default='output');a=p.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
 cases=read(ROOT/'examples'/'cases.json'); summary=[]
 for c in cases:
  patch=build(c); validate_patch(patch); summary.append({'id':c['case_id'],'mode':c['mode'],'status':patch['status'],'decisions':[s['decision'] for s in patch['steps']],'labels':[s['label'] for s in patch['steps']]}); print(json.dumps(summary[-1],ensure_ascii=False))
  if c['case_id'] in ('partial_change','vscode_127','chrome_downloads'):
   write(out/(c['case_id']+'.json'),patch);(out/(c['case_id']+'.md')).write_text(md(patch),encoding='utf-8')
  if c['case_id']=='partial_change':
   for s in patch['steps']:
    for i in range(1,len(s['actions'])+1):
     f={'revision':patch['revision'],'environment':c['environment'],'step_id':s['id'],'action_index':i,'actor':'simulation','outcome':'success','expected_met':True,'note':'Synthetic scripted fixture; not actual user feedback','date':'2026-11-24'}; apply(patch,f)
   apply(patch,dict(f,step_id='__goal__',action_index=0));validate_patch(patch);write(out/'simulation-completed.json',patch);(out/'simulation-completed.md').write_text(md(patch),encoding='utf-8'); print('Simulated end-to-end status:',patch['status'])
 write(out/'case-results.json',summary)
