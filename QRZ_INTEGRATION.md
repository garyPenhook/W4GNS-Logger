# QRZ.com Integration

Complete QRZ.com integration for the W4GNS Ham Radio Logger, providing callsign lookups and logbook management.

## Features

### Callsign Lookups
- Real-time callsign information from QRZ.com database
- Automatic lookup when callsign is entered (if auto-fetch enabled)
- Manual lookup via "QRZ↻" button on logging form
- 24-hour caching for improved performance
- Auto-fill form fields with QRZ data:
  - Operator name
  - State
  - Grid square
  - QTH (city)
  - Country

### Logbook Management
- Automatic upload of QSOs to QRZ.com logbook
- Uploads include:
  - Callsign, date, time, frequency
  - Mode, RST sent/received
  - TX power, key type (in notes)
- Non-blocking async uploads
- Doesn't interrupt contact saving if upload fails

### Configuration
All QRZ settings are managed in the Settings dialog:
- **Settings → QRZ.com tab**

## Setup Instructions

### 1. Enable QRZ Integration

Open **Settings → QRZ.com** tab:

1. Check "Enable QRZ.com integration"
2. Enter your QRZ.com username and password
3. Click "Test Connection" to verify credentials
4. Optional: Enable "Auto-fetch callsign info from QRZ"
5. Optional: Enable "Auto-upload contacts to QRZ logbook"
6. Click "Save Settings"

### 2. Using Auto-Fetch

When enabled, entering a callsign on the logging form will:
1. Wait 5 seconds for the callsign to stabilize
2. Fetch information from QRZ
3. Auto-fill available form fields

### 3. Using Manual Fetch

With QRZ enabled, a "QRZ↻" button appears next to the callsign field:
1. Enter a callsign
2. Click the "QRZ↻" button
3. Form fields will auto-fill with QRZ data

### 4. Auto-Uploading QSOs

When auto-upload is enabled:
1. Save a contact normally
2. The QSO is automatically uploaded to your QRZ.com logbook
3. Upload happens in the background (non-blocking)
4. Upload failure doesn't prevent contact from being saved locally

## API Information

### QRZ.com XML API
- Endpoint: `https://xmldata.qrz.com/xml/current/`
- Authentication: Username/password
- Session-based: Session key valid for 24 hours
- Rate limiting: Reasonable limits for automated lookups

### Data Retrieved

The QRZ callsign lookup returns:
- Callsign, name, license class
- Address (street, city, state, ZIP, country)
- Grid square, coordinates (latitude/longitude)
- Email address, website
- QTH (city), QSL manager
- Club, IOTA
- LOTW member status
- eQSL member status
- Biography (if available)

## Technical Details

### Architecture

```
QRZAPIClient (qrz_api.py)
    ↓
QRZService (qrz_service.py)
    ↓
LoggingForm (logging_form.py)
```

### Thread Safety
- API operations are thread-safe using locks
- Async operations run in background threads
- UI updates happen on main thread

### Caching
- Callsign lookups cached for 24 hours
- Cache automatically expires
- Cache can be manually cleared via service

### Error Handling
- Network errors: Logged, doesn't block UI
- Authentication errors: Shows dialog, allows retry
- Missing data: Gracefully skips unavailable fields
- Upload failures: Logged as warning, doesn't affect contact

## Files

- `src/qrz/qrz_api.py` - QRZ XML API client
- `src/qrz/qrz_service.py` - High-level service wrapper
- `src/qrz/__init__.py` - Module exports
- `src/ui/settings_editor.py` - Settings UI (updated)
- `src/ui/logging_form.py` - Logging form (updated)
- `src/config/settings.py` - Configuration (updated)

## Configuration Keys

```yaml
qrz:
  enabled: false                 # Enable/disable QRZ integration
  username: ""                   # QRZ.com username
  password: ""                   # QRZ.com password
  auto_fetch: false             # Auto-fetch callsign info when stable
  auto_upload: false            # Auto-upload contacts to logbook
```

## Example Usage (Python)

```python
from src.qrz import get_qrz_service

# Get service
service = get_qrz_service()

# Initialize (loads credentials from config)
if service.initialize():
    
    # Authenticate
    if service.authenticate():
        
        # Lookup callsign
        info = service.lookup_callsign("W4GNS")
        if info:
            print(f"Found: {info.name} in {info.state}")
        
        # Or async lookup
        def on_result(info):
            if info:
                print(f"Async: {info.name}")
        
        service.lookup_callsign_async("K0ABC", on_result)
        
        # Upload QSO
        success = service.upload_qso(
            callsign="W4GNS",
            qso_date="2025-10-25",
            time_on="12:34:56",
            freq=7.050,
            mode="CW",
            rst_sent="599",
            rst_rcvd="579",
            tx_power=5.0
        )
```

## Troubleshooting

### "Connection Failed" when testing credentials
- Check username and password
- Verify internet connection
- QRZ.com API may be temporarily unavailable
- Check application logs for details

### Callsign not found
- Verify callsign spelling
- Check if callsign is active on QRZ.com
- Some new or inactive callsigns may not be in database

### Auto-fetch not working
- Verify "Enable QRZ.com integration" is checked
- Verify "Auto-fetch callsign info from QRZ" is checked
- Check application logs for errors
- Test connection in settings

### Upload not appearing in QRZ logbook
- Verify "Enable QRZ.com integration" is checked
- Verify "Auto-upload contacts to QRZ logbook" is checked
- Check that frequency and mode are valid
- Check QRZ.com logbook directly
- Check application logs for upload errors

## Limitations

- QRZ.com API requires valid account
- Not all callsigns are in QRZ database
- Some QRZ fields may be incomplete
- Session key expires after 24 hours (auto-refreshed)
- Logbook uploads follow QRZ.com validation rules

## Future Enhancements

- QRZ subscription photo display
- Download logbook from QRZ for comparison
- Batch upload of existing contacts
- LOTW status integration
- Award tracking from QRZ data

## References

- QRZ.com: https://www.qrz.com
- QRZ XML API: https://www.qrz.com/page/api_details
- ADIF format: https://www.adif.org
