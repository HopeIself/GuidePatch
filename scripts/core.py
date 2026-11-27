"""GuidePatch deterministic structure/state engine. Standard library only."""
import datetime as dt
import hashlib
import html
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

ENV = ('product', 'version', 'os', 'language', 'context')
UNKNOWN = {'unknown', '未知', '不明', '?', 'n/a', '待确认'}
ID = re.compile(r'^[A-Za-z0-9_-]{1,50}$')
SECRET = re.compile(r'(?i)(?:[\w.+-]+@[\w.-]+\.[a-z]{2,}|(?:api[_ -]?key|password|passwd|token|验证码|密码|密钥)\s*[:=：]\s*\S+|\b(?:sk-[A-Za-z0-9_-]{15,}|AKIA[A-Z0-9]{16})\b|(?:[A-Z]:\\Users\\|/home/|/Users/)[^\s/\\]+|https?://[^\s]+[?#])')

class Invalid(ValueError): pass

def require(ok, message):
    if not ok: raise Invalid(message)

def obj(x, keys, optional=()):
    require(isinstance(x, dict), 'Expected object')
    require(set(keys) <= set(x) <= set(keys) | set(optional), 'Missing or unexpected fields: ' + ','.join(sorted(set(keys)^set(x))))
    return x

def text(x, name, maximum=400):
    require(isinstance(x, str) and 0 < len(x.strip()) <= maximum and len(x) <= maximum, name + ': invalid text')
    require(not SECRET.search(x), name + ': possible private data; redact first')
    require(not any(ord(c)<32 and c not in '\n\t' for c in x), name + ': control characters')
    return x.strip()

def ident(x, name):
    require(isinstance(x,str) and ID.fullmatch(x), name + ': invalid ID')
    return x

def arr(x, name, limit=40):
    require(isinstance(x,list) and len(x)<=limit, name + ': invalid list')
    return x

def boolean(x, name):
    require(type(x) is bool, name + ': expected boolean')
    return x

def enum(x, values, name):
    require(isinstance(x,str) and x in values, name + ': invalid value')
    return x

def date(x):
    require(isinstance(x,str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}',x), 'Invalid ISO date')
    try: d=dt.date.fromisoformat(x)
    except ValueError as e: raise Invalid('Invalid date') from e
    return d.isoformat()

def env(x):
    obj(x,ENV)
    return {k:text(x[k],k,100) for k in ENV}

def known(e): return all(v.strip().lower() not in UNKNOWN for v in e.values())

def digest(x): return hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()[:24]

def read(path):
    p=Path(path); require(p.stat().st_size<=1_000_000,'Input too large')
    def pairs(items):
        out={}
        for k,v in items:
            require(k not in out,'Duplicate JSON key'); out[k]=v
        return out
    return json.loads(p.read_text(encoding='utf-8-sig'), object_pairs_hook=pairs)

def write(path, value):
    p=Path(path); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def normalize(c):
    obj(c,('case_id','mode','environment','old_version','goal','origin','sources','steps'))
    ident(c['case_id'],'case_id'); enum(c['mode'],('live','documentary','simulation'),'mode')
    e=env(c['environment']); text(c['old_version'],'old_version',100); text(c['goal'],'goal',200); text(c['origin'],'origin',200)
    sources={}
    for s in arr(c['sources'],'sources'):
        obj(s,('id','kind','fact','reviewed','scope','url'))
        sid=ident(s['id'],'source id'); require(sid not in sources,'Duplicate source ID')
        enum(s['kind'],('official','screenshot','user_observation','other'),'source kind'); text(s['fact'],'fact'); boolean(s['reviewed'],'reviewed')
        require(s['scope'] is None or isinstance(s['scope'],dict),'Invalid source scope')
        if s['scope'] is not None: env(s['scope'])
        if s['kind']=='official':
            u=text(s['url'],'source URL',500); parsed=urlsplit(u)
            require(parsed.scheme=='https' and parsed.hostname and not parsed.username and not parsed.password and not parsed.query and not parsed.fragment,'Official evidence must be clean HTTPS URL')
        else: require(s['url'] is None,'Non-official source URL must be null')
        sources[sid]=s
    def refs(xs):
        require(len(arr(xs,'refs',20))==len(set(ident(x,'source ref') for x in xs)),'Duplicate evidence reference')
        require(all(x in sources for x in xs),'Unknown evidence reference')
    require(0<len(arr(c['steps'],'steps',30)),'No steps')
    seen=set()
    for s in c['steps']:
        obj(s,('id','intent','original','precondition','expected','assessment','risk','conflict','goal_preserved','refs','candidate','reason'))
        sid=ident(s['id'],'step id'); require(sid not in seen and sid!='__goal__','Duplicate or reserved step ID'); seen.add(sid)
        for k in ('intent','original','precondition','expected','reason'): text(s[k],k)
        enum(s['assessment'],('unchanged','changed','unknown','removed'),'assessment'); enum(s['risk'],('low','review'),'risk')
        boolean(s['conflict'],'conflict'); boolean(s['goal_preserved'],'goal_preserved'); refs(s['refs'])
        for a in arr(s['candidate'],'candidate',8):
            obj(a,('action','expected','refs')); text(a['action'],'action'); text(a['expected'],'expected'); refs(a['refs'])
        require(s['assessment']=='changed' or not s['candidate'],'Only changed steps may have replacements')
    return json.loads(json.dumps(c,ensure_ascii=False))

def build(case):
    c=normalize(case); e=c['environment']; sources={s['id']:s for s in c['sources']}
    def supporting(ids):
        return [sources[i] for i in ids if sources[i]['reviewed'] and (sources[i]['scope']==e or (sources[i]['kind']=='official' and sources[i]['scope'] is None)) and sources[i]['kind'] in ('official','screenshot','user_observation')]
    def documented(ids): return any(s['kind']=='official' and s['scope']==e for s in supporting(ids))
    out=[]
    for s in c['steps']:
        why=None; actions=[]; refs=s['refs']; assessment=s['assessment']
        if not known(e): why='Current environment unknown: obtain exact version, OS, language and context.'
        elif s['risk']!='low': why='Risky action: stop and seek appropriate official guidance.'
        elif s['conflict']: why='Conflicting evidence: resolve before continuing.'
        elif not s['goal_preserved']: why='Intent not preserved: clarify the goal.'
        elif assessment in ('unknown','removed'): why='Insufficient evidence or removed feature: do not guess.'
        elif not supporting(refs): why='No reviewed, applicable evidence for diagnosis.'
        elif assessment=='changed' and (not s['candidate'] or any(not supporting(a['refs']) for a in s['candidate'])): why='Replacement action lacks reviewed applicable evidence.'
        if why: label='BLOCKED'
        elif assessment=='unchanged':
            actions=[{'action':s['original'],'expected':s['expected'],'refs':refs}]; label='DOCUMENTED' if documented(refs) else 'INFERRED'
        else:
            actions=s['candidate']; label='DOCUMENTED' if all(documented(a['refs']) for a in actions) else 'INFERRED'
        out.append({'id':s['id'],'intent':s['intent'],'original':s['original'],'precondition':s['precondition'],'expected':s['expected'],'assessment':assessment,'decision':'block' if why else ('keep' if assessment=='unchanged' else 'replace'),'base_label':label,'label':label,'reason':why or s['reason'],'refs':refs,'actions':actions,'verification':[],'status':'blocked' if why else 'pending'})
    return refresh({'schema_version':1,'case':c,'revision':digest(c),'steps':out,'final_confirmation':None,'status':'pending'})

def refresh(p):
    final = p['final_confirmation']
    states = [step['status'] for step in p['steps']]
    if 'failed' in states or (final and final['outcome'] == 'failure'):
        p['status'] = 'failed'
    elif 'blocked' in states:
        p['status'] = 'blocked'
    elif final:
        p['status'] = 'verified' if final['actor'] == 'user' else 'simulated'
    elif all(state in ('verified', 'simulated') for state in states):
        p['status'] = 'awaiting_final'
    else:
        p['status'] = 'pending'
    return p

def apply(p, f):
    obj(f,('revision','environment','step_id','action_index','actor','outcome','expected_met','note','date'))
    require(f['revision']==p['revision'],'Stale revision'); require(env(f['environment'])==p['case']['environment'],'Environment mismatch'); require(known(f['environment']),'Unknown environment')
    actor=enum(f['actor'],('user','simulation'),'actor'); require((p['case']['mode']=='live' and actor=='user') or (p['case']['mode']=='simulation' and actor=='simulation'),'Feedback actor and case mode mismatch; documentary cases cannot be verified')
    outcome=enum(f['outcome'],('success','failure'),'outcome'); met=boolean(f['expected_met'],'expected_met'); text(f['note'],'note'); date(f['date'])
    require(type(f['action_index']) is int,'Invalid action index'); require(not p['final_confirmation'],'Already finalized')
    require(not any(s['status']=='failed' for s in p['steps']),'Prior failure; rebuild with fresh evidence')
    if f['step_id']=='__goal__':
        require(f['action_index']==0 and all(s['status'] in ('verified','simulated') for s in p['steps']),'Complete all steps first')
        require(met == (outcome == 'success'), 'Final outcome and expected state disagree')
        p['final_confirmation'] = f
        return refresh(p)
    ident(f['step_id'],'step_id')
    pending=next((s for s in p['steps'] if s['status'] not in ('verified','simulated')),None)
    require(pending is not None and pending['id']==f['step_id'],'Out of order or unknown step'); require(pending['status']=='pending','Step blocked; rebuild')
    require(f['action_index']==len(pending['verification'])+1 and f['action_index']<=len(pending['actions']),'Wrong action index')
    require(outcome!='success' or met,'Success requires expected state confirmation')
    pending['verification'].append(f)
    if outcome=='failure': pending['status']='failed'; pending['label']='BLOCKED'; pending['reason']='User reported failure; request new evidence and rebuild.'
    elif len(pending['verification'])==len(pending['actions']):
        pending['status']='verified' if actor=='user' else 'simulated'; pending['label']='VERIFIED' if actor=='user' else pending['base_label']
    return refresh(p)

def validate_patch(p):
    # Reconstruct from original case and replay validated feedback. Reject edited labels/steps/status.
    obj(p,('schema_version','case','revision','steps','final_confirmation','status'))
    require(p['schema_version']==1,'Unsupported schema'); rebuilt=refresh(build(p['case']))
    require(p['revision']==rebuilt['revision'],'Revision mismatch')
    for s in arr(p['steps'],'patch steps',30):
        require(isinstance(s,dict) and 'verification' in s,'Invalid patch step')
        for f in arr(s['verification'],'verification',8): apply(rebuilt,f)
    if p['final_confirmation'] is not None: apply(rebuilt,p['final_confirmation'])
    require(rebuilt==p,'Patch differs from reconstructed state; possible tampering')
    return rebuilt

def next_prompt(p):
    """Return one actionable node, an evidence request, or the terminal result."""
    p = validate_patch(p)
    state = p['status']
    mode = p['case']['mode']
    common = {'revision': p['revision'], 'environment': p['case']['environment'],
              'mode': mode, 'status': state}
    if state == 'failed':
        record = p['final_confirmation'] or next(s['verification'][-1] for s in p['steps'] if s['status'] == 'failed')
        return dict(common, kind='stopped', step_id=record['step_id'], action_index=record['action_index'],
                    message='本次核验失败，请补充该位置的界面或结果，保留本修订后重新诊断。')
    if state in ('verified', 'simulated'):
        return dict(common, kind='complete', goal=p['case']['goal'])
    if state == 'awaiting_final':
        return dict(common, kind='goal', step_id='__goal__', action_index=0, expected=p['case']['goal'])
    step = next(s for s in p['steps'] if s['status'] not in ('verified', 'simulated'))
    if step['decision'] == 'block':
        return dict(common, kind='evidence', step_id=step['id'], reason=step['reason'], detail=step['intent'])
    offset = len(step['verification'])
    return dict(common, kind='preview' if mode == 'documentary' else 'action',
                step_id=step['id'], action_index=offset+1, label=step['label'], **step['actions'][offset])

def search(folder, query):
    obj(query,('environment','goal')); e=env(query['environment']); text(query['goal'],'goal',200); require(known(e),'Cannot reuse unknown environment')
    matches=[]; rejected=0
    for f in sorted(Path(folder).glob('*.json')):
        try:
            p=validate_patch(read(f))
            if p['status']=='verified' and p['case']['environment']==e and p['case']['goal']==query['goal']:
                matches.append({'file':f.name,'revision':p['revision'],'verified_at':p['final_confirmation']['date'],'notice':'Recheck current UI; fresh user verification required.'})
        except (ValueError, OSError, TypeError, KeyError): rejected+=1
    return {'matches':matches,'invalid_records_skipped':rejected}

def md(p, public=False):
    p=validate_patch(p); c=p['case']; e=c['environment']
    def esc(v): return html.escape(str(v)).replace('|','\\|').replace('\n',' ').replace('`','\\`').replace('[','\\[').replace(']','\\]')
    lines=['# GuidePatch | 教程复活师','',f"**目标：** {esc(c['goal'])}",f"**环境：** {' / '.join(esc(e[k]) for k in ENV)}",f"**原版本：** {esc(c['old_version'])}",f"**案例类型：** {c['mode']} · **流程状态：** {p['status']} · **修订：** `{p['revision']}`",'', '本记录仅描述本次证据和反馈；未验证路径不是保证。模拟案例不是用户实测。','', '| 步骤 | 原步骤（摘要） | 决策 | 证据标签 | 验证 |','|---|---|---|---|---|']
    for s in p['steps']: lines.append('| '+' | '.join(esc(v) for v in [s['id'],s['original'],s['decision'],s['label'],s['status']])+' |')
    lines.extend(['','## 最小修复与核验'])
    stopped = False
    for s in p['steps']:
        if stopped:
            lines.extend(['',f"### {esc(s['id'])} · {esc(s['intent'])}",'- 前序步骤中断，此步骤等待重新诊断。'])
            continue
        lines.extend(['',f"### {esc(s['id'])} · {esc(s['intent'])}",f"- 前提：{esc(s['precondition'])}",f"- 原因：{esc(s['reason'])}" if not public else f"- 决策：{s['decision']}"])
        if s['status']=='failed' or s['decision']=='block':
            stopped = True
            lines.append('- 已暂停。请补充当前界面与预期结果。')
        elif s['decision']=='keep': lines.append('- 保留原步骤，不改写。')
        else:
            for i,a in enumerate(s['actions'],1): lines.append(f"- {i}. {esc(a['action'])} → {esc(a['expected'])}（证据：{', '.join(a['refs'])}）")
        if not public:
            for f in s['verification']: lines.append(f"- 核验 {f['action_index']}：{f['outcome']} / {f['actor']} / {f['date']} — {esc(f['note'])}")
    lines.extend(['','## 证据与来源',f"- 原教程来源：{esc(c['origin'])}"])
    for s in c['sources']:
        if public and s['kind']!='official': continue
        lines.append(f"- {s['id']} ({s['kind']})：{esc(s['fact'])}"+(f" — {s['url']}" if s['url'] else ''))
    lines.extend(['','## 适用范围','仅限上述环境。版本、系统、语言、扩展或配置变化时重新核验；公开前检查隐私、版权、来源授权。'])
    if p['final_confirmation']:
        f = p['final_confirmation']
        result = '达成' if f['outcome'] == 'success' else '未达成，等待重新诊断'
        lines.append(f"最终目标记录 {f['date']}（{f['actor']}） · {result}")
        if not public: lines.append('反馈 '+esc(f['note']))
    return '\n'.join(lines)+'\n'
