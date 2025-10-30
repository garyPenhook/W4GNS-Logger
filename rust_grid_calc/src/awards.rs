use pyo3::prelude::*;
use std::collections::{HashMap, HashSet};

/// Extract base SKCC number without suffixes (C, T, S, xN)
fn extract_base_skcc(skcc: &str) -> Option<String> {
    let skcc = skcc.trim();
    if skcc.is_empty() {
        return None;
    }
    
    let mut base = skcc.split_whitespace().next()?.to_string();
    
    // Remove letter suffix (C, T, S)
    if let Some(last_char) = base.chars().last() {
        if last_char == 'C' || last_char == 'T' || last_char == 'S' {
            base.pop();
        }
    }
    
    // Remove x multiplier
    if let Some(pos) = base.find('x') {
        base = base[..pos].to_string();
    }
    
    // Verify it's a number
    if base.chars().all(|c| c.is_ascii_digit()) && !base.is_empty() {
        Some(base)
    } else {
        None
    }
}

/// Calculate Centurion award progress
/// 
/// Returns: (unique_members, member_details)
#[pyfunction]
pub fn calculate_centurion_progress(contacts: Vec<(String, String, String, String, String, String)>) -> PyResult<(usize, Vec<(String, String, String, String)>)> {
    let mut unique_members: HashSet<String> = HashSet::new();
    let mut member_details: HashMap<String, (String, String, String)> = HashMap::new();
    
    for (callsign, skcc_number, mode, key_type, qso_date, band) in contacts {
        // Filter: CW mode and mechanical key
        if mode != "CW" {
            continue;
        }
        
        if !["STRAIGHT", "BUG", "SIDESWIPER"].contains(&key_type.as_str()) {
            continue;
        }
        
        // Extract base SKCC number
        if let Some(base_num) = extract_base_skcc(&skcc_number) {
            unique_members.insert(base_num.clone());
            
            // Store first occurrence
            member_details.entry(base_num)
                .or_insert((callsign, qso_date, band));
        }
    }
    
    let count = unique_members.len();
    let details: Vec<(String, String, String, String)> = member_details
        .into_iter()
        .map(|(skcc, (call, date, band))| (skcc, call, date, band))
        .collect();
    
    Ok((count, details))
}

/// Calculate Tribune award progress
/// 
/// Returns: (unique_tribunes, tribune_details)
#[pyfunction]
pub fn calculate_tribune_progress(contacts: Vec<(String, String, String, String, String, String)>) -> PyResult<(usize, Vec<(String, String, String, String)>)> {
    let mut unique_tribunes: HashSet<String> = HashSet::new();
    let mut tribune_details: HashMap<String, (String, String, String)> = HashMap::new();
    
    for (callsign, skcc_number, mode, key_type, qso_date, band) in contacts {
        // Filter: CW mode and mechanical key
        if mode != "CW" {
            continue;
        }
        
        if !["STRAIGHT", "BUG", "SIDESWIPER"].contains(&key_type.as_str()) {
            continue;
        }
        
        // Check if Tribune or Senator (has T or S suffix)
        let skcc = skcc_number.trim();
        if skcc.ends_with('T') || skcc.ends_with('S') {
            if let Some(base_num) = extract_base_skcc(skcc) {
                unique_tribunes.insert(base_num.clone());
                
                tribune_details.entry(base_num)
                    .or_insert((callsign, qso_date, band));
            }
        }
    }
    
    let count = unique_tribunes.len();
    let details: Vec<(String, String, String, String)> = tribune_details
        .into_iter()
        .map(|(skcc, (call, date, band))| (skcc, call, date, band))
        .collect();
    
    Ok((count, details))
}

/// Calculate QRP MPW award progress
/// 
/// Args: List of (callsign, tx_power, distance_km, mode, date, band)
/// Returns: (total_qualifying, best_mpw, average_mpw, qualifying_contacts)
#[pyfunction]
pub fn calculate_qrp_mpw_progress(
    contacts: Vec<(String, f64, f64, String, String, String)>
) -> PyResult<(usize, f64, f64, Vec<(String, String, String, f64, f64, f64)>)> {
    const KM_TO_MILES: f64 = 0.621371;
    const MPW_THRESHOLD: f64 = 1000.0;
    const QRP_POWER: f64 = 5.0;
    
    let mut qualifying = Vec::new();
    let mut total_mpw = 0.0;
    
    for (callsign, tx_power, distance_km, mode, date, band) in contacts {
        // Filter: QRP power (<=5W), CW mode, has distance
        if tx_power > QRP_POWER || mode != "CW" || distance_km <= 0.0 {
            continue;
        }
        
        let distance_mi = distance_km * KM_TO_MILES;
        let mpw = distance_mi / tx_power;
        
        if mpw >= MPW_THRESHOLD {
            qualifying.push((callsign, date, band, distance_mi, tx_power, mpw));
            total_mpw += mpw;
        }
    }
    
    let count = qualifying.len();
    let best_mpw = qualifying.iter()
        .map(|(_, _, _, _, _, mpw)| mpw)
        .fold(0.0f64, |a, &b| a.max(b));
    
    let avg_mpw = if count > 0 {
        total_mpw / count as f64
    } else {
        0.0
    };
    
    Ok((count, best_mpw, avg_mpw, qualifying))
}

/// Count unique states worked
#[pyfunction]
pub fn count_unique_states(states: Vec<String>) -> PyResult<usize> {
    let unique: HashSet<String> = states
        .into_iter()
        .filter(|s| !s.is_empty())
        .collect();
    Ok(unique.len())
}

/// Count unique prefixes from callsigns
#[pyfunction]
pub fn count_unique_prefixes(callsigns: Vec<String>) -> PyResult<usize> {
    let mut prefixes = HashSet::new();
    
    for call in callsigns {
        if let Some(prefix) = extract_prefix(&call) {
            prefixes.insert(prefix);
        }
    }
    
    Ok(prefixes.len())
}

/// Extract prefix from callsign (e.g., "W4GNS" -> "W4")
fn extract_prefix(callsign: &str) -> Option<String> {
    let call = callsign.trim().to_uppercase();
    
    // Handle special prefixes like VE, VA, VK, etc.
    if call.len() >= 2 {
        let first_two = &call[..2];
        if first_two.starts_with('V') || first_two.starts_with('Z') {
            return Some(first_two.to_string());
        }
    }
    
    // Standard prefix: letter(s) + digit
    let digits: Vec<_> = call.char_indices()
        .filter(|(_, c)| c.is_ascii_digit())
        .collect();
    
    if let Some((pos, _)) = digits.first() {
        Some(call[..=*pos].to_string())
    } else {
        None
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_extract_base_skcc() {
        assert_eq!(extract_base_skcc("14947T"), Some("14947".to_string()));
        assert_eq!(extract_base_skcc("14947"), Some("14947".to_string()));
        assert_eq!(extract_base_skcc("123C"), Some("123".to_string()));
        assert_eq!(extract_base_skcc("123S"), Some("123".to_string()));
        assert_eq!(extract_base_skcc("456x2"), Some("456".to_string()));
        assert_eq!(extract_base_skcc("789Cx5"), Some("789".to_string()));
    }

    #[test]
    fn test_extract_prefix() {
        assert_eq!(extract_prefix("W4GNS"), Some("W4".to_string()));
        assert_eq!(extract_prefix("VE3SVQ"), Some("VE".to_string()));
        assert_eq!(extract_prefix("K1SP"), Some("K1".to_string()));
        assert_eq!(extract_prefix("G4AFU"), Some("G4".to_string()));
    }
}
