# Online HF MUF/Propagation Prediction Sources

Comprehensive guide to online sources for HF propagation predictions, Maximum Usable Frequency (MUF) data, and space weather information for amateur radio applications.

---

## Executive Summary

### Current Implementation (W4GNS Logger)
The codebase currently uses:
1. **NOAA SWPC** - K-index, geomagnetic scales, solar flux (via HamQSL fallback)
2. **HamQSL** - Solar Flux Index (SFI) primary source
3. **Empirical MUF calculation** - Local calculation based on SFI and K-index

### Recommended Online Sources (Ranked)

| Rank | Service | Best For | API Available | Accuracy | Free |
|------|---------|----------|---------------|----------|------|
| 1 | NOAA SWPC | Real-time space weather, K-index, SFI | Yes (JSON) | Official | Yes |
| 2 | HamQSL | Solar data aggregation | Yes (XML/RSS) | Good | Yes |
| 3 | KC2G prop.kc2g.com | Ham-focused MUF maps | Limited | Good | Yes |
| 4 | VOACAP Online | Path-specific predictions | No (web only) | Excellent | Yes |
| 5 | Proppy (ITU P.533) | Professional predictions | No (web only) | Excellent | Yes |
| 6 | WSPRnet | Real-world propagation | Telnet/scraping | Actual data | Yes |
| 7 | RBN | Real beacon data | Telnet | Actual data | Yes |

---

## 1. NOAA Space Weather Prediction Center (SWPC)

### Overview
Official US government space weather service. Most reliable source for geomagnetic and solar data.

### API Access
**Base URL:** `https://services.swpc.noaa.gov/`

**Authentication:** None required

**Rate Limiting:** Not specified, but use reasonable caching (30-60 min)

### Key Endpoints

#### A. NOAA Scales (Geomagnetic Conditions)
```
GET https://services.swpc.noaa.gov/products/noaa-scales.json
```

**Response Format:**
```json
{
  "0": {
    "DateStamp": "2025-10-26",
    "TimeStamp": "16:39:00",
    "R": {"Scale": "0", "Text": "none"},
    "S": {"Scale": "0", "Text": "none"},
    "G": {"Scale": "0", "Text": "none"}
  },
  "1": { /* Day 1 forecast */ },
  "2": { /* Day 2 forecast */ },
  "3": { /* Day 3 forecast */ }
}
```

**Data Provided:**
- `R` - Radio Blackout Scale (R0-R5)
- `S` - Solar Radiation Storm Scale (S0-S5)
- `G` - Geomagnetic Storm Scale (G0-G5)

**Update Frequency:** Every 3 hours

**Geographic Coverage:** Global

#### B. K-Index Forecast
```
GET https://services.swpc.noaa.gov/products/noaa-planetary-k-index-forecast.json
```

**Response Format:**
```json
[
  ["time_tag", "kp", "observed", "noaa_scale"],
  ["2025-10-19 00:00:00", "5.00", "observed", "G1"],
  ["2025-10-19 03:00:00", "3.33", "observed", null]
]
```

**Data Provided:**
- Kp index (0-9 scale)
- Observed vs predicted flag
- NOAA scale classification

**Update Frequency:** Every 3 hours

**Usage for MUF:**
```python
import requests

response = requests.get('https://services.swpc.noaa.gov/products/noaa-planetary-k-index-forecast.json')
data = response.json()

# Get latest observed K-index
for row in reversed(data[1:]):
    if row[2] == "observed":
        kp_index = float(row[1])
        break
```

#### C. Solar Flux Index (F10.7)
```
GET https://services.swpc.noaa.gov/json/f107_cm_flux.json
```

**Response Format:**
```json
[
  {
    "time_tag": "2025-10-25T20:00:00",
    "frequency": 2800,
    "flux": 126.0,
    "reporting_schedule": "Noon",
    "ninety_day_mean": 153.0,
    "rec_count": 90
  }
]
```

**Data Provided:**
- Solar Flux at 2800 MHz (10.7 cm)
- 90-day smoothed average
- Multiple daily observations

**Update Frequency:** 3 times per day (morning/noon/afternoon)

**Usage for MUF:** SFI is the primary driver for MUF calculations

### Advantages
- Official government source
- High reliability
- JSON format (easy parsing)
- No authentication required
- Free

### Disadvantages
- Does not provide MUF directly
- Requires calculation from base data
- Updates only every 3 hours

### Implementation Status
**Currently used:** Yes (in `src/services/space_weather_fetcher.py`)

---

## 2. HamQSL Solar/Propagation Data

### Overview
Community-maintained aggregation service providing solar-terrestrial data formatted for ham radio operators.

### API Access
**Base URL:** `https://www.hamqsl.com/`

**Authentication:** None required

**Rate Limiting:** Request every 3 hours minimum (data updates every 3 hours)

### Key Endpoints

#### Solar Data (Primary)
```
GET https://www.hamqsl.com/solar.json
```

**Note:** As of testing, this endpoint returns 404. The service may have changed formats.

**Alternative (XML format):**
```
GET https://www.hamqsl.com/solarxml.php
```

**Data Provided:**
- Solar Flux Index (SFI)
- A-Index and K-Index
- Sunspot Number
- X-Ray flux
- Proton flux
- Electron flux
- Aurora latitude
- MUF calculations for 4 HF band categories

**Update Frequency:** Every 3 hours

**Geographic Coverage:** Global

### Advantages
- Ham radio specific
- Pre-calculated MUF values
- Multiple formats (XML, RSS)
- Free

### Disadvantages
- JSON endpoint may be deprecated
- Secondary source (aggregates from NOAA)
- Less reliable than NOAA direct

### Implementation Status
**Currently used:** Yes (in `src/services/space_weather_fetcher.py` as SFI fallback)

**Current Issue:** JSON endpoint appears to be down/deprecated

---

## 3. KC2G Propagation (prop.kc2g.com)

### Overview
Open-source ham radio propagation prediction tool by Andrew Rodland (KC2G). Provides real-time MUF maps and band recommendations.

### API Access
**Website:** `https://prop.kc2g.com/`

**API:** Limited - primarily web-based visualization

**Authentication:** None required

### Data Provided
- MUF maps for 3000km paths
- foF2 (critical frequency) data from ionosondes worldwide
- eSSN (Effective Sunspot Number)
- HF propagation planner
- Band recommendations with beam headings

### Data Sources
- GIRO (Global Ionospheric Radio Observatory) - ionosonde data
- Real-time ionospheric measurements

### Advantages
- Ham radio specific
- Real-time ionosonde data
- Visual maps
- Open source
- Free

### Disadvantages
- No official API
- Requires web scraping for automation
- Limited to visualization primarily

### Implementation Potential
**Difficulty:** Medium (would require web scraping)

**Recommended:** For manual reference only, not automated queries

---

## 4. VOACAP Online (www.voacap.com)

### Overview
Professional HF propagation prediction software (3-30 MHz) from NTIA/ITS, originally developed for Voice of America.

### API Access
**Website:** `https://www.voacap.com/`

**API:** **NOT AVAILABLE** - Web forms only

**IMPORTANT:** Automated access is strictly prohibited without prior written agreement. Violations result in permanent ban.

### Access Method
Web-based interface only:
- Fill out transmitter/receiver locations
- Select antennas, power, date/time
- Submit form
- Receive graphical predictions

### Data Provided
- Point-to-point predictions
- MUF, FOT (Frequency of Optimum Traffic)
- Signal strength predictions
- Reliability calculations
- Path loss analysis
- Best frequency recommendations by hour

### Specialized Versions
- Ham Radio: `https://www.voacap.com/hf/`
- Marine HF: `https://www.voacap.com/marine/`
- 11M (CB): `https://www.voacap.com/11m/`

### Advantages
- Industry standard
- Extremely accurate
- Path-specific predictions
- Accounts for antenna characteristics
- Free

### Disadvantages
- **No API** - web only
- **Automated access forbidden**
- Requires manual interaction
- Cannot integrate into applications

### Implementation Potential
**Cannot be used** for automated applications

**Alternative:** Use `pythonprop` library (see Python Libraries section)

---

## 5. Proppy - ITU-R P.533 Predictions

### Overview
Online tool implementing ITU Recommendation P.533 (official HF circuit prediction method) using ITURHFProp.

### API Access
**Website:** `https://soundbytes.asia/proppy/`

**API:** Limited - primarily web interface

**GitHub:** `https://github.com/G4FKH/proppy`

### Access Method
Web forms:
- Point-to-Point predictions: `https://soundbytes.asia/proppy/p2p`
- Area predictions: `https://soundbytes.asia/proppy/area`
- Planner: `https://soundbytes.asia/proppy/planner`

### Data Provided
- Available frequencies
- Signal levels
- Circuit reliability
- MUF and FOT
- 24-hour predictions
- NCDXF/IARU beacon monitoring

### Method
ITU-R Recommendation P.533-14 (official international standard)

### Advantages
- Uses ITU official methodology
- Professional quality
- Open source
- Free

### Disadvantages
- No REST API
- Requires ITURHFProp (32-bit Windows, needs Wine on Linux)
- Web interface primarily

### Implementation Potential
**Difficulty:** High

**Option:** Run pythonprop locally (requires Wine + ITURHFProp)

---

## 6. WSPRnet - Weak Signal Propagation Reporter

### Overview
Crowdsourced propagation database using WSPR (Whisper) protocol. Real-world propagation measurements from thousands of stations.

### API Access
**Website:** `https://wsprnet.org/`

**API:** Telnet interface + database queries

**Data Access:** Public database

### Access Method
1. Telnet to WSPRnet server (DX-cluster-like interface)
2. Query historical database via website
3. Map interface showing spots

### Data Provided
- Real-time signal reports
- Signal strength (SNR)
- Frequency drift
- Power levels
- Path distances
- Historical propagation data

### Advantages
- Real-world actual propagation data
- Continuous measurements
- Global coverage
- Free

### Disadvantages
- Requires WSPR-capable stations
- Data is spot reports, not predictions
- Must correlate many reports for trends
- Telnet interface requires custom client

### Implementation Potential
**Difficulty:** Medium-High

**Python Library:** `rbn` (PyPI) - Reverse Beacon Network client (similar protocol)

**Usage:**
```python
# Example concept (not tested)
import telnetlib

tn = telnetlib.Telnet('wsprnet.org', port)
# Query spots for specific frequency/path
```

---

## 7. Reverse Beacon Network (RBN)

### Overview
Network of automated receivers that monitor HF bands and report heard stations. Provides real-time propagation intelligence.

### API Access
**Website:** `https://www.reversebeacon.net/`

**API:** Telnet interface (DX-cluster protocol)

**Data Access:** Real-time spots + historical database

### Access Method
```
Telnet: reversebeacon.net port 7000
```

### Data Provided
- Real-time station spots
- Signal strength (SNR/dB)
- Frequency
- Mode
- Time
- Receiving station location

### Advantages
- Real-world propagation data
- High spot volume
- Global coverage
- Free

### Disadvantages
- Telnet interface (not REST)
- Requires parsing DX-cluster protocol
- Spots, not predictions

### Implementation Potential
**Difficulty:** Medium

**Python Library:** `rbn` (available on PyPI)

**Installation:**
```bash
pip install rbn
```

**Usage:**
```python
from rbn import RBNClient

client = RBNClient()
client.connect()

for spot in client.iter_spots():
    print(f"{spot.callsign} on {spot.frequency} heard by {spot.de_call}")
```

---

## Python Libraries for HF Propagation

### 1. pythonprop (VOACAP Wrapper)
**GitHub:** `https://github.com/jawatson/pythonprop`

**Description:** Python wrapper for VOACAP propagation engine

**Features:**
- Point-to-point predictions
- Area coverage maps
- Creates VOACAP input files
- Plots predictions

**Installation:**
```bash
git clone https://github.com/jawatson/pythonprop
# Requires VOACAP engine separately
```

**Limitations:**
- Requires VOACAP engine installation
- GUI-focused (not library)
- Complex setup

### 2. proppy (ITU P.533 Wrapper)
**GitHub:** `https://github.com/G4FKH/proppy`

**Description:** Flask web app wrapping ITURHFProp

**Features:**
- ITU-R P.533 methodology
- Point-to-point predictions
- 24-hour analysis

**Limitations:**
- Requires ITURHFProp (Windows 32-bit)
- Web app, not importable library
- Needs Wine on Linux

### 3. rbn (Reverse Beacon Network Client)
**PyPI:** `https://pypi.org/project/rbn/`

**Installation:**
```bash
pip install rbn
```

**Description:** Client for accessing RBN real-time spots

**Usage:**
```python
from rbn import RBNClient

with RBNClient() as client:
    for spot in client.iter_spots():
        # Process real-time spots
        pass
```

---

## Recommendation for W4GNS Logger

### Current Approach: GOOD
The current implementation using empirical MUF calculation is appropriate because:

1. **No direct MUF API exists** - All services either:
   - Provide raw space weather data (NOAA)
   - Are web-only (VOACAP, Proppy)
   - Provide real-time spots, not predictions (WSPR, RBN)

2. **Current data sources are optimal:**
   - NOAA SWPC (K-index, geomagnetic data) - Official, reliable
   - HamQSL (SFI) - Ham-focused aggregator
   - Local calculation - Fast, no network dependency

### Recommended Enhancements

#### Short Term (Easy)
1. **Fix HamQSL endpoint**
   - JSON endpoint appears deprecated
   - Switch to XML: `https://www.hamqsl.com/solarxml.php`
   - Parse XML for SFI value

2. **Add NOAA F10.7 endpoint as primary SFI source**
   ```python
   # More reliable than HamQSL
   url = "https://services.swpc.noaa.gov/json/f107_cm_flux.json"
   ```

3. **Add band condition color coding**
   - Already implemented in UI
   - Enhance with time-of-day awareness (already done!)

#### Medium Term (Moderate Effort)
1. **Add RBN integration for real-world validation**
   - Install `rbn` library
   - Monitor RBN spots for user's bands
   - Show "Band is ACTIVE now" indicators based on real spots

2. **Cache NOAA data properly**
   - Already implemented with TTLCache
   - Ensure 30-60 minute cache lifetime

#### Long Term (Advanced)
1. **Local VOACAP installation (optional)**
   - Use `pythonprop` for path-specific predictions
   - Only for users who want professional-grade predictions
   - Complex installation (requires Wine on Linux)

2. **WSPRnet historical analysis**
   - Query WSPRnet database for specific paths
   - Show "This path was open X hours ago"
   - Moderate complexity

### What NOT to Do
1. **Do NOT scrape VOACAP website** - Violates ToS, will result in ban
2. **Do NOT query NOAA more than once per 30 minutes** - Unnecessary load
3. **Do NOT try to create MUF API wrapper** - No suitable source exists

---

## Example Integration Code

### Enhanced SFI Fetcher (using NOAA F10.7)
```python
import requests
from typing import Optional

def get_solar_flux_from_noaa() -> Optional[float]:
    """
    Get Solar Flux Index from NOAA SWPC (most reliable source)

    Returns:
        Current SFI value or None
    """
    try:
        url = "https://services.swpc.noaa.gov/json/f107_cm_flux.json"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        # Get most recent observation (first in array)
        if data and len(data) > 0:
            # Look for "Noon" observation (most reliable)
            for obs in data:
                if obs.get('reporting_schedule') == 'Noon':
                    flux = obs.get('flux')
                    if flux:
                        return float(flux)

            # Fallback to latest observation
            latest = data[0]
            flux = latest.get('flux')
            if flux:
                return float(flux)

        return None

    except Exception as e:
        print(f"Error fetching SFI from NOAA: {e}")
        return None
```

### RBN Spot Monitor (for real-time band activity)
```python
from rbn import RBNClient
import threading

class BandActivityMonitor:
    """Monitor RBN for current band activity"""

    def __init__(self, home_grid: str = "FN20"):
        self.home_grid = home_grid
        self.active_bands = set()
        self.client = None

    def start_monitoring(self):
        """Start background RBN monitoring"""
        def monitor():
            try:
                with RBNClient() as client:
                    self.client = client
                    for spot in client.iter_spots():
                        # Determine band from frequency
                        band = self._frequency_to_band(spot.frequency)
                        if band:
                            self.active_bands.add(band)
                            # Keep only last 5 minutes of activity
                            # (implement time-based expiry)
            except Exception as e:
                print(f"RBN error: {e}")

        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()

    def _frequency_to_band(self, freq_khz: float) -> Optional[str]:
        """Convert frequency to band name"""
        freq_mhz = freq_khz / 1000.0

        if 1.8 <= freq_mhz <= 2.0:
            return "160m"
        elif 3.5 <= freq_mhz <= 4.0:
            return "80m"
        elif 7.0 <= freq_mhz <= 7.3:
            return "40m"
        elif 14.0 <= freq_mhz <= 14.35:
            return "20m"
        elif 21.0 <= freq_mhz <= 21.45:
            return "15m"
        elif 28.0 <= freq_mhz <= 29.7:
            return "10m"

        return None

    def is_band_active(self, band: str) -> bool:
        """Check if band has recent activity"""
        return band in self.active_bands
```

---

## Data Format Comparison

| Source | Format | Auth | Updates | MUF Direct | SFI | K-Index |
|--------|--------|------|---------|------------|-----|---------|
| NOAA SWPC | JSON | No | 3hr | No | Yes | Yes |
| HamQSL | XML/RSS | No | 3hr | Calculated | Yes | Yes |
| KC2G | HTML | No | Real-time | Maps | No | No |
| VOACAP | Web | No | On-demand | Yes | - | - |
| Proppy | Web | No | On-demand | Yes | - | - |
| WSPRnet | Telnet/DB | No | Real-time | No | No | No |
| RBN | Telnet | No | Real-time | No | No | No |

---

## Conclusion

**Best approach for ham radio logging software:**

1. **Use NOAA SWPC as primary source** (K-index, SFI)
   - Most reliable
   - Official government data
   - JSON API

2. **Calculate MUF locally** (already implemented)
   - No online MUF API exists
   - Empirical formula is adequate
   - Fast and offline-capable

3. **Optional: Add RBN integration**
   - Shows real-world band activity
   - Complements predictions
   - Easy to implement with `rbn` library

4. **Avoid:**
   - Web scraping VOACAP (ToS violation)
   - Complex VOACAP/ITURHFProp installation
   - Over-querying APIs

**The current implementation in W4GNS Logger is well-designed and uses the best available data sources.**

---

## References

- NOAA SWPC: https://www.swpc.noaa.gov/
- NOAA SWPC JSON Index: https://services.swpc.noaa.gov/json/
- HamQSL: https://www.hamqsl.com/
- VOACAP: https://www.voacap.com/
- Proppy: https://soundbytes.asia/proppy/
- WSPRnet: https://wsprnet.org/
- RBN: https://www.reversebeacon.net/
- KC2G Propagation: https://prop.kc2g.com/
- pythonprop: https://github.com/jawatson/pythonprop
- ITU-R P.533: https://www.itu.int/rec/R-REC-P.533/

---

**Document Version:** 1.0
**Last Updated:** 2025-10-26
**Author:** Research for W4GNS Logger HF Propagation Integration
