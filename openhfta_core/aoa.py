import re
from typing import Optional
from .exceptions import ValidationError

HAM_BANDS = {'160m': 1.85, '80m': 3.75, '60m': 5.35, '40m': 7.15, '30m': 10.12,
             '20m': 14.2, '17m': 18.1, '15m': 21.2, '12m': 24.9, '10m': 28.5, '6m': 50.1}

def parse_frequency(freq_str: str) -> float:
    value = freq_str.strip().lower().replace(',', '.')
    if value in HAM_BANDS: return HAM_BANDS[value]
    value = re.sub(r'\s*mhz\s*$', '', value).strip()
    try: return float(value)
    except ValueError as exc: raise ValidationError(f"Invalid frequency specification: {freq_str}. Use MHz value or ham band like '20m'.") from exc

def frequency_to_band(freq_mhz: float) -> Optional[str]:
    ranges = [('160m',1.8,2),('80m',3.5,4),('60m',5.3,5.4),('40m',7,7.3),('30m',10.1,10.15),('20m',14,14.35),('17m',18.068,18.168),('15m',21,21.45),('12m',24.89,24.99),('10m',28,29.7),('6m',50,54)]
    return next((name for name, low, high in ranges if low <= freq_mhz <= high), None)

def parse_prn_multiband(content: str, band: Optional[str] = None) -> dict[int, float]:
    lines = content.replace('\ufeff', '').splitlines()
    header_index = next((index for index, line in enumerate(lines) if line.strip().lower().startswith('elev')), None)
    if header_index is None or band is None: return {}
    header_names = header_index
    raw_names = lines[header_names].strip().split()[1:]
    names = []
    for token in raw_names:
        # A spaced header such as "14.20 MHz" represents one column.
        if token.lower() == 'mhz' and names:
            continue
        names.append(token)
    normalized = []
    for name in names:
        token = name.lower().replace('mhz', '').strip().replace(',', '.')
        if token.endswith('m'):
            candidate = token
        else:
            try:
                # Some PRN producers write the column as 14.20 MHz instead of 20m.
                candidate = frequency_to_band(float(token))
            except ValueError:
                candidate = None
        # Ignore labels such as "Stat." in headers like "Elev. Stat. 20m...".
        # Data columns are then indexed only by actual band/frequency columns.
        if candidate in HAM_BANDS:
            normalized.append(candidate)
        elif candidate is not None:
            normalized.append(candidate)
    wanted = band.lower()
    if wanted not in normalized: return {}
    index = normalized.index(wanted); result = {}
    for line in lines[header_index + 1:]:
        parts = line.strip().split()
        if len(parts) < 2: continue
        try:
            angle, percentage = int(float(parts[0])), float(parts[index + 1])
            probability = percentage / 100.0
            if 0 <= probability <= 1 and 0 <= angle <= 90: result[angle] = probability
        except (ValueError, IndexError): continue
    # An all-zero column means the path has no statistics on that band.
    return result if any(result.values()) else {}

def parse_aoa_file(path: str, frequency_mhz: float) -> dict[int, float]:
    with open(path) as file: return parse_prn_multiband(file.read(), frequency_to_band(frequency_mhz))
