#!/usr/bin/env python3
import json, math, sys, os

def fail(msg): raise ValueError(msg)
def finite(x): return isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x)
def validate(d):
    if not isinstance(d,dict) or set(d)!={'horizon_hours','generators','storage','periods'}: fail('schema')
    H=d['horizon_hours']; gs=d['generators']; st=d['storage']; ps=d['periods']
    if not isinstance(H,int) or H<1 or H>96 or len(ps)!=H or not isinstance(gs,list) or not gs: fail('horizon')
    ids=set()
    for g in gs:
        req={'id','min_MW','max_MW','marginal_cost','startup_cost','ramp_up_MW','ramp_down_MW','min_up_hours','min_down_hours','initial_state'}
        if set(g)!=req or not isinstance(g['id'],str) or not g['id'] or g['id'] in ids: fail('generator')
        ids.add(g['id'])
        for k in req-{'id','initial_state','min_up_hours','min_down_hours'}:
            if not finite(g[k]) or g[k]<0: fail('generator number')
        if g['max_MW']<g['min_MW'] or not isinstance(g['min_up_hours'],int) or not isinstance(g['min_down_hours'],int) or g['min_up_hours']<0 or g['min_down_hours']<0 or g['initial_state'] not in ('on','off'): fail('generator limits')
    reqs={'capacity_MWh','initial_MWh','max_charge_MW','max_discharge_MW','charge_efficiency','discharge_efficiency'}
    if not isinstance(st,dict) or set(st)!=reqs: fail('storage schema')
    for k in reqs:
        if not finite(st[k]): fail('storage finite')
    if st['capacity_MWh']<0 or st['initial_MWh']<0 or st['initial_MWh']>st['capacity_MWh'] or st['max_charge_MW']<0 or st['max_discharge_MW']<0 or not (0<st['charge_efficiency']<=1) or not (0<st['discharge_efficiency']<=1): fail('storage limits')
    for p in ps:
        if not isinstance(p,dict) or set(p)!={'load_MW','renewable_MW'} or not finite(p['load_MW']) or not finite(p['renewable_MW']) or p['load_MW']<0 or p['renewable_MW']<0: fail('period')

def choose_on(g, prev, remaining_on, remaining_off):
    if prev: return True
    return remaining_off<=0

def solve(d):
    validate(d); gs=d['generators']; st=d['storage']; ps=d['periods']; H=d['horizon_hours']
    state=st['initial_MWh']; prev={g['id']:(g['initial_state']=='on') for g in gs}; run={g['id']:0 for g in gs}; offrun={g['id']:0 for g in gs}; lastp={g['id']:0.0 for g in gs}
    out=[]; total_cost=0.0; unserved=0.0; curt=0.0; commit={g['id']:0 for g in gs}
    for t,p in enumerate(ps):
        renewable=min(p['load_MW'],p['renewable_MW']); excess=max(0.0,p['renewable_MW']-p['load_MW']); deficit=max(0.0,p['load_MW']-renewable)
        eligible=[]
        for g in sorted(gs,key=lambda x:(x['marginal_cost'],x['id'])):
            must_on=prev[g['id']] and run[g['id']]<g['min_up_hours']
            blocked_off=(not prev[g['id']] and offrun[g['id']]<g['min_down_hours'])
            if must_on or (deficit>0 and not blocked_off): eligible.append((g,must_on))
        gen=[]; remaining=deficit
        for g,must in eligible:
            on=True
            lo=g['min_MW']; hi=g['max_MW']
            if prev[g['id']]: lo=max(lo,lastp[g['id']]-g['ramp_down_MW']); hi=min(hi,lastp[g['id']]+g['ramp_up_MW'])
            else: lo=max(lo,0.0); hi=min(hi,g['ramp_up_MW'])
            if hi<lo-1e-12: fail('ramp infeasible')
            power=min(hi,max(lo,remaining)) if remaining>0 else (lo if must else 0.0)
            if power>0 or must: remaining-=power; gen.append((g,on,power))
            else: gen.append((g,False,0.0))
        for g in gs:
            if not any(x[0]['id']==g['id'] for x in gen): gen.append((g,False,0.0))
        discharge=min(st['max_discharge_MW'],state*st['discharge_efficiency'],remaining)
        state-=discharge/st['discharge_efficiency']; remaining-=discharge
        charge=min(st['max_charge_MW'],max(0.0,(st['capacity_MWh']-state)/st['charge_efficiency']),excess)
        state+=charge*st['charge_efficiency']; excess-=charge
        curt+=excess; unserved+=remaining
        recgen=[]
        for g,on,powr in sorted(gen,key=lambda x:gs.index(x[0])):
            started=on and not prev[g['id']]
            total_cost += powr*g['marginal_cost'] + (g['startup_cost'] if started else 0.0); commit[g['id']]+=1 if on else 0
            recgen.append({'id':g['id'],'on':bool(on),'power_MW':powr})
            if on: run[g['id']]=run[g['id']]+1 if prev[g['id']] else 1; offrun[g['id']]=0
            else: offrun[g['id']]=offrun[g['id']]+1 if not prev[g['id']] else 1; run[g['id']]=0
            prev[g['id']]=on; lastp[g['id']]=powr
        total_cost += remaining*10000.0
        thermal=sum(x['power_MW'] for x in recgen)
        renewable_used=max(0.0, p['load_MW'] + charge - discharge + remaining - thermal)
        renewable_used=min(p['renewable_MW'], renewable_used)
        curtailment=max(0.0, p['renewable_MW']-renewable_used)
        balance=renewable_used+thermal+discharge-charge+remaining-p['load_MW']
        out.append({'generators':recgen,'storage':{'charge_MW':charge,'discharge_MW':discharge,'state_MWh':state},'renewable_used_MW':renewable_used,'curtailment_MW':curtailment,'unserved_MW':remaining,'balance_residual_MW':balance})
    return {'dispatch':out,'summary':{'total_cost':total_cost,'total_unserved_MWh':unserved,'total_renewable_curtailment_MWh':curt,'final_storage_MWh':state,'commitment_hours':commit}}

def main():
    if len(sys.argv)!=3: return 2
    inp,out=sys.argv[1:]
    try:
        with open(inp,encoding='utf-8') as f: d=json.load(f)
        result=solve(d)
        tmp=out+'.tmp'
        with open(tmp,'w',encoding='utf-8') as f: json.dump(result,f,ensure_ascii=False,separators=(',',':')); f.write('\n')
        os.replace(tmp,out); return 0
    except Exception as e:
        try:
            if os.path.exists(out+'.tmp'): os.unlink(out+'.tmp')
        except OSError: pass
        print(str(e),file=sys.stderr); return 1
if __name__=='__main__': sys.exit(main())
