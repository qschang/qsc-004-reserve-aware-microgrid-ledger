import json, os, subprocess, sys, tempfile
from pathlib import Path
import pytest
import re
APP=os.environ.get('MICROGRID_PATH','/app/microgrid.py')

@pytest.fixture(autouse=True)
def emit_case_id(request):
    doc = request.function.__doc__ or ''
    match = re.search(r'CASE-QSC004-[A-Z0-9-]+', doc)
    if match:
        print(match.group(0))

def base():
 return {'horizon_hours':3,'reserve_MW':0,'generators':[{'id':'cheap','min_MW':2,'max_MW':8,'marginal_cost':10,'startup_cost':5,'ramp_up_MW':8,'ramp_down_MW':8,'min_up_hours':1,'min_down_hours':1,'initial_state':'off'},{'id':'expensive','min_MW':1,'max_MW':10,'marginal_cost':30,'startup_cost':7,'ramp_up_MW':10,'ramp_down_MW':10,'min_up_hours':1,'min_down_hours':1,'initial_state':'off'}],'storage':{'capacity_MWh':4,'initial_MWh':2,'max_charge_MW':2,'max_discharge_MW':2,'charge_efficiency':0.9,'discharge_efficiency':0.8},'periods':[{'load_MW':6,'renewable_MW':2},{'load_MW':3,'renewable_MW':6},{'load_MW':9,'renewable_MW':1}]}
def run(d,existing=False):
 with tempfile.TemporaryDirectory() as td:
  p=Path(td); i=p/'i.json'; o=p/'o.json'; i.write_text(json.dumps(d)); sentinel=b'keep';
  if existing:o.write_bytes(sentinel)
  r=subprocess.run([sys.executable,APP,str(i),str(o)],capture_output=True,timeout=20)
  output_bytes=o.read_bytes() if o.exists() else None
  observed={'output_exists':o.exists(),'output_bytes':output_bytes,'temporary_files':sorted(x.name for x in p.glob('*.tmp'))}
  return r,output_bytes,sentinel,observed
def run_raw(raw,existing=False):
 with tempfile.TemporaryDirectory() as td:
  p=Path(td); i=p/'i.json'; o=p/'o.json'; i.write_text(raw,encoding='utf-8'); sentinel=b'keep'
  if existing:o.write_bytes(sentinel)
  r=subprocess.run([sys.executable,APP,str(i),str(o)],capture_output=True,timeout=20)
  output_bytes=o.read_bytes() if o.exists() else None
  observed={'output_exists':o.exists(),'output_bytes':output_bytes,'temporary_files':sorted(x.name for x in p.glob('*.tmp'))}
  return r,output_bytes,sentinel,observed
def good(d=None):
 r,b,_,_=run(base() if d is None else d); return json.loads(b) if r.returncode==0 and b is not None else {'__returncode__':r.returncode,'__stderr__':r.stderr.decode()}
def rec(x): return x['dispatch']
def test_minimum_up_duration_is_respected():
 '''CASE-QSC004-MIN-UP: "Apply the minimum up/down duration from that point, including the first hour."'''
 d=base(); d['generators'][0]['min_up_hours']=2; d['generators'][0]['min_down_hours']=0; d['periods']=[{'load_MW':6,'renewable_MW':0},{'load_MW':0,'renewable_MW':0},{'load_MW':0,'renewable_MW':0}]; d['horizon_hours']=3
 x=good(d); a=[g['on'] for q in rec(x) for g in q['generators'] if g['id']=='cheap']; assert a[0] is True and a[1] is True
def test_must_run_output_is_reserved_before_merit_dispatch():
 '''CASE-QSC004-MUST-RUN-BALANCE: "First reserve each must-run unit at its minimum feasible output for the hour".'''
 d=base(); d['generators'][0].update({'min_MW':0,'max_MW':6,'marginal_cost':1,'min_up_hours':0,'min_down_hours':0}); d['generators'][1].update({'min_MW':2,'max_MW':10,'marginal_cost':30,'min_up_hours':2,'min_down_hours':0}); d['horizon_hours']=2; d['periods']=[{'load_MW':10,'renewable_MW':0},{'load_MW':6,'renewable_MW':0}]; d['storage'].update({'capacity_MWh':0,'initial_MWh':0,'max_charge_MW':0,'max_discharge_MW':0}); x=good(d); q=x['dispatch'][1]
 assert {g['id']:g['power_MW'] for g in x['dispatch'][0]['generators']}=={'cheap':6,'expensive':4}
 assert {g['id']:g['power_MW'] for g in q['generators']}=={'cheap':4,'expensive':2}
 assert q['unserved_MW']==0 and q['storage']['discharge_MW']>=0 and abs(q['balance_residual_MW'])<=1e-9
def test_merit_ties_use_generator_id_without_changing_output_order():
 '''CASE-QSC004-TIE-ORDER: "Then allocate the remaining deficit in merit order by `(marginal_cost, id)` across all already-on and startable units, including must-run units that have room to increase."'''
 d=base(); d['generators']=list(reversed(d['generators']))
 for g in d['generators']: g.update({'min_MW':0,'max_MW':5,'marginal_cost':10,'startup_cost':0,'ramp_up_MW':5,'ramp_down_MW':5,'min_up_hours':0,'min_down_hours':0,'initial_state':'off'})
 d['horizon_hours']=1; d['periods']=[{'load_MW':3,'renewable_MW':0}]; d['storage'].update({'capacity_MWh':0,'initial_MWh':0,'max_charge_MW':0,'max_discharge_MW':0})
 q=good(d)['dispatch'][0]
 assert [g['id'] for g in q['generators']]==['expensive','cheap']
 assert {g['id']:g['power_MW'] for g in q['generators']}=={'cheap':3,'expensive':0}
def test_startup_cost_does_not_change_merit_order():
 '''CASE-QSC004-STARTUP-NOT-OBJECTIVE: "This cost is a reported ledger value, not a dispatch optimization objective."'''
 d=base(); d['generators']=d['generators'][:2]
 d['generators'][0].update({'id':'cheap','min_MW':0,'max_MW':5,'marginal_cost':1,'startup_cost':1000,'ramp_up_MW':5,'ramp_down_MW':5,'min_up_hours':0,'min_down_hours':0,'initial_state':'off'})
 d['generators'][1].update({'id':'dear','min_MW':0,'max_MW':5,'marginal_cost':2,'startup_cost':0,'ramp_up_MW':5,'ramp_down_MW':5,'min_up_hours':0,'min_down_hours':0,'initial_state':'off'})
 d['horizon_hours']=1; d['periods']=[{'load_MW':4,'renewable_MW':0}]; d['storage'].update({'capacity_MWh':0,'initial_MWh':0,'max_charge_MW':0,'max_discharge_MW':0})
 x=good(d); q=x['dispatch'][0]
 assert {g['id']:g['power_MW'] for g in q['generators']}=={'cheap':4,'dear':0}
 assert x['summary']['total_cost']==pytest.approx(1004,abs=1e-9)
def test_must_run_surplus_uses_storage_capacity():
 '''CASE-QSC004-MUST-RUN-CHARGE: "A must-run thermal minimum that exceeds the deficit may be absorbed by available storage charging capacity".'''
 d=base(); d['generators']=d['generators'][:1]; d['generators'][0].update({'min_MW':2,'max_MW':2,'min_up_hours':1,'min_down_hours':0,'initial_state':'on'}); d['horizon_hours']=1; d['periods']=[{'load_MW':0,'renewable_MW':0}]; d['storage'].update({'capacity_MWh':2,'initial_MWh':0,'max_charge_MW':2,'max_discharge_MW':0}); q=good(d)['dispatch'][0]
 assert q['generators'][0]['power_MW']==2 and q['storage']['charge_MW']==2 and q['storage']['state_MWh']==pytest.approx(1.8,abs=1e-9)
 assert q['unserved_MW']==0 and abs(q['balance_residual_MW'])<=1e-9
def test_unabsorbable_must_run_surplus_is_rejected_atomically():
 '''CASE-QSC004-MUST-RUN-INFEASIBLE: "if the resulting surplus cannot be absorbed while satisfying the storage limits, reject the input as infeasible and preserve the output path."'''
 d=base(); d['generators']=d['generators'][:1]; d['generators'][0].update({'min_MW':2,'max_MW':2,'min_up_hours':1,'min_down_hours':0,'initial_state':'on'}); d['horizon_hours']=1; d['periods']=[{'load_MW':0,'renewable_MW':0}]; d['storage'].update({'capacity_MWh':0,'initial_MWh':0,'max_charge_MW':0,'max_discharge_MW':0})
 for existing in (False,True):
  r,b,s,observed=run(d,existing)
  assert r.returncode!=0
  assert b==s if existing else b is None
  assert observed['output_exists'] is existing and observed['temporary_files']==[]
def test_reserve_report_handles_each_single_unit_outage():
 '''CASE-QSC004-N1-RESERVE: "For each online generator in turn, treat that unit as unavailable and sum the remaining online-generator reserve plus storage reserve."'''
 d=base(); d['generators']=[{'id':'beta','min_MW':2,'max_MW':6,'marginal_cost':10,'startup_cost':0,'ramp_up_MW':6,'ramp_down_MW':6,'min_up_hours':1,'min_down_hours':0,'initial_state':'on'},{'id':'alpha','min_MW':2,'max_MW':6,'marginal_cost':20,'startup_cost':0,'ramp_up_MW':6,'ramp_down_MW':6,'min_up_hours':1,'min_down_hours':0,'initial_state':'on'}]
 d['horizon_hours']=1; d['reserve_MW']=4.5; d['periods']=[{'load_MW':4,'renewable_MW':0}]; d['storage'].update({'capacity_MWh':1,'initial_MWh':1,'max_charge_MW':0,'max_discharge_MW':2})
 r=good(d)['dispatch'][0]['reserve']
 assert r['required_MW']==pytest.approx(4.5,abs=1e-9)
 assert r['available_MW']==pytest.approx(4.8,abs=1e-9)
 assert r['limiting_outage_id']=='alpha'
def test_storage_alone_supplies_reserve_when_all_generators_are_off():
 '''CASE-QSC004-RESERVE-STORAGE-ONLY: "If no generator is online, `available_MW` is storage reserve alone and `limiting_outage_id` is `null`."'''
 d=base(); d['generators']=[d['generators'][0]]; d['generators'][0].update({'min_MW':1,'max_MW':4,'initial_state':'off','min_up_hours':0,'min_down_hours':0}); d['horizon_hours']=1; d['reserve_MW']=1.2; d['periods']=[{'load_MW':0,'renewable_MW':0}]; d['storage'].update({'capacity_MWh':2,'initial_MWh':1.5,'max_charge_MW':0,'max_discharge_MW':2})
 r=good(d)['dispatch'][0]['reserve']
 assert r['required_MW']==pytest.approx(1.2,abs=1e-9) and r['available_MW']==pytest.approx(1.2,abs=1e-9) and r['limiting_outage_id'] is None
def test_storage_contingency_reserve_is_limited_by_energy_and_efficiency():
 '''CASE-QSC004-RESERVE-STORAGE-ENERGY: "Storage contributes `min(max_discharge_MW - discharge_MW, state_MWh * discharge_efficiency)` MW."'''
 d=base(); d['generators']=d['generators'][:1]; d['generators'][0].update({'min_MW':2,'max_MW':2,'initial_state':'on','min_up_hours':1,'min_down_hours':0}); d['horizon_hours']=1; d['reserve_MW']=0.5; d['periods']=[{'load_MW':2,'renewable_MW':0}]; d['storage'].update({'capacity_MWh':1,'initial_MWh':1,'max_charge_MW':0,'max_discharge_MW':2})
 r=good(d)['dispatch'][0]['reserve']
 assert r['available_MW']==pytest.approx(0.8,abs=1e-9) and r['limiting_outage_id']=='cheap'
 d['storage']['initial_MWh']=0.5
 for existing in (False,True):
  proc,b,s,observed=run(d,existing)
  assert proc.returncode!=0
  assert b==s if existing else b is None
  assert observed['output_exists'] is existing and observed['temporary_files']==[]
def test_reserve_shortfall_rejects_atomically():
 '''CASE-QSC004-RESERVE-SHORTFALL: "Reject the complete input atomically if any hour's available reserve is more than `1e-9` MW below `reserve_MW`."'''
 d=base(); d['generators']=d['generators'][:1]; d['generators'][0].update({'min_MW':2,'max_MW':2,'initial_state':'on','min_up_hours':1,'min_down_hours':0}); d['horizon_hours']=1; d['reserve_MW']=0.1; d['periods']=[{'load_MW':2,'renewable_MW':0}]; d['storage'].update({'capacity_MWh':0,'initial_MWh':0,'max_charge_MW':0,'max_discharge_MW':0})
 for existing in (False,True):
  r,b,s,observed=run(d,existing)
  assert r.returncode!=0
  assert b==s if existing else b is None
  assert observed['output_exists'] is existing and observed['temporary_files']==[]
def test_initial_off_state_honors_minimum_down_duration():
 '''CASE-QSC004-MIN-DOWN: "Apply the minimum up/down duration from that point, including the first hour."'''
 d=base(); d['generators'][0]['min_down_hours']=2; d['generators'][1]['initial_state']='on'; d['periods']=[{'load_MW':6,'renewable_MW':0}]; d['horizon_hours']=1; q=good(d)['dispatch'][0]
 assert q['generators'][0]['on'] is False and q['generators'][1]['on'] is True and sum(g['power_MW'] for g in q['generators'])==6
def test_initial_minimum_down_time_expires_after_exact_hours():
 '''CASE-QSC004-INITIAL-DOWN-EXPIRY: "Apply the minimum up/down duration from that point, including the first hour."'''
 d=base(); d['generators']=d['generators'][:1]; d['generators'][0].update({'min_MW':0,'max_MW':5,'ramp_up_MW':5,'ramp_down_MW':5,'min_up_hours':0,'min_down_hours':2,'initial_state':'off'})
 d['horizon_hours']=3; d['periods']=[{'load_MW':5,'renewable_MW':0} for _ in range(3)]; d['storage'].update({'capacity_MWh':0,'initial_MWh':0,'max_charge_MW':0,'max_discharge_MW':0})
 q=good(d)['dispatch']
 assert [x['generators'][0]['on'] for x in q]==[False,False,True]
 assert [x['unserved_MW'] for x in q]==[5,5,0]
def test_ramp_limits_include_initial_transition():
 '''CASE-QSC004-RAMP-INITIAL: "Each hourly commitment must also respect its ramp limits."'''
 d=base(); d['generators'][0]['ramp_up_MW']=3; x=good(d); p=next(g['power_MW'] for g in x['dispatch'][0]['generators'] if g['id']=='cheap'); assert p<=3+1e-9
def test_zero_output_when_off():
 '''CASE-QSC004-OFF-OUTPUT: "A generator that is off must have `power_MW` equal to zero."'''
 x=good(); assert all(g['power_MW']==0 for q in rec(x) for g in q['generators'] if not g['on'])
def test_storage_recurrence_uses_efficiencies():
 '''CASE-QSC004-SOC-RECURRENCE: "Storage state advances by `charge_MW * charge_efficiency - discharge_MW / discharge_efficiency` over each one-hour period."'''
 d=base(); d['generators']=d['generators'][:1]; d['generators'][0].update({'min_MW':0,'max_MW':0,'min_up_hours':0,'min_down_hours':0}); d['periods']=[{'load_MW':0,'renewable_MW':2},{'load_MW':2,'renewable_MW':0}]; d['horizon_hours']=2; x=good(d); state=2.0
 for q in x['dispatch']:
  state+=q['storage']['charge_MW']*0.9-q['storage']['discharge_MW']/0.8
  assert q['storage']['state_MWh']==pytest.approx(state,abs=1e-9)
def test_unit_efficiencies_are_valid_boundary_values():
    '''CASE-QSC004-BOUNDARY-EFFICIENCY: "Each storage efficiency must be greater than zero and at most one."'''
    d=base(); d['storage']['charge_efficiency']=1.0; d['storage']['discharge_efficiency']=1.0
    x=good(d)
    assert 'dispatch' in x
    assert 'summary' in x

def test_storage_capacity_is_never_exceeded():
 '''CASE-QSC004-SOC-CAPACITY: "Every reported storage `state_MWh` must be between zero and `capacity_MWh`, inclusive."'''
 x=good(); assert all(0<=q['storage']['state_MWh']<=4+1e-9 for q in rec(x))
def test_renewable_is_used_before_thermal():
 '''CASE-QSC004-RENEWABLE: "For each hour, renewable energy serves load first."'''
 d=base(); d['periods']=[{'load_MW':3,'renewable_MW':8}]; d['horizon_hours']=1; x=good(d); assert x['dispatch'][0]['renewable_used_MW']==5 and x['dispatch'][0]['curtailment_MW']==3 and sum(g['power_MW'] for g in x['dispatch'][0]['generators'])==0
def test_renewable_surplus_charges_storage_before_curtailment():
 '''CASE-QSC004-SURPLUS-CHARGE: "Use remaining renewable surplus to charge storage within its power and energy limits, then curtail any unused renewable energy."'''
 d=base(); d['periods']=[{'load_MW':3,'renewable_MW':6}]; d['horizon_hours']=1; x=good(d); q=x['dispatch'][0]
 assert q['storage']['charge_MW']==2 and q['storage']['state_MWh']==pytest.approx(3.8,abs=1e-9) and q['curtailment_MW']==1
def test_storage_is_used_before_unserved_load():
 '''CASE-QSC004-STORAGE-LAST-RESORT: "When renewable supply is insufficient, dispatch feasible thermal output in merit order, then discharge available storage within its power and energy limits, and record any remaining deficit as unserved load."'''
 d=base(); d['generators']=d['generators'][:1]; d['generators'][0].update({'min_MW':0,'max_MW':0,'min_up_hours':0,'min_down_hours':0}); d['storage'].update({'capacity_MWh':2,'initial_MWh':2,'max_discharge_MW':2}); d['periods']=[{'load_MW':3,'renewable_MW':1}]; d['horizon_hours']=1; q=good(d)['dispatch'][0]
 assert q['storage']['discharge_MW']==pytest.approx(1.6,abs=1e-9) and q['storage']['state_MWh']==pytest.approx(0,abs=1e-9) and q['unserved_MW']==pytest.approx(0.4,abs=1e-9)
def test_unserved_load_is_last_resort_and_penalized():
 '''CASE-QSC004-UNSERVED: "`unserved_MW * 10000.0`" is included in the reported cost.'''
 d=base(); d['periods']=[{'load_MW':100,'renewable_MW':0}]; d['horizon_hours']=1; x=good(d)
 generation=sum(g['power_MW']*next(v['marginal_cost'] for v in d['generators'] if v['id']==g['id']) for q in x['dispatch'] for g in q['generators'])
 previous={g['id']:g['initial_state']=='on' for g in d['generators']}
 startup=0
 for q in x['dispatch']:
  for g in q['generators']:
   startup+=next(v['startup_cost'] for v in d['generators'] if v['id']==g['id'])*bool(g['on'] and not previous[g['id']])
   previous[g['id']]=g['on']
 assert x['summary']['total_unserved_MWh']>0
 assert x['summary']['total_cost']==pytest.approx(generation+startup+10000*x['summary']['total_unserved_MWh'],abs=1e-9)

def test_cost_ledger_accumulates_generation_startups_and_unserved_energy():
 '''CASE-QSC004-COST-LEDGER: "The `total_cost` summary is exactly the sum over all hours of each generator's `power_MW * marginal_cost`, startup costs for off-to-on transitions, and `unserved_MW * 10000.0`; renewable curtailment has no cost."'''
 d={'horizon_hours':3,'reserve_MW':0,'generators':[{'id':'g','min_MW':2,'max_MW':4,'marginal_cost':3,'startup_cost':7,'ramp_up_MW':4,'ramp_down_MW':4,'min_up_hours':1,'min_down_hours':0,'initial_state':'off'}], 'storage':{'capacity_MWh':0,'initial_MWh':0,'max_charge_MW':0,'max_discharge_MW':0,'charge_efficiency':1,'discharge_efficiency':1}, 'periods':[{'load_MW':3,'renewable_MW':0},{'load_MW':0,'renewable_MW':0},{'load_MW':6,'renewable_MW':0}]}
 x=good(d); rows=x['dispatch']
 assert [row['generators'][0]['on'] for row in rows]==[True,False,True]
 assert [row['unserved_MW'] for row in rows]==pytest.approx([0,0,2],abs=1e-9)
 assert x['summary']['total_cost']==pytest.approx(7+3*3+7+3*4+2*10000,abs=1e-9)
 assert x['summary']['total_unserved_MWh']==pytest.approx(sum(row['unserved_MW'] for row in rows),abs=1e-9)
def test_balance_residual_is_zero():
 '''CASE-QSC004-BALANCE: "For each hour the balance is `renewable_used_MW + sum(generator power_MW) + discharge_MW - charge_MW + unserved_MW = load_MW + balance_residual_MW`."'''
 x=good(); assert all(abs(q['balance_residual_MW'])<=1e-9 for q in rec(x))
def test_summary_commitment_hours_matches_records():
 '''CASE-QSC004-COMMITMENT-SUMMARY: "the last field maps each input generator ID to its number of committed hours."'''
 x=good();
 for gid,n in x['summary']['commitment_hours'].items(): assert n==sum(g['on'] for q in rec(x) for g in q['generators'] if g['id']==gid)
def test_output_schema_is_exact_and_ordered():
 '''CASE-QSC004-OUTPUT-SCHEMA: "Return one UTF-8 JSON object with exactly two top-level keys, in this order: `dispatch`, then `summary`."'''
 x=good(); assert list(x)==['dispatch','summary']
 assert list(x['dispatch'][0])==['generators','storage','reserve','renewable_used_MW','curtailment_MW','unserved_MW','balance_residual_MW']
 assert list(x['dispatch'][0]['storage'])==['charge_MW','discharge_MW','state_MWh']
 assert list(x['dispatch'][0]['reserve'])==['required_MW','available_MW','limiting_outage_id']
 assert all(list(g)==['id','on','power_MW'] for g in x['dispatch'][0]['generators'])
 assert list(x['summary'])==['total_cost','total_unserved_MWh','total_renewable_curtailment_MWh','final_storage_MWh','commitment_hours']
def test_invalid_input_preserves_absent_output():
 '''CASE-QSC004-REJECT-ABSENT: "Reject malformed, non-finite, negative, inconsistent, or horizon-violating inputs with a nonzero exit and leave `OUTPUT.json` absent or byte-for-byte unchanged."'''
 d=base(); d['storage']['charge_efficiency']=0
 for existing in (False,True):
  r,b,s,observed=run(d,existing)
  assert r.returncode!=0
  assert b==s if existing else b is None
  assert observed['output_exists'] is existing
  assert observed['temporary_files'] == []
def test_invalid_input_preserves_sentinel():
 '''CASE-QSC004-REJECT-SENTINEL: "Reject malformed, non-finite, negative, inconsistent, or horizon-violating inputs with a nonzero exit and leave `OUTPUT.json` absent or byte-for-byte unchanged."'''
 d=base(); d['periods'][1]['load_MW']=-1
 for existing in (False,True):
  r,b,s,observed=run(d,existing)
  assert r.returncode!=0
  assert b==s if existing else b is None
  assert observed['output_exists'] is existing
  assert observed['temporary_files'] == []
def test_late_invalid_period_is_atomic():
 '''CASE-QSC004-REJECT-LATE: "Validate the complete record before publishing any output."'''
 d=base(); d['periods'][2]['renewable_MW']=float('nan')
 for existing in (False,True):
  r,b,s,observed=run(d,existing)
  assert r.returncode!=0
  assert b==s if existing else b is None
  assert observed['output_exists'] is existing
  assert observed['temporary_files'] == []




def test_missing_period_field_is_rejected_atomically():
    '''CASE-QSC004-REJECT-SECOND: "Reject malformed, non-finite, negative, inconsistent, or horizon-violating inputs with a nonzero exit and leave `OUTPUT.json` absent or byte-for-byte unchanged."'''
    d=base(); del d['periods'][0]['renewable_MW']
    for existing in (False,True):
        r,b,s,observed=run(d,existing)
        assert r.returncode != 0
        assert b==s if existing else b is None
        assert observed['output_exists'] is existing
        assert observed['temporary_files'] == []

def test_zero_hour_horizon_is_rejected_atomically():
    '''CASE-QSC004-REJECT-ZERO-HORIZON: "`horizon_hours` must be a JSON integer from 1 through 96"'''
    d=base(); d['horizon_hours']=0; d['periods']=[]
    for existing in (False,True):
        r,b,s,observed=run(d,existing)
        assert r.returncode != 0
        assert b==s if existing else b is None
        assert observed['output_exists'] is existing
        assert observed['temporary_files'] == []

def test_empty_generator_set_is_rejected_atomically():
    '''CASE-QSC004-REJECT-EMPTY-GENERATORS: "`generators` must contain at least one unit"'''
    d=base(); d['generators']=[]
    for existing in (False,True):
        r,b,s,observed=run(d,existing)
        assert r.returncode != 0
        assert b==s if existing else b is None
        assert observed['output_exists'] is existing
        assert observed['temporary_files'] == []

def test_duplicate_nested_json_member_is_rejected_atomically():
    '''CASE-QSC004-REJECT-DUPLICATE-MEMBER: "Reject duplicate object member names at any depth."'''
    raw='{"horizon_hours":1,"reserve_MW":0,"generators":[{"id":"g","min_MW":0,"max_MW":2,"marginal_cost":1,"startup_cost":0,"ramp_up_MW":2,"ramp_down_MW":2,"min_up_hours":0,"min_down_hours":0,"initial_state":"off"}],"storage":{"capacity_MWh":0,"capacity_MWh":1,"initial_MWh":0,"max_charge_MW":0,"max_discharge_MW":0,"charge_efficiency":1,"discharge_efficiency":1},"periods":[{"load_MW":0,"renewable_MW":0}]}'
    for existing in (False,True):
        r,b,s,observed=run_raw(raw,existing)
        assert r.returncode != 0
        assert b==s if existing else b is None
        assert observed['output_exists'] is existing
        assert observed['temporary_files'] == []

def test_boolean_horizon_is_not_an_integer():
    '''CASE-QSC004-REJECT-BOOLEAN-HORIZON: "JSON booleans are not numbers or integers."'''
    d=base(); d['horizon_hours']=True; d['periods']=[d['periods'][0]]
    for existing in (False,True):
        r,b,s,observed=run(d,existing)
        assert r.returncode != 0
        assert b==s if existing else b is None
        assert observed['output_exists'] is existing
        assert observed['temporary_files'] == []

def test_boolean_minimum_up_time_is_rejected():
    '''CASE-QSC004-REJECT-BOOLEAN-DURATION: "JSON booleans are not numbers or integers."'''
    d=base(); d['generators'][0]['min_up_hours']=True
    for existing in (False,True):
        r,b,s,observed=run(d,existing)
        assert r.returncode != 0
        assert b==s if existing else b is None
        assert observed['output_exists'] is existing
        assert observed['temporary_files'] == []

def test_invalid_discharge_efficiency_preserves_sentinel():
    '''CASE-QSC004-REJECT-EFFICIENCY: "Each storage efficiency must be greater than zero and at most one."'''
    d=base(); d['storage']['discharge_efficiency']=0
    for existing in (False,True):
        r,b,s,observed=run(d,existing)
        assert r.returncode != 0
        assert b==s if existing else b is None
        assert observed['output_exists'] is existing
        assert observed['temporary_files'] == []

def test_repeat_run_is_idempotent():
    '''CASE-QSC004-IDEMPOTENT: "Re-running the same valid input must be idempotent and produce the same JSON bytes"'''
    with tempfile.TemporaryDirectory() as td:
        p=Path(td); i=p/'input.json'; o=p/'output.json'; i.write_text(json.dumps(base()))
        first=subprocess.run([sys.executable,APP,str(i),str(o)],capture_output=True,timeout=20); b1=o.read_bytes()
        second=subprocess.run([sys.executable,APP,str(i),str(o)],capture_output=True,timeout=20); b2=o.read_bytes()
        assert first.returncode==0 and second.returncode==0 and b1==b2

def test_startup_cost_is_reported_once():
    '''CASE-QSC004-STARTUP-COST: "Report startup cost once when a unit changes from off to on".'''
    d=base(); d['generators']=d['generators'][:1]; d['generators'][0]['min_down_hours']=0; d['storage'].update({'capacity_MWh':0,'initial_MWh':0,'max_charge_MW':0,'max_discharge_MW':0}); d['horizon_hours']=2; d['periods']=[{'load_MW':6,'renewable_MW':0},{'load_MW':6,'renewable_MW':0}]; x=good(d)
    assert x['summary']['total_cost'] == pytest.approx(125.0, abs=1e-9)

def test_generator_order_is_preserved():
    '''CASE-QSC004-ORDER: "`generators` is an input-order array of objects".'''
    d=base(); d['generators']=list(reversed(d['generators'])); x=good(d)
    assert [g['id'] for g in x['dispatch'][0]['generators']]==[g['id'] for g in d['generators']]

def test_replace_failure_preserves_existing_output():
    '''CASE-QSC004-REPLACE-FAILURE: "leave `OUTPUT.json` absent or byte-for-byte unchanged."'''
    with tempfile.TemporaryDirectory() as td:
        p=Path(td); i=p/'input.json'; o=p/'output.json'; i.write_text(json.dumps(base()))
        baseline=subprocess.run([sys.executable,APP,str(i),str(o)],capture_output=True,timeout=20)
        assert baseline.returncode == 0
        assert set(json.loads(o.read_text(encoding='utf-8'))) == {'dispatch','summary'}
        sentinel=b'previous-result\x00'; o.write_bytes(sentinel)
        code="import os,runpy,sys; script,inp,out=sys.argv[3],sys.argv[1],sys.argv[2]; os.replace=lambda *a,**k: (_ for _ in ()).throw(OSError('injected replace failure')); sys.argv=['reference.py',inp,out]; runpy.run_path(script,run_name='__main__')"
        result=subprocess.run([sys.executable,'-c',code,str(i),str(o),APP],capture_output=True,timeout=20)
        assert result.returncode != 0
        assert o.read_bytes() == sentinel
        assert not list(p.glob('*.tmp'))

