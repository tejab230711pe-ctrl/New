#!/usr/bin/env python3
"""Plot retained numerical checks; this is not a predicted full deposited track."""
import argparse
import csv
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def plot(flow, contacts, output):
    balance=json.loads((flow/'balance.json').read_text())
    surface=json.loads((flow/'surface_flux.json').read_text())
    with (flow/'flow.csv').open() as f:
        temperatures=[{k:float(v) for k,v in r.items()} for r in csv.DictReader(f)]
    start=temperatures[0]['time']
    fig,axes=plt.subplots(2,2,figsize=(11,7),layout='constrained')
    ax=axes[0,0]
    time=[1000*(r['time']-start) for r in temperatures]
    for name,label in [('T_max','Maximum'),('T_min','Minimum')]:
        ax.plot(time,[r[name] for r in temperatures],label=label)
    ax.set(xlabel='Elapsed hot-flow time (ms)',ylabel='Temperature (K)',title='Assumed hot start: 723.15 K')
    ax.legend()
    ax=axes[0,1]
    ax.plot([1000*(r['time']-start) for r in balance['samples']],
            [100*abs(r['relative_to_feed']) for r in balance['samples']],label='Volume error / feed')
    ax.plot([1000*(r['time_s']-start) for r in surface['samples']],
            [100*r['absolute_free_surface_leak_relative_to_feed'] for r in surface['samples']],label='Surface leakage / feed')
    ax.axhline(2,color='black',ls='--',lw=1,label='Qualification screen')
    ax.set(xlabel='Elapsed hot-flow time (ms)',ylabel='Error (%)',title='Numerical conservation screens')
    ax.legend(fontsize=8)
    ax=axes[1,0]
    for directory in contacts:
        budget=json.loads((directory/'thermal_balance.json').read_text())
        ax.plot([1e6*r['time_s'] for r in budget['samples']],
                [100*r['relative_to_generated_heat'] for r in budget['samples']],marker='o',label=directory.name)
    ax.axhline(2,color='black',ls='--',lw=1)
    ax.axhline(-2,color='black',ls='--',lw=1)
    ax.set(xlabel='Elapsed contact time (microseconds)',ylabel='Thermal budget error (%)',title='Stored heat + loss − generated heat')
    ax.legend(fontsize=8)
    ax=axes[1,1]
    tracer=json.loads((flow/'rod_transport.json').read_text())
    data=tracer['history']
    ax.plot([1000*(r['time_s']-start) for r in data],
            [1e9*r['rod_volume_in_trailing_region_m3'] for r in data],label='Rod-origin volume behind rod')
    ax.set(xlabel='Elapsed hot-flow time (ms)',ylabel='Tracked volume (mm³)',title='Trailing deposit has not yet formed')
    ax.legend(fontsize=8)
    for ax in axes.flat:
        ax.grid(alpha=.2)
    fig.suptitle('AFSD numerical qualification — short runs, not experimental validation',fontsize=13)
    output.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(output,dpi=160)
    plt.close(fig)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('flow',type=Path)
    p.add_argument('output',type=Path)
    p.add_argument('--contacts',type=Path,nargs='+',required=True)
    a=p.parse_args();plot(a.flow,a.contacts,a.output)
