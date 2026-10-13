from pathlib import Path
from typing import Any, Optional
import matplotlib.pyplot as plt
import numpy as np

def plot_multiple_terrain_profiles(profile_configs: list[dict[str, Any]], global_args: dict[str, Any], output_path: Optional[str] = None):
    fig, ax = plt.subplots(figsize=(12, 8)); factor = 1 / 3.28084 if global_args['units'] == 'meters' else 1
    colors = plt.cm.tab10(np.linspace(0, 1, len(profile_configs)))
    for i, config in enumerate(profile_configs):
        from .profiles import parse_profile
        distances, heights = parse_profile(config['profile']); ax.plot(distances*factor, heights*factor, label=Path(config['profile']).name, color=colors[i])
        for j, height in enumerate(config['processed_heights']): ax.plot(0, (heights[0]+height)*factor, 'o', color=colors[i], label=f'Ant {j+1}' if j == 0 else None)
    ax.set(xlabel=f"Distance ({global_args['units']})", ylabel=f"Height ({global_args['units']})", title='Terrain Profile'); ax.grid(alpha=.3); ax.legend(); fig.tight_layout()
    if output_path: fig.savefig(output_path, dpi=150, bbox_inches='tight')
    else: plt.show()
    plt.close(fig)

def plot_multiple_patterns(results, frequency_mhz, diffraction_enabled, aoa_data, global_args, output_path=None):
    fig, ax = plt.subplots(figsize=(12, 8)); colors = plt.cm.tab10(np.linspace(0, 1, len(results)))
    for i, result in enumerate(results):
        config, angles, pattern = result['config'], result['angles'], result['pattern_db']
        ax.plot(angles, pattern, color=colors[i], label=f"{Path(config['profile']).name} • {config['antenna_type']}")
    ax.set(xlabel='Elevation angle (degrees)', ylabel='Gain (dB)', title=f'{frequency_mhz:.1f} MHz • Diffraction: {"On" if diffraction_enabled else "Off"}', xlim=(0,35)); ax.grid(alpha=.3); ax.legend(bbox_to_anchor=(1.05,1), loc='upper left'); fig.tight_layout()
    if output_path: fig.savefig(output_path, dpi=150, bbox_inches='tight')
    else: plt.show()
    plt.close(fig)
