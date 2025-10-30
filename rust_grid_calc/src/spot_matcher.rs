use pyo3::prelude::*;
use std::collections::HashSet;

/// Spot data structure for matching
#[derive(Clone, Debug)]
pub struct Spot {
    pub callsign: String,
    pub frequency: f64,
    pub band: String,
    pub mode: String,
    pub snr: i32,
    pub spotter: String,
    pub timestamp: String,
}

/// Fast spot filtering and matching
pub struct SpotMatcher {
    worked_callsigns: HashSet<String>,
    worked_callsign_bands: HashSet<String>, // "CALLSIGN:BAND"
    skcc_members: HashSet<String>,
    tribune_members: HashSet<String>,
}

impl SpotMatcher {
    pub fn new() -> Self {
        SpotMatcher {
            worked_callsigns: HashSet::new(),
            worked_callsign_bands: HashSet::new(),
            skcc_members: HashSet::new(),
            tribune_members: HashSet::new(),
        }
    }
    
    /// Check if callsign has been worked
    pub fn is_worked(&self, callsign: &str) -> bool {
        self.worked_callsigns.contains(callsign)
    }
    
    /// Check if callsign+band has been worked
    pub fn is_worked_on_band(&self, callsign: &str, band: &str) -> bool {
        let key = format!("{}:{}", callsign, band);
        self.worked_callsign_bands.contains(&key)
    }
    
    /// Check if callsign is SKCC member
    pub fn is_skcc(&self, callsign: &str) -> bool {
        self.skcc_members.contains(callsign)
    }
    
    /// Check if callsign is Tribune/Senator
    pub fn is_tribune(&self, callsign: &str) -> bool {
        self.tribune_members.contains(callsign)
    }
    
    /// Filter spots by criteria
    pub fn filter_spots(
        &self,
        spots: &[(String, f64, String, String, i32, String, String)],
        min_snr: i32,
        bands: &[String],
        skcc_only: bool,
        unworked_only: bool,
    ) -> Vec<usize> {
        let band_set: HashSet<&String> = bands.iter().collect();
        let mut matching_indices = Vec::new();
        
        for (idx, (callsign, _freq, band, _mode, snr, _spotter, _timestamp)) in spots.iter().enumerate() {
            // SNR filter
            if *snr < min_snr {
                continue;
            }
            
            // Band filter
            if !band_set.is_empty() && !band_set.contains(band) {
                continue;
            }
            
            // SKCC filter
            if skcc_only && !self.is_skcc(callsign) {
                continue;
            }
            
            // Unworked filter
            if unworked_only && self.is_worked_on_band(callsign, band) {
                continue;
            }
            
            matching_indices.push(idx);
        }
        
        matching_indices
    }
}

/// Create a new spot matcher
#[pyfunction]
pub fn create_spot_matcher() -> PyResult<usize> {
    // Return a handle (in real implementation, would use py.allow_threads)
    Ok(0)
}

/// Batch filter spots
/// 
/// Args:
///     spots: List of dict with keys: callsign, frequency, band, mode, snr
///     worked_calls: Set of worked callsigns
///     worked_bands: Set of "CALL:BAND" strings
///     skcc_members: Set of SKCC member callsigns
///     tribune_members: Set of Tribune/Senator callsigns
///     min_snr: Minimum signal strength
///     bands: List of bands to include (empty = all)
///     skcc_only: Only show SKCC members
///     unworked_only: Only show unworked stations
/// 
/// Returns:
///     List of indices that passed all filters
#[pyfunction]
pub fn batch_filter_spots<'py>(
    py: Python<'py>,
    spots: Vec<Bound<'py, pyo3::types::PyDict>>,
    worked_calls: Vec<String>,
    worked_bands: Vec<String>,
    skcc_members: Vec<String>,
    tribune_members: Vec<String>,
    min_snr: i32,
    bands: Vec<String>,
    skcc_only: bool,
    unworked_only: bool,
) -> PyResult<Vec<usize>> {
    // Build lookup sets
    let worked_set: HashSet<String> = worked_calls.into_iter().collect();
    let worked_band_set: HashSet<String> = worked_bands.into_iter().collect();
    let skcc_set: HashSet<String> = skcc_members.into_iter().collect();
    let tribune_set: HashSet<String> = tribune_members.into_iter().collect();
    let band_filter: HashSet<String> = bands.into_iter().collect();
    
    let mut indices = Vec::new();
    
    for (idx, spot_dict) in spots.iter().enumerate() {
        // Extract fields from dict
        let callsign: String = spot_dict.get_item("callsign")?.ok_or_else(|| 
            PyErr::new::<pyo3::exceptions::PyKeyError, _>("Missing 'callsign' key")
        )?.extract()?;
        
        let band: String = spot_dict.get_item("band")?.ok_or_else(|| 
            PyErr::new::<pyo3::exceptions::PyKeyError, _>("Missing 'band' key")
        )?.extract()?;
        
        let snr: i32 = spot_dict.get_item("snr")?.ok_or_else(|| 
            PyErr::new::<pyo3::exceptions::PyKeyError, _>("Missing 'snr' key")
        )?.extract()?;
        
        // SNR filter
        if snr < min_snr {
            continue;
        }
        
        // Band filter
        if !band_filter.is_empty() && !band_filter.contains(&band) {
            continue;
        }
        
        let is_worked = worked_set.contains(&callsign);
        let is_skcc = skcc_set.contains(&callsign);
        let band_key = format!("{}:{}", callsign, band);
        let is_worked_band = worked_band_set.contains(&band_key);
        
        // SKCC filter
        if skcc_only && !is_skcc {
            continue;
        }
        
        // Unworked filter
        if unworked_only && is_worked_band {
            continue;
        }
        
        indices.push(idx);
    }
    
    Ok(indices)
}

/// Parse RBN spot line
/// 
/// Example: "DX de K3LR-#:     14025.0  W4GNS         CW    24 dB  33 WPM  CQ      1234Z"
/// 
/// Returns: dict with keys: callsign, frequency, snr, timestamp
#[pyfunction]
pub fn parse_rbn_spot<'py>(py: Python<'py>, line: &str) -> PyResult<Bound<'py, pyo3::types::PyDict>> {
    use pyo3::types::PyDict;
    
    let parts: Vec<&str> = line.split_whitespace().collect();
    
    // Need at least: DX de SPOTTER: FREQ CALL MODE SNR
    if parts.len() < 7 {
        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
            "Invalid RBN spot format: too few parts"
        ));
    }
    
    // Check for "DX de"
    if parts.get(0) != Some(&"DX") || parts.get(1) != Some(&"de") {
        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
            "Invalid RBN spot format: missing 'DX de' prefix"
        ));
    }
    
    // Extract frequency (index 3)
    let freq = match parts.get(3) {
        Some(f) => match f.parse::<f64>() {
            Ok(val) => val,
            Err(_) => return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Invalid frequency value"
            )),
        },
        None => return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
            "Missing frequency field"
        )),
    };
    
    // Extract callsign (index 4)
    let callsign = match parts.get(4) {
        Some(c) => c.to_string(),
        None => return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
            "Missing callsign field"
        )),
    };
    
    // Extract SNR - look for pattern like "24 dB"
    let mut snr = 0;
    for i in 0..parts.len() {
        if let Some(next) = parts.get(i + 1) {
            if *next == "dB" {
                if let Ok(s) = parts[i].parse::<i32>() {
                    snr = s;
                    break;
                }
            }
        }
    }
    
    // Extract timestamp (last element ending in Z)
    let timestamp = parts.iter()
        .rev()
        .find(|p| p.ends_with('Z'))
        .map(|s| s.to_string())
        .unwrap_or_else(|| String::from(""));
    
    // Create Python dict
    let result = PyDict::new_bound(py);
    result.set_item("callsign", callsign)?;
    result.set_item("frequency", freq)?;
    result.set_item("snr", snr)?;
    result.set_item("timestamp", timestamp)?;
    
    Ok(result)
}

/// Determine band from frequency (MHz)
#[pyfunction]
pub fn frequency_to_band(freq_mhz: f64) -> PyResult<String> {
    let band = match freq_mhz {
        f if f >= 1.8 && f <= 2.0 => "160M",
        f if f >= 3.5 && f <= 4.0 => "80M",
        f if f >= 5.3 && f <= 5.4 => "60M",
        f if f >= 7.0 && f <= 7.3 => "40M",
        f if f >= 10.1 && f <= 10.15 => "30M",
        f if f >= 14.0 && f <= 14.35 => "20M",
        f if f >= 18.068 && f <= 18.168 => "17M",
        f if f >= 21.0 && f <= 21.45 => "15M",
        f if f >= 24.89 && f <= 24.99 => "12M",
        f if f >= 28.0 && f <= 29.7 => "10M",
        f if f >= 50.0 && f <= 54.0 => "6M",
        _ => "UNK",
    };
    
    Ok(band.to_string())
}

/// Determine mode from frequency and additional hints
#[pyfunction]
#[pyo3(signature = (freq_mhz, mode_hint=None))]
pub fn determine_mode(freq_mhz: f64, mode_hint: Option<&str>) -> PyResult<String> {
    // If explicit mode hint provided, use it
    if let Some(hint) = mode_hint {
        let hint_upper = hint.to_uppercase();
        if ["CW", "SSB", "USB", "LSB", "FM", "RTTY", "FT8", "FT4"].contains(&hint_upper.as_str()) {
            return Ok(hint_upper);
        }
    }
    
    // Determine from frequency
    let mode = match freq_mhz {
        // CW portions
        f if (f >= 1.8 && f <= 1.84) => "CW",
        f if (f >= 3.5 && f <= 3.6) => "CW",
        f if (f >= 7.0 && f <= 7.04) => "CW",
        f if (f >= 14.0 && f <= 14.07) => "CW",
        f if (f >= 21.0 && f <= 21.07) => "CW",
        f if (f >= 28.0 && f <= 28.07) => "CW",
        // SSB portions
        f if (f >= 3.6 && f <= 4.0) => "LSB",
        f if (f >= 7.04 && f <= 7.3) => "LSB",
        f if (f >= 14.15 && f <= 14.35) => "USB",
        f if (f >= 21.2 && f <= 21.45) => "USB",
        f if (f >= 28.3 && f <= 29.7) => "USB",
        _ => "CW", // Default to CW for unknown
    };
    
    Ok(mode.to_string())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_rbn_spot() {
        let line = "DX de K3LR-#:     14025.0  W4GNS         CW    24 dB  33 WPM  CQ      1234Z";
        let result = parse_rbn_spot(line).unwrap();
        assert!(result.is_some());
        let (call, freq, snr, time) = result.unwrap();
        assert_eq!(call, "W4GNS");
        assert!((freq - 14025.0).abs() < 0.1);
        assert_eq!(snr, 24);
        assert_eq!(time, "1234Z");
    }

    #[test]
    fn test_frequency_to_band() {
        assert_eq!(frequency_to_band(14.025).unwrap(), "20M");
        assert_eq!(frequency_to_band(7.025).unwrap(), "40M");
        assert_eq!(frequency_to_band(28.025).unwrap(), "10M");
    }

    #[test]
    fn test_determine_mode() {
        assert_eq!(determine_mode(14.025, None).unwrap(), "CW");
        assert_eq!(determine_mode(14.250, None).unwrap(), "USB");
        assert_eq!(determine_mode(7.025, None).unwrap(), "CW");
    }
}
