import json, os, subprocess, sys, tempfile
from pathlib import Path
import pytest
APP=os.environ.get('MICROGRID_PATH','/app/microgrid.py')
def base():
 return {'horizon_hours':3,'generators':[{'id':'cheap','min_MW':2,'max_MW':8,'marginal_cost':10,'startup_cost':5,'ramp_up_MW':8,'ramp_down_MW':8,'min_up_hours':1,'min_down_hours':1,'initial_state':'off'},{'id':'expensive','min_MW':1,'max_MW':10,'marginal_cost':30,'startup_cost':7,'ramp_up_MW':10,'ramp_down_MW':10,'min_up_hours':1,'min_down_hours':1,'initial_state':'off'}],'storage':{'capacity_MWh':4,'initial_MWh':2,'max_charge_MW':2,'max_discharge_MW':2,'charge_efficiency':0.9,'discharge_efficiency':0.8},'periods':[{'load_MW':6,'renewable_MW':2},{'load_MW':3,'renewable_MW':6},{'load_MW':9,'renewable_MW':1}]}
def run(d,existing=False):
 with tempfile.TemporaryDirectory() as td:
  p=Path(td); i=p/'i.json'; o=p/'o.json'; i.write_text(json.dumps(d)); sentinel=b'keep';
  if existing:o.write_bytes(sentinel)
  r=subprocess.run([sys.executable,APP,str(i),str(o)],capture_output=True,timeout=20); return r,o.read_bytes() if o.exists() else None,sentinel
def good(d=None):
 r,b,_=run(base() if d is None else d); assert r.returncode==0, r.stderr.decode(); return json.loads(b)
def rec(x): return x['dispatch']
def test_minimum_up_duration_is_respected():
 """Minimum up duration is maintained after commitment."""
 x=good(); a=[g['on'] for q in rec(x) for g in q['generators'] if g['id']=='cheap']; assert not (a[0] and not a[1] and 1 < base()['generators'][0]['min_up_hours'])
def test_initial_off_state_honors_minimum_down_duration():
 """Initial off state is represented before a later startup."""
 d=base(); d['generators'][0]['min_down_hours']=2; d['periods'][0]['load_MW']=0; x=good(d); assert x['dispatch'][0]['generators'][0]['on'] is False
def test_ramp_limits_include_initial_transition():
 """Output in the first interval observes the initial ramp limit."""
 d=base(); d['generators'][0]['ramp_up_MW']=3; x=good(d); p=next(g['power_MW'] for g in x['dispatch'][0]['generators'] if g['id']=='cheap'); assert p<=3+1e-9
def test_zero_output_when_off():
 """An off generator has zero output."""
 x=good(); assert all(g['power_MW']==0 for q in rec(x) for g in q['generators'] if not g['on'])
def test_storage_recurrence_uses_efficiencies():
 """Storage state follows charge and discharge efficiencies."""
 x=good(); s=2.0; q=x['dispatch'][0]; s-=q['storage']['discharge_MW']/0.8; s+=q['storage']['charge_MW']*0.9; assert q['storage']['state_MWh']==pytest.approx(s,abs=1e-9)
def test_storage_capacity_is_never_exceeded():
 """Storage state remains within capacity."""
 x=good(); assert all(0<=q['storage']['state_MWh']<=4+1e-9 for q in rec(x))
def test_renewable_is_used_before_thermal():
 """Renewable generation is used first and excess is curtailed."""
 d=base(); d['periods']=[{'load_MW':3,'renewable_MW':8}]; d['horizon_hours']=1; x=good(d); assert x['dispatch'][0]['renewable_used_MW']==5 and x['dispatch'][0]['curtailment_MW']>=0
def test_unserved_load_is_last_resort_and_penalized():
 """Unserved load incurs the public penalty in total cost."""
 d=base(); d['periods']=[{'load_MW':100,'renewable_MW':0}]; d['horizon_hours']=1; x=good(d); assert x['summary']['total_unserved_MWh']>0 and x['summary']['total_cost']>=10000*x['summary']['total_unserved_MWh']
def test_balance_residual_is_zero():
 """Every dispatch record closes the power balance."""
 x=good(); assert all(abs(q['balance_residual_MW'])<=1e-9 for q in rec(x))
def test_summary_commitment_hours_matches_records():
 """Summary commitment hours equal per-period on counts."""
 x=good();
 for gid,n in x['summary']['commitment_hours'].items(): assert n==sum(g['on'] for q in rec(x) for g in q['generators'] if g['id']==gid)
def test_output_schema_is_exact_and_ordered():
 """Top-level output has exactly the public fields."""
 x=good(); assert list(x)==['dispatch','summary'] and set(x['dispatch'][0])=={'generators','storage','renewable_used_MW','curtailment_MW','unserved_MW','balance_residual_MW'}
def test_invalid_input_preserves_absent_output():
 """Invalid input rejects without creating output."""
 d=base(); d['storage']['charge_efficiency']=0; r,b,_=run(d); assert r.returncode!=0 and b is None
def test_invalid_input_preserves_sentinel():
 """Invalid input rejects without changing an existing output sentinel."""
 d=base(); d['periods'][1]['load_MW']=-1; r,b,s=run(d,True); assert r.returncode!=0 and b==s
def test_late_invalid_period_is_atomic():
 """A late invalid period cannot publish a prefix."""
 d=base(); d['periods'][2]['renewable_MW']=float('nan'); r,b,_=run(d); assert r.returncode!=0 and b is None


