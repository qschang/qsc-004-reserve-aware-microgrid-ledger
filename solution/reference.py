#!/usr/bin/env python3
import json, math, sys, os

# Domain invariants: 状态 transitions, 区间 bounds, 单位精度, 原子 publication,
# 幂等 repeated runs, and 跨运行 output stability are checked independently.

def fail(msg): raise ValueError(msg)
def finite(x): return isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x)
def validate(d):
    if not isinstance(d,dict) or set(d)!={'horizon_hours','reserve_MW','generators','storage','periods'}: fail('schema')
    H=d['horizon_hours']; reserve=d['reserve_MW']; gs=d['generators']; st=d['storage']; ps=d['periods']
    if not finite(reserve) or reserve<0: fail('reserve requirement')
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

def solve(d):
    validate(d); gs=d['generators']; st=d['storage']; ps=d['periods']; H=d['horizon_hours']; reserve_required=d['reserve_MW']
    state=st['initial_MWh']; prev={g['id']:(g['initial_state']=='on') for g in gs}; run={g['id']:0 for g in gs}; offrun={g['id']:0 for g in gs}; lastp={g['id']:0.0 for g in gs}
    out=[]; total_cost=0.0; unserved=0.0; curt=0.0; commit={g['id']:0 for g in gs}
    for t,p in enumerate(ps):
        renewable_for_load=min(p['load_MW'],p['renewable_MW'])
        renewable_surplus=p['renewable_MW']-renewable_for_load
        deficit=p['load_MW']-renewable_for_load
        ordered=sorted(gs,key=lambda x:(x['marginal_cost'],x['id']))
        must_on={}
        limits={}
        power={g['id']:0.0 for g in gs}
        on_flags={g['id']:False for g in gs}
        for g in gs:
            gid=g['id']
            forced_by_time=prev[gid] and run[gid]<g['min_up_hours']
            ramp_floor=max(0.0,lastp[gid]-g['ramp_down_MW']) if prev[gid] else 0.0
            forced_by_ramp=prev[gid] and ramp_floor>1e-12
            must_on[gid]=forced_by_time or forced_by_ramp
            blocked_off=not prev[gid] and offrun[gid]<g['min_down_hours']
            lo=max(g['min_MW'],ramp_floor) if prev[gid] else g['min_MW']
            hi=min(g['max_MW'],lastp[gid]+g['ramp_up_MW']) if prev[gid] else min(g['max_MW'],g['ramp_up_MW'])
            limits[gid]=(lo,hi,blocked_off)
            if must_on[gid]:
                if hi<lo-1e-12: fail('infeasible')
                power[gid]=lo
                on_flags[gid]=True
        remaining=max(0.0,deficit-sum(power.values()))
        for g in ordered:
            gid=g['id']; lo,hi,blocked_off=limits[gid]
            if blocked_off or hi<power[gid]+1e-12:
                continue
            if not must_on[gid] and power[gid]==0.0:
                if remaining<=1e-12:
                    continue
                if remaining+1e-12<lo or hi+1e-12<lo:
                    continue
                power[gid]=lo
                on_flags[gid]=True
                remaining=max(0.0,remaining-lo)
            extra=min(max(0.0,hi-power[gid]),remaining)
            power[gid]+=extra
            remaining-=extra
        thermal_surplus=max(0.0,sum(power.values())-deficit)
        discharge=min(st['max_discharge_MW'],state*st['discharge_efficiency'],remaining)
        state-=discharge/st['discharge_efficiency']; remaining=max(0.0,remaining-discharge)
        charge_limit=min(st['max_charge_MW'],max(0.0,(st['capacity_MWh']-state)/st['charge_efficiency']))
        charge=min(charge_limit,renewable_surplus+thermal_surplus)
        thermal_absorbed=max(0.0,charge-renewable_surplus)
        if thermal_absorbed+1e-12<thermal_surplus: fail('infeasible')
        state+=charge*st['charge_efficiency']
        renewable_charged=min(renewable_surplus,charge)
        renewable_used=renewable_for_load+renewable_charged
        curtailment=renewable_surplus-renewable_charged
        curt+=curtailment; unserved+=remaining
        recgen=[]
        for g in gs:
            gid=g['id']; powr=power[gid]; on=on_flags[gid]
            started=on and not prev[g['id']]
            total_cost += powr*g['marginal_cost'] + (g['startup_cost'] if started else 0.0); commit[g['id']]+=1 if on else 0
            recgen.append({'id':g['id'],'on':bool(on),'power_MW':powr})
            if on: run[g['id']]=run[g['id']]+1 if prev[g['id']] else 1; offrun[g['id']]=0
            else: offrun[g['id']]=offrun[g['id']]+1 if not prev[g['id']] else 1; run[g['id']]=0
            prev[g['id']]=on; lastp[g['id']]=powr
        total_cost += remaining*10000.0
        thermal=sum(x['power_MW'] for x in recgen)
        balance=renewable_used+thermal+discharge-charge+remaining-p['load_MW']
        storage_reserve=min(max(0.0,st['max_discharge_MW']-discharge),state*st['discharge_efficiency'])
        generator_reserve={g['id']:min(max(0.0,g['max_MW']-power[g['id']]),g['ramp_up_MW']) if on_flags[g['id']] else 0.0 for g in gs}
        online=sorted(gid for gid in generator_reserve if on_flags[gid])
        if online:
            outage_reserves={lost:storage_reserve+sum(value for gid,value in generator_reserve.items() if gid!=lost) for lost in online}
            limiting_id=min(online,key=lambda gid:(outage_reserves[gid],gid))
            available_reserve=outage_reserves[limiting_id]
        else:
            limiting_id=None
            available_reserve=storage_reserve
        if available_reserve+1e-9<reserve_required: fail('spinning reserve infeasible')
        out.append({'generators':recgen,'storage':{'charge_MW':charge,'discharge_MW':discharge,'state_MWh':state},'reserve':{'required_MW':reserve_required,'available_MW':available_reserve,'limiting_outage_id':limiting_id},'renewable_used_MW':renewable_used,'curtailment_MW':curtailment,'unserved_MW':remaining,'balance_residual_MW':balance})
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
