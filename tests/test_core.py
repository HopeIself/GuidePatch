import copy, json, sys, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'scripts'))
from core import *
CASES={c['case_id']:c for c in json.loads((ROOT/'examples/cases.json').read_text(encoding='utf-8'))}
def get(name='partial_change'): return copy.deepcopy(CASES[name])
def live(): c=get(); c['mode']='live'; return c
def feedback(p,step='step_01',i=1,actor=None,outcome='success',met=True):
 return dict(revision=p['revision'],environment=p['case']['environment'],step_id=step,action_index=i,actor=actor or ('simulation' if p['case']['mode']=='simulation' else 'user'),outcome=outcome,expected_met=met,note='Synthetic test assertion: expected state observed',date='2026-11-24')
def complete(p):
 for s in p['steps']:
  for i in range(1,len(s['actions'])+1): apply(p,feedback(p,s['id'],i))
 return apply(p,feedback(p,'__goal__',0))
class Tests(unittest.TestCase):
 def test_cases(self):
  for c in CASES.values():
   with self.subTest(c=c['case_id']): validate_patch(build(c))
 def test_partial(self): self.assertEqual([s['decision'] for s in build(get())['steps']],['keep','replace'])
 def test_unchanged(self): self.assertEqual(build(get('unchanged'))['steps'][0]['decision'],'keep')
 def test_all_changed(self): self.assertEqual(build(get('all_changed'))['steps'][0]['decision'],'replace')
 def test_no_evidence(self): self.assertEqual(build(get('insufficient'))['steps'][0]['actions'],[])
 def test_removed(self): self.assertEqual(build(get('removed'))['status'],'blocked')
 def test_risk(self): self.assertEqual(build(get('risk'))['steps'][0]['actions'],[])
 def test_conflict(self): self.assertEqual(build(get('conflict'))['status'],'blocked')
 def test_unknown_version(self): self.assertEqual(build(get('version_unknown'))['status'],'blocked')
 def test_doc(self): self.assertEqual(build(get('vscode_127'))['steps'][0]['label'],'DOCUMENTED')
 def test_doc_unknown(self): self.assertEqual(build(get('chrome_downloads'))['status'],'blocked')
 def test_candidate_no_refs(self): c=get(); c['steps'][1]['candidate'][0]['refs']=[]; self.assertEqual(build(c)['steps'][1]['label'],'BLOCKED')
 def test_unref(self): c=get(); c['steps'][1]['refs']=['made_up']; self.assertRaises(Invalid,build,c)
 def test_unreviewed(self): c=get(); c['sources'][0]['reviewed']=False; self.assertEqual(build(c)['steps'][0]['label'],'BLOCKED')
 def test_scope(self): c=get(); c['sources'][0]['scope']=dict(c['environment'],version='3.0'); self.assertEqual(build(c)['steps'][0]['label'],'BLOCKED')
 def test_goal_mismatch(self): c=get(); c['steps'][1]['goal_preserved']=False; self.assertEqual(build(c)['steps'][1]['label'],'BLOCKED')
 def test_duplicate_id(self): c=get(); c['steps'].append(c['steps'][0]); self.assertRaises(Invalid,build,c)
 def test_duplicate_source(self): c=get(); c['sources'].append(c['sources'][0]); self.assertRaises(Invalid,build,c)
 def test_unknown_field(self): c=get(); c['raw_screenshot']='xyz'; self.assertRaises(Invalid,build,c)
 def test_private(self): c=get(); c['goal']='password: secret'; self.assertRaises(Invalid,build,c)
 def test_email(self): c=get(); c['origin']='me@example.com'; self.assertRaises(Invalid,build,c)
 def test_invalid_source_url(self): c=get('vscode_127'); c['sources'][1]['url']='http://code.visualstudio.com'; self.assertRaises(Invalid,build,c)
 def test_bad_bool(self): c=get(); c['steps'][0]['conflict']='false'; self.assertRaises(Invalid,build,c)
 def test_mixed_sim_user(self): p=build(get()); self.assertRaises(Invalid,apply,p,feedback(p,actor='user'))
 def test_doc_feedback_rejected(self): p=build(get('vscode_127')); self.assertRaises(Invalid,apply,p,feedback(p))
 def test_simulated_no_verified(self): p=complete(build(get())); self.assertEqual(p['status'],'simulated'); self.assertNotIn('VERIFIED',[s['label'] for s in p['steps']]); validate_patch(p)
 def test_live_state_machine_fixture(self): p=complete(build(live())); self.assertEqual(p['status'],'verified'); self.assertTrue(all(s['label']=='VERIFIED' for s in p['steps'])); validate_patch(p)
 def test_order(self): p=build(get()); self.assertRaises(Invalid,apply,p,feedback(p,'step_02'))
 def test_action_order(self): p=build(get()); apply(p,feedback(p)); self.assertRaises(Invalid,apply,p,feedback(p,'step_02',2))
 def test_partial_not_verified(self): p=build(live()); apply(p,feedback(p)); apply(p,feedback(p,'step_02')); self.assertEqual(p['steps'][1]['label'],'INFERRED')
 def test_goal_early(self): p=build(get()); self.assertRaises(Invalid,apply,p,feedback(p,'__goal__',0))
 def test_goal_separate(self): p=build(live()); apply(p,feedback(p)); apply(p,feedback(p,'step_02',1)); apply(p,feedback(p,'step_02',2)); self.assertEqual(p['status'],'awaiting_final')
 def test_failure(self): p=build(get()); apply(p,feedback(p,outcome='failure',met=False)); self.assertEqual(p['status'],'failed'); self.assertRaises(Invalid,apply,p,feedback(p)); validate_patch(p)
 def test_met(self): p=build(get()); self.assertRaises(Invalid,apply,p,feedback(p,met=False))
 def test_stale_revision(self): p=build(get()); f=feedback(p); f['revision']='stale'; self.assertRaises(Invalid,apply,p,f)
 def test_env_mismatch(self): p=build(get()); f=feedback(p); f['environment']=dict(f['environment'],version='3'); self.assertRaises(Invalid,apply,p,f)
 def test_date(self): p=build(get()); f=feedback(p); f['date']='2026-02-30'; self.assertRaises(Invalid,apply,p,f)
 def test_blocked(self): p=build(get('insufficient')); self.assertRaises(Invalid,apply,p,feedback(p))
 def test_tamper_label(self): p=build(get()); p['steps'][0]['label']='VERIFIED'; self.assertRaises(Invalid,validate_patch,p)
 def test_tamper_path(self): p=build(get()); p['steps'][0]['actions'][0]['action']='invented'; self.assertRaises(Invalid,validate_patch,p)
 def test_tamper_revision(self): p=build(get()); p['case']['goal']='changed'; self.assertRaises(Invalid,validate_patch,p)
 def test_private_export(self): p=complete(build(get())); self.assertIn('Synthetic test assertion',md(p)); self.assertNotIn('Synthetic test assertion',md(p,True)); self.assertNotIn('模拟：主页',md(p,True))
 def test_public_html_escape(self): c=get(); c['goal']='<script>alert(1)</script>'; self.assertIn('&lt;script&gt;',md(build(c),True))
 def test_history(self):
  with tempfile.TemporaryDirectory() as d:
   write(Path(d)/'fixture.json',complete(build(live()))); write(Path(d)/'sim.json',complete(build(get()))); write(Path(d)/'pending.json',build(live())); q={'environment':live()['environment'],'goal':live()['goal']}; self.assertEqual(len(search(d,q)['matches']),1); q['environment']=dict(q['environment'],version='3'); self.assertEqual(search(d,q)['matches'],[])
 def test_history_invalid(self):
  with tempfile.TemporaryDirectory() as d:
   write(Path(d)/'bad.json',{'bad':True}); self.assertEqual(search(d,{'environment':live()['environment'],'goal':live()['goal']})['invalid_records_skipped'],1)
 def test_duplicates_json(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'x.json';p.write_text('{"a":1,"a":2}');self.assertRaises(Invalid,read,p)
 def test_reserved_id(self): c=get(); c['steps'][0]['id']='__goal__';self.assertRaises(Invalid,build,c)
 def test_no_replacement_unchanged(self): c=get(); c['steps'][0]['candidate']=c['steps'][1]['candidate'];self.assertRaises(Invalid,build,c)
if __name__=='__main__':unittest.main()
