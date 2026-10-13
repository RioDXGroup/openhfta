#!/usr/bin/env python3
"""Compatibility CLI adapter for :mod:`openhfta_core`."""
import os, sys
from pathlib import Path
import numpy as np
from openhfta_core.aoa import parse_frequency, frequency_to_band, parse_aoa_file, parse_prn_multiband
from openhfta_core.analysis import analyze as analyze_result
from openhfta_core.library import load_ytw_core, FortranInt16, FortranInt32, FortranReal
from openhfta_core.metrics import compute_fom
from openhfta_core.profiles import parse_height_and_phase, parse_profile
from openhfta_core.models import AnalysisConfig
from openhfta_core.plotting import plot_multiple_patterns, plot_multiple_terrain_profiles

def find_ytw_core_library():
    """Compatibility wrapper whose lookup remains relative to this script."""
    import ctypes.util
    env_path = os.environ.get('OPENHFTA_LIB')
    if env_path:
        path = Path(env_path).expanduser()
        return str(path if path.is_absolute() else Path.cwd() / path)
    script_dir = Path(__file__).resolve().parent
    for directory in (script_dir, script_dir.parent / 'lib'):
        for name in ('libopenytwcore.so', 'OpenYTWCore.dll', 'libOpenYTWCore.dylib'):
            candidate = directory / name
            if candidate.exists(): return str(candidate)
    return ctypes.util.find_library('openytwcore')

def analyze(profile_path, frequency_mhz, antenna_heights=[10.0], antenna_phases=[1], soil_epsr=13.0, soil_sigma=.005, diffraction_disable=False, debug_enable=False, debug_angle=0., lib_path=None, move_tower=0., antenna_pattern_type=1):
    """Legacy tuple-returning wrapper retained for existing callers."""
    result = analyze_result(AnalysisConfig(profile_path, frequency_mhz, tuple(antenna_heights), tuple(antenna_phases), soil_epsr, soil_sigma, diffraction_disable, debug_enable, debug_angle, lib_path, move_tower, antenna_pattern_type))
    return result.angles_deg, result.pattern_db

def parse_profile_blocks(args):
    defaults = {'heights':['10.0'], 'antenna_type':'Dipole', 'move_tower':0.0}
    global_args = {'freq':None,'soil_sigma':.005,'soil_epsr':13.,'units':'meters','no_diffraction':False,'plot_mode':'elevation','lib':None,'aoa':None,'output':None,'debug':False,'debug_angle':0.}
    profiles=[]; current=None; i=0
    while i < len(args):
        arg=args[i]
        if arg == '--profile':
            if i+1 >= len(args): raise ValueError('--profile requires a filename argument')
            if current is not None: profiles.append(current.copy())
            current=defaults.copy(); current['profile']=args[i+1]; i+=2
        elif arg == '--freq': global_args['freq']=args[i+1]; i+=2
        elif arg == '--heights':
            if current is None: raise ValueError('--heights must come after --profile')
            i+=1; values=[]
            while i<len(args) and not args[i].startswith('--'): values.append(args[i]); i+=1
            if not values: raise ValueError('--heights requires at least one value')
            current['heights']=values
        elif arg == '--antenna-type':
            if current is None: raise ValueError('--antenna-type must come after --profile')
            value=args[i+1]
            if value not in ['Dipole','2-Ele','3-Ele','4-Ele','5-Ele','6-Ele','8-Ele']: raise ValueError(f'Invalid antenna type: {value}')
            current['antenna_type']=value; i+=2
        elif arg == '--move-tower': current['move_tower']=float(args[i+1]); i+=2
        elif arg == '--units':
            value=args[i+1]
            if value not in ['meters','feet']: raise ValueError(f'Invalid units: {value}')
            global_args['units']=value; i+=2
        elif arg in ('--soil-sigma','--soil-epsr','--debug-angle'):
            key={'--soil-sigma':'soil_sigma','--soil-epsr':'soil_epsr','--debug-angle':'debug_angle'}[arg]; global_args[key]=float(args[i+1]); i+=2
        elif arg == '--no-diffraction': global_args['no_diffraction']=True; i+=1
        elif arg == '--plot-mode':
            global_args['plot_mode']=args[i+1]
            if global_args['plot_mode'] not in ('elevation','terrain'): raise ValueError(f"Invalid plot mode: {global_args['plot_mode']}")
            i+=2
        elif arg in ('--lib','--aoa','--output'):
            global_args[arg[2:]]=args[i+1]; i+=2
        elif arg == '--debug': global_args['debug']=True; i+=1
        elif arg in ('-h','--help'): print_help(); raise SystemExit(0)
        else: raise ValueError(f'Unknown argument: {arg}')
    if current is not None: profiles.append(current)
    if not profiles: raise ValueError('At least one --profile must be specified')
    if global_args['plot_mode']=='elevation' and global_args['freq'] is None: raise ValueError('--freq is required')
    return profiles, global_args

def print_help():
    print('''OpenHFTA - HF Terrain Analysis using OpenYTWCore

Usage: hfta --profile terrain.pro [profile-options] --freq frequency [global-options]
  --profile FILE, --heights H1 [H2 ...], --antenna-type TYPE, --move-tower DISTANCE
  --freq FREQUENCY, --units {meters,feet}, --soil-sigma SIGMA, --soil-epsr EPSR
  --no-diffraction, --plot-mode {elevation,terrain}, --lib PATH, --aoa FILE
  --output FILE, --debug, --debug-angle ANGLE''')

def main():
    try: profiles, global_args = parse_profile_blocks(sys.argv[1:])
    except ValueError as exc: print(f'Error: {exc}', file=sys.stderr); return 1
    mapping={'Dipole':1,'2-Ele':2,'3-Ele':3,'4-Ele':4,'5-Ele':5,'6-Ele':6,'8-Ele':7}
    for config in profiles:
        if not os.path.exists(config['profile']): print(f"Error: Profile file '{config['profile']}' not found", file=sys.stderr); return 1
        config['processed_heights'], config['processed_phases'] = zip(*(parse_height_and_phase(x, global_args['units']) for x in config['heights']))
        config['processed_heights'], config['processed_phases'] = list(config['processed_heights']), list(config['processed_phases']); config['antenna_pattern_type']=mapping[config['antenna_type']]
    if global_args['plot_mode']=='terrain': plot_multiple_terrain_profiles(profiles, global_args, global_args['output']); return 0
    try: frequency=parse_frequency(global_args['freq'])
    except Exception as exc: print(f'Error: {exc}', file=sys.stderr); return 1
    aoa=parse_aoa_file(global_args['aoa'], frequency) if global_args['aoa'] else None; results=[]
    if aoa: print(f"Loaded AoA data: {len(aoa)} angle points")
    print(f"Diffraction: {'Disabled' if global_args['no_diffraction'] else 'Enabled'}")
    for i, config in enumerate(profiles):
        print(f"Analyzing profile {i+1}/{len(profiles)}: {Path(config['profile']).name}")
        print(f"  {frequency:.1f} MHz with {config['antenna_type']} antenna\n  Heights: {config['heights']} {global_args['units']}")
        result=analyze_result(AnalysisConfig(config['profile'], frequency, tuple(config['processed_heights']), tuple(config['processed_phases']), global_args['soil_epsr'], global_args['soil_sigma'], global_args['no_diffraction'], global_args['debug'], global_args['debug_angle'], global_args['lib'], config['move_tower']*(3.28084 if global_args['units']=='meters' else 1), config['antenna_pattern_type']))
        fom=compute_fom(result.pattern_db, aoa) if aoa else None
        results.append({'config':config,'angles':result.angles_deg,'pattern_db':result.pattern_db,'fom':fom})
    for i, result in enumerate(results):
        summary = f"\nProfile {i+1} ({Path(result['config']['profile']).name}):\n  Maximum gain: {np.max(result['pattern_db']):.1f} dB at {result['angles'][np.argmax(result['pattern_db'])]:.2f}°"
        if result['fom'] is not None: summary += f"\n  Figure of Merit (FOM): {result['fom']:.1f}"
        print(summary)
    plot_multiple_patterns(results, frequency, not global_args['no_diffraction'], aoa, global_args, global_args['output']); return 0

if __name__ == '__main__': sys.exit(main())
