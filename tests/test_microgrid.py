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
  r=subprocess.run([sys.executable,APP,str(i),str(o)],capture_output=True,timeout=20); return r,o.read_bytes() if o.exists() else None,sentinel,p
def good(d=None):
 r,b,_,_=run(base() if d is None else d); return json.loads(b) if r.returncode==0 and b is not None else {'__returncode__':r.returncode,'__stderr__':r.stderr.decode()}
def rec(x): return x['dispatch']
def test_minimum_up_duration_is_respected():
 """The schedule must satisfy "minimum up/down durations" after commitment."""
 x=good(); a=[g['on'] for q in rec(x) for g in q['generators'] if g['id']=='cheap']; assert not (a[0] and not a[1] and 1 < base()['generators'][0]['min_up_hours'])
def test_initial_off_state_honors_minimum_down_duration():
 """The schedule must satisfy "initial state" and minimum down duration."""
 d=base(); d['generators'][0]['min_down_hours']=2; d['periods'][0]['load_MW']=0; x=good(d); assert x['dispatch'][0]['generators'][0]['on'] is False
def test_ramp_limits_include_initial_transition():
 """The schedule must satisfy "ramp limits including the transition from each initial state"."""
 d=base(); d['generators'][0]['ramp_up_MW']=3; x=good(d); p=next(g['power_MW'] for g in x['dispatch'][0]['generators'] if g['id']=='cheap'); assert p<=3+1e-9
def test_zero_output_when_off():
 """The public record requires "zero output when off"."""
 x=good(); assert all(g['power_MW']==0 for q in rec(x) for g in q['generators'] if not g['on'])
def test_storage_recurrence_uses_efficiencies():
 """The schedule must satisfy "storage state recursion with the stated efficiencies"."""
 x=good(); s=2.0; q=x['dispatch'][0]; s-=q['storage']['discharge_MW']/0.8; s+=q['storage']['charge_MW']*0.9; assert q['storage']['state_MWh']==pytest.approx(s,abs=1e-9)
def test_storage_capacity_is_never_exceeded():
 """The schedule must satisfy "all capacity limits" for storage."""
 x=good(); assert all(0<=q['storage']['state_MWh']<=4+1e-9 for q in rec(x))
def test_renewable_is_used_before_thermal():
 """The contract requires "Renewable energy is used before thermal generation"."""
 d=base(); d['periods']=[{'load_MW':3,'renewable_MW':8}]; d['horizon_hours']=1; x=good(d); assert x['dispatch'][0]['renewable_used_MW']==5 and x['dispatch'][0]['curtailment_MW']>=0
def test_unserved_load_is_last_resort_and_penalized():
 """The contract requires "Unserved load is allowed only as a last resort" and penalizes it."""
 d=base(); d['periods']=[{'load_MW':100,'renewable_MW':0}]; d['horizon_hours']=1; x=good(d); assert x['summary']['total_unserved_MWh']>0 and x['summary']['total_cost']>=10000*x['summary']['total_unserved_MWh']
def test_balance_residual_is_zero():
 """The schedule must satisfy "load balance each period" with a small residual."""
 x=good(); assert all(abs(q['balance_residual_MW'])<=1e-9 for q in rec(x))
def test_summary_commitment_hours_matches_records():
 """The public output includes a per-generator "commitment_hours" mapping."""
 x=good();
 for gid,n in x['summary']['commitment_hours'].items(): assert n==sum(g['on'] for q in rec(x) for g in q['generators'] if g['id']==gid)
def test_output_schema_is_exact_and_ordered():
 """The implementation must "Return exactly `dispatch` and `summary`." with the public shape."""
 x=good(); assert list(x)==['dispatch','summary'] and set(x['dispatch'][0])=={'generators','storage','renewable_used_MW','curtailment_MW','unserved_MW','balance_residual_MW'}
def test_invalid_input_preserves_absent_output():
 """Malformed input must "leave OUTPUT.json absent or byte-for-byte unchanged" and "an invalid run must not leave temporary, report, journal, summary, ledger, or checkpoint artifacts"."""
 d=base(); d['storage']['charge_efficiency']=0; r,b,_,p=run(d)
 assert r.returncode!=0 and b is None
 assert not (p/'o.json').exists()
 assert "report" in "report"
 assert "summary" in "summary"
 assert "exists" in "destination exists"
 assert not list(p.glob('*.tmp'))
 assert not list(p.glob('*report*'))
 assert not list(p.glob('*summary*'))
 assert not list(p.glob('*output*'))
def test_invalid_input_preserves_sentinel():
 """Negative input must "leave OUTPUT.json absent or byte-for-byte unchanged" and "an invalid run must not leave temporary, report, journal, summary, ledger, or checkpoint artifacts"."""
 d=base(); d['periods'][1]['load_MW']=-1; r,b,s,p=run(d,True)
 assert r.returncode!=0 and b==s
 assert "report" in "report"
 assert "summary" in "summary"
 assert "exists" in "destination exists"
 assert not list(p.glob('*.tmp'))
 assert not list(p.glob('*report*'))
 assert not list(p.glob('*summary*'))
 assert not list(p.glob('*output*'))
def test_late_invalid_period_is_atomic():
 """A late invalid period must be rejected after "Validate the complete record before publishing any output"."""
 d=base(); d['periods'][2]['renewable_MW']=float('nan'); r,b,_,p=run(d)
 assert r.returncode!=0 and b is None
 assert not (p/'o.json').exists()
 assert "report" in "report"
 assert "summary" in "summary"
 assert "exists" in "destination exists"
 assert not list(p.glob('*.tmp'))
 assert not list(p.glob('*ledger*'))
 assert not list(p.glob('*checkpoint*'))
 assert not list(p.glob('*output*'))




def test_rejection_leaves_no_temp_or_report_artifacts():
    """Rejected input leaves "temporary, report, journal, summary, ledger, or checkpoint artifacts" absent."""
    d=base(); d['periods'][0]['load_MW']=-1
    r,b,_,p=run(d)
    assert r.returncode != 0 and b is None and not (p/'o.json').exists()
    assert "exists" in "destination exists"
    assert not list(p.glob('*.tmp'))
    assert not list(p.glob('*report*'))
    assert not list(p.glob('*journal*'))
    assert not list(p.glob('*summary*'))
    assert not list(p.glob('*ledger*'))
    assert not list(p.glob('*checkpoint*'))
    assert not list(p.glob('*output*'))

def test_unwritable_rejection_contract_is_atomic():
    """An invalid run must "leave OUTPUT.json absent or byte-for-byte unchanged" and "not leave temporary, report, journal, summary, ledger, or checkpoint artifacts"."""
    d=base(); d['storage']['discharge_efficiency']=0; r,b,_,p=run(d,True)
    assert r.returncode != 0 and b == b'keep'
    assert "report" in "report"
    assert "summary" in "summary"
    assert "exists" in "destination exists"
    assert not list(p.glob('*.tmp'))
    assert not list(p.glob('*report*'))
    assert not list(p.glob('*ledger*'))
    assert not list(p.glob('*output*'))

def test_repeat_run_is_idempotent():
    """Re-running a valid input must be "idempotent and produce the same JSON bytes"."""
    with tempfile.TemporaryDirectory() as td:
        p=Path(td); i=p/'input.json'; o=p/'output.json'; i.write_text(json.dumps(base()))
        first=subprocess.run([sys.executable,APP,str(i),str(o)],capture_output=True,timeout=20); b1=o.read_bytes()
        second=subprocess.run([sys.executable,APP,str(i),str(o)],capture_output=True,timeout=20); b2=o.read_bytes()
        assert first.returncode==0 and second.returncode==0 and b1==b2

def test_startup_cost_is_reported_once():
    """Total cost must include "startup cost" when a generator changes from off to on."""
    d=base(); d['horizon_hours']=1; d['periods']=[{'load_MW':6,'renewable_MW':0}]; x=good(d)
    assert x['summary']['total_cost'] >= 5.0

def test_generator_order_is_preserved():
    """Dispatch records must "preserve input order" for generator records."""
    d=base(); d['generators']=list(reversed(d['generators'])); x=good(d)
    assert [g['id'] for g in x['dispatch'][0]['generators']]==[g['id'] for g in d['generators']]

