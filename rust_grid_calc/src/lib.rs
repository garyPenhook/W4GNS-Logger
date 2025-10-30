use pyo3::prelude::*;
use std::f64::consts::PI;

mod awards;
use awards::{
    calculate_centurion_progress, calculate_tribune_progress,
    calculate_qrp_mpw_progress, count_unique_states, count_unique_prefixes
};

mod spot_matcher;
use spot_matcher::{
    batch_filter_spots, parse_rbn_spot, frequency_to_band, determine_mode
};

mod adif;
use adif::{
    parse_adi, parse_fields, export_adi, format_record, 
    batch_parse_records, validate_record
};

/// Convert degrees to radians
#[inline]
fn deg_to_rad(degrees: f64) -> f64 {
    degrees * PI / 180.0
}

/// Convert Maidenhead grid square to latitude/longitude
/// 
/// Supports 4, 6, 8, or 10 character grid squares
/// Returns (latitude, longitude) in degrees
fn grid_to_latlon(grid: &str) -> PyResult<(f64, f64)> {
    let grid = grid.to_uppercase();
    let chars: Vec<char> = grid.chars().collect();
    
    if chars.len() < 4 || chars.len() > 10 {
        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
            format!("Grid square must be 4, 6, 8, or 10 characters, got {}", chars.len())
        ));
    }

    // Field (first 2 characters): 20° longitude, 10° latitude
    let lon_field = (chars[0] as i32 - 'A' as i32) as f64 * 20.0;
    let lat_field = (chars[1] as i32 - 'A' as i32) as f64 * 10.0;

    // Square (characters 3-4): 2° longitude, 1° latitude
    let lon_square = chars[2].to_digit(10).ok_or_else(|| {
        PyErr::new::<pyo3::exceptions::PyValueError, _>("Invalid grid square digit")
    })? as f64 * 2.0;
    let lat_square = chars[3].to_digit(10).ok_or_else(|| {
        PyErr::new::<pyo3::exceptions::PyValueError, _>("Invalid grid square digit")
    })? as f64 * 1.0;

    let mut lon = -180.0 + lon_field + lon_square;
    let mut lat = -90.0 + lat_field + lat_square;

    // Subsquare (characters 5-6): 5' longitude, 2.5' latitude
    if chars.len() >= 6 {
        let lon_subsq = (chars[4] as i32 - 'A' as i32) as f64 * (2.0 / 24.0);
        let lat_subsq = (chars[5] as i32 - 'A' as i32) as f64 * (1.0 / 24.0);
        lon += lon_subsq;
        lat += lat_subsq;
    }

    // Extended square (characters 7-8)
    if chars.len() >= 8 {
        let lon_ext = chars[6].to_digit(10).ok_or_else(|| {
            PyErr::new::<pyo3::exceptions::PyValueError, _>("Invalid extended square digit")
        })? as f64 * (2.0 / 240.0);
        let lat_ext = chars[7].to_digit(10).ok_or_else(|| {
            PyErr::new::<pyo3::exceptions::PyValueError, _>("Invalid extended square digit")
        })? as f64 * (1.0 / 240.0);
        lon += lon_ext;
        lat += lat_ext;
    }

    // Super extended (characters 9-10)
    if chars.len() >= 10 {
        let lon_super = (chars[8] as i32 - 'A' as i32) as f64 * (2.0 / 5760.0);
        let lat_super = (chars[9] as i32 - 'A' as i32) as f64 * (1.0 / 5760.0);
        lon += lon_super;
        lat += lat_super;
    }

    // Center of grid square
    lon += 1.0;
    lat += 0.5;

    Ok((lat, lon))
}

/// Calculate great circle distance using Haversine formula
/// 
/// Args:
///     grid1: First Maidenhead grid square
///     grid2: Second Maidenhead grid square
/// 
/// Returns:
///     Distance in kilometers
#[pyfunction]
fn calculate_distance(grid1: &str, grid2: &str) -> PyResult<f64> {
    let (lat1, lon1) = grid_to_latlon(grid1)?;
    let (lat2, lon2) = grid_to_latlon(grid2)?;

    // Earth radius in kilometers
    const EARTH_RADIUS: f64 = 6371.0;

    let lat1_rad = deg_to_rad(lat1);
    let lat2_rad = deg_to_rad(lat2);
    let delta_lat = deg_to_rad(lat2 - lat1);
    let delta_lon = deg_to_rad(lon2 - lon1);

    let a = (delta_lat / 2.0).sin().powi(2)
        + lat1_rad.cos() * lat2_rad.cos() * (delta_lon / 2.0).sin().powi(2);
    
    let c = 2.0 * a.sqrt().atan2((1.0 - a).sqrt());
    let distance = EARTH_RADIUS * c;

    Ok(distance)
}

/// Batch calculate distances for multiple grid pairs
/// 
/// Args:
///     home_grid: Home station grid square
///     grids: List of contact grid squares
/// 
/// Returns:
///     List of distances in kilometers (None for invalid grids)
#[pyfunction]
fn batch_calculate_distances(home_grid: &str, grids: Vec<String>) -> PyResult<Vec<Option<f64>>> {
    let mut results = Vec::with_capacity(grids.len());
    
    for grid in grids.iter() {
        match calculate_distance(home_grid, grid) {
            Ok(dist) => results.push(Some(dist)),
            Err(_) => results.push(None),
        }
    }
    
    Ok(results)
}

/// Calculate bearing from grid1 to grid2
/// 
/// Returns:
///     Bearing in degrees (0-360)
#[pyfunction]
fn calculate_bearing(grid1: &str, grid2: &str) -> PyResult<f64> {
    let (lat1, lon1) = grid_to_latlon(grid1)?;
    let (lat2, lon2) = grid_to_latlon(grid2)?;

    let lat1_rad = deg_to_rad(lat1);
    let lat2_rad = deg_to_rad(lat2);
    let delta_lon = deg_to_rad(lon2 - lon1);

    let y = delta_lon.sin() * lat2_rad.cos();
    let x = lat1_rad.cos() * lat2_rad.sin()
        - lat1_rad.sin() * lat2_rad.cos() * delta_lon.cos();
    
    let mut bearing = y.atan2(x).to_degrees();
    
    // Normalize to 0-360
    if bearing < 0.0 {
        bearing += 360.0;
    }
    
    Ok(bearing)
}

/// Python module
#[pymodule]
fn rust_grid_calc(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Grid/distance functions
    m.add_function(wrap_pyfunction!(calculate_distance, m)?)?;
    m.add_function(wrap_pyfunction!(batch_calculate_distances, m)?)?;
    m.add_function(wrap_pyfunction!(calculate_bearing, m)?)?;
    
    // Award calculation functions
    m.add_function(wrap_pyfunction!(calculate_centurion_progress, m)?)?;
    m.add_function(wrap_pyfunction!(calculate_tribune_progress, m)?)?;
    m.add_function(wrap_pyfunction!(calculate_qrp_mpw_progress, m)?)?;
    m.add_function(wrap_pyfunction!(count_unique_states, m)?)?;
    m.add_function(wrap_pyfunction!(count_unique_prefixes, m)?)?;
    
    // Spot matching functions
    m.add_function(wrap_pyfunction!(batch_filter_spots, m)?)?;
    m.add_function(wrap_pyfunction!(parse_rbn_spot, m)?)?;
    m.add_function(wrap_pyfunction!(frequency_to_band, m)?)?;
    m.add_function(wrap_pyfunction!(determine_mode, m)?)?;
    
    // ADIF parsing and export functions
    m.add_function(wrap_pyfunction!(parse_adi, m)?)?;
    m.add_function(wrap_pyfunction!(parse_fields, m)?)?;
    m.add_function(wrap_pyfunction!(export_adi, m)?)?;
    m.add_function(wrap_pyfunction!(format_record, m)?)?;
    m.add_function(wrap_pyfunction!(batch_parse_records, m)?)?;
    m.add_function(wrap_pyfunction!(validate_record, m)?)?;
    
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_grid_to_latlon() {
        // FM06ew (W4GNS location)
        let (lat, lon) = grid_to_latlon("FM06ew").unwrap();
        assert!((lat - 36.229).abs() < 0.1);
        assert!((lon - (-86.729)).abs() < 0.1);
    }

    #[test]
    fn test_distance_calculation() {
        // FM06ew to EM29nf (roughly Nashville to Atlanta area)
        let dist = calculate_distance("FM06ew", "EM29nf").unwrap();
        assert!(dist > 900.0 && dist < 1100.0); // ~1000 km
    }

    #[test]
    fn test_bearing() {
        let bearing = calculate_bearing("FM06ew", "EM29nf").unwrap();
        assert!(bearing >= 0.0 && bearing <= 360.0);
    }
}
