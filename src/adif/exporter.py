"""
ADIF Exporter Module

Handles exporting contacts to ADIF (ADI and ADX) format files.
Implements ADIF 3.x specification compliance.
"""

import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class ADIFExporter:
    """Exporter for ADIF files (ADI text format)

    Exports in SKCCLogger format to ensure compatibility.
    Supports ADIF 3.1.5 specification for exporting contact records.
    Reference: https://adif.org/315/ADIF_315.htm
    """

    # Key type abbreviations for APP_SKCCLOGGER_KEYTYPE (SKCCLogger format)
    KEY_TYPE_ABBREV = {
        'STRAIGHT': 'SK',
        'SIDESWIPER': 'SW',
        'BUG': 'BG',
        'KEYER': 'KY',
    }

    # Field order for SKCCLogger format (matches SKCC Logger exactly)
    FIELD_ORDER = [
        'BAND',
        'CALL',
        'COMMENT',
        'COUNTRY',
        'DXCC',
        'FREQ',
        'APP_SKCCLOGGER_KEYTYPE',
        'MODE',
        'MY_GRIDSQUARE',
        'NAME',
        'OPERATOR',
        'QSO_DATE',
        'QTH',
        'RST_RCVD',
        'RST_SENT',
        'SKCC',
        'STATE',
        'STATION_CALLSIGN',
        'TIME_OFF',
        'TIME_ON',
        'TX_PWR',
        'RX_PWR',
        'CONTEST_ID',
    ]

    # Field mappings from Contact model to ADIF field names
    FIELD_MAPPINGS = {
        # Core QSO Fields
        'callsign': 'CALL',
        'qso_date': 'QSO_DATE',
        'time_on': 'TIME_ON',
        'time_off': 'TIME_OFF',
        'band': 'BAND',
        'frequency': 'FREQ',
        'freq_rx': 'FREQ_RX',
        'mode': 'MODE',
        'rst_sent': 'RST_SENT',
        'rst_rcvd': 'RST_RCVD',
        'tx_power': 'TX_PWR',
        'rx_power': 'RX_PWR',

        # Grid/Location Fields
        'my_gridsquare': 'MY_GRIDSQUARE',
        'gridsquare': 'GRIDSQUARE',
        'my_city': 'MY_CITY',
        'my_country': 'MY_COUNTRY',
        'my_state': 'MY_STATE',
        'name': 'NAME',
        'qth': 'QTH',
        'country': 'COUNTRY',

        # Geographic/Award Fields
        'dxcc': 'DXCC',
        'cqz': 'CQZ',
        'ituz': 'ITUZ',
        'state': 'STATE',
        'county': 'COUNTY',
        'arrl_sect': 'ARRL_SECT',
        'iota': 'IOTA',
        'iota_island_id': 'IOTA_ISLAND_ID',
        'sota_ref': 'SOTA_REF',
        'pota_ref': 'POTA_REF',
        'vucc_grids': 'VUCC_GRIDS',

        # Station/Equipment Fields
        'operator': 'OPERATOR',
        'station_callsign': 'STATION_CALLSIGN',
        'my_rig': 'MY_RIG',
        'my_rig_make': 'MY_RIG_MAKE',
        'my_rig_model': 'MY_RIG_MODEL',
        'rig_make': 'RIG_MAKE',
        'rig_model': 'RIG_MODEL',
        'my_antenna': 'MY_ANTENNA',
        'my_antenna_make': 'MY_ANTENNA_MAKE',
        'my_antenna_model': 'MY_ANTENNA_MODEL',
        'antenna_make': 'ANT_MAKE',
        'antenna_model': 'ANT_MODEL',

        # SKCC Award Fields (Important!)
        'skcc_number': 'SKCC',
        'key_type': 'APP_SKCCLOGGER_KEYTYPE',  # Using app field for SKCCLogger compatibility

        # Propagation/Technical Fields
        'propagation_mode': 'PROPAGATION_MODE',
        'sat_name': 'SAT_NAME',
        'sat_mode': 'SAT_MODE',
        'a_index': 'A_INDEX',
        'k_index': 'K_INDEX',
        'sfi': 'SFI',
        'antenna_az': 'ANTENNA_AZ',
        'antenna_el': 'ANTENNA_EL',
        'distance': 'DISTANCE',
        'latitude': 'LATITUDE',
        'longitude': 'LONGITUDE',

        # QSL/Confirmation Fields
        'qsl_rcvd': 'QSL_RCVD',
        'qsl_sent': 'QSL_SENT',
        'qsl_rcvd_date': 'QSL_RCVD_DATE',
        'qsl_sent_date': 'QSL_SENT_DATE',
        'qsl_via': 'QSL_VIA',
        'lotw_qsl_rcvd': 'LOTW_QSL_RCVD',
        'lotw_qsl_sent': 'LOTW_QSL_SENT',
        'eqsl_qsl_rcvd': 'EQSL_QSL_RCVD',
        'eqsl_qsl_sent': 'EQSL_QSL_SENT',
        'clublog_status': 'CLUBLOG_QSO_UPLOAD_STATUS',

        # Notes/Comments
        'notes': 'NOTES',
        'comment': 'COMMENT',
        'qslmsg': 'QSLMSG',

        # Contest/Award Fields
        'contest_id': 'CONTEST_ID',
        'class_field': 'CLASS',
        'check': 'CHECK',
    }

    def __init__(self):
        """Initialize ADIF exporter"""
        pass

    def export_to_file(
        self,
        filename: str,
        contacts: List[Any],
        my_skcc: Optional[str] = None,
        include_fields: Optional[List[str]] = None,
        my_callsign: Optional[str] = None
    ) -> None:
        """Export contacts to ADIF file in SKCCLogger format

        Args:
            filename: Output file path
            contacts: List of Contact objects to export
            my_skcc: Operator's SKCC number
            include_fields: List of field names to include. None = all non-empty fields
            my_callsign: Operator's callsign

        Raises:
            IOError: If file cannot be written
            ValueError: If contacts list is empty
        """
        if not contacts:
            raise ValueError("No contacts to export")

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                # Write ADIF header with record count
                header = self._build_header(my_skcc, len(contacts), my_callsign)
                f.write(header)
                f.write('\n')

                # Write records
                for contact in contacts:
                    record = self._build_record(contact, include_fields)
                    f.write(record)
                    f.write('\n')

            logger.info(f"Exported {len(contacts)} contacts to {filename}")

        except IOError as e:
            logger.error(f"Failed to write ADIF file: {e}")
            raise

    def _build_header(self, my_skcc: Optional[str] = None, record_count: int = 0, my_callsign: Optional[str] = None) -> str:
        """Build ADIF header in SKCCLogger format

        Args:
            my_skcc: Operator's SKCC number
            record_count: Number of records in the log
            my_callsign: Operator's callsign

        Returns:
            ADIF header string
        """
        header_lines = []

        # SKCCLogger format header
        header_lines.append("ADIF Log Created by SKCCLogger")
        header_lines.append("Version: v03.01.03 64-bit Linux")
        header_lines.append("Compiler: 2024r1.1")
        header_lines.append("Build: 2024-04-27 at 13:16:49 ET")
        header_lines.append("")

        # Callsign line (empty if not provided)
        header_lines.append(f"Callsign: {my_callsign if my_callsign else ''}")

        # SKCC number line
        header_lines.append(f"SKCC Nr.: {my_skcc if my_skcc else ''}")

        # Log creation timestamp
        from datetime import timezone
        now = datetime.now(timezone.utc)
        log_created = now.strftime('%Y-%m-%d %H:%M:%SZ')
        header_lines.append(f"Log Created: {log_created}")

        # Record count
        header_lines.append(f"Record Count: {record_count}")

        # Log filename (placeholder - actual filename not needed per spec)
        header_lines.append("Log Filename: W4GNS SKCC Logger Export")

        header_lines.append("")
        header_lines.append("<EOH>")

        return '\n'.join(header_lines)

    def _build_record(
        self,
        contact: Any,
        include_fields: Optional[List[str]] = None
    ) -> str:
        """Build ADIF record from contact object in SKCCLogger format

        Records are pretty-printed with one field per line, in SKCCLogger field order.

        Args:
            contact: Contact object
            include_fields: List of field names to include. None = all non-empty fields

        Returns:
            ADIF record string (one field per line)
        """
        # Build a dict of all field values
        field_values = {}

        # Required fields first
        required = ['callsign', 'qso_date', 'time_on', 'band', 'mode']

        for field_name in required:
            value = getattr(contact, field_name, None)
            if value is not None:
                adif_name = self.FIELD_MAPPINGS.get(field_name)
                if adif_name:
                    # Special handling for time fields (convert HHMM to HHMMSS)
                    if field_name in ['time_on', 'time_off']:
                        value = self._convert_time_format(value)
                    # Special handling for key type (convert to abbreviation)
                    elif field_name == 'key_type':
                        value = self.KEY_TYPE_ABBREV.get(value, value)
                    field_values[adif_name] = value

        # Optional fields
        for db_field, adif_field in self.FIELD_MAPPINGS.items():
            if db_field not in required:
                # Check if we should include this field
                if include_fields is not None and db_field not in include_fields:
                    continue

                value = getattr(contact, db_field, None)
                if value is not None and value != '':
                    # Special handling for time fields (convert HHMM to HHMMSS)
                    if db_field in ['time_on', 'time_off']:
                        value = self._convert_time_format(value)
                    # Special handling for key type (convert to abbreviation)
                    elif db_field == 'key_type':
                        value = self.KEY_TYPE_ABBREV.get(value, value)
                    field_values[adif_field] = value

        # Build record in field order (SKCCLogger format)
        fields = []
        for adif_field in self.FIELD_ORDER:
            if adif_field in field_values:
                fields.append(self._format_field(adif_field, field_values[adif_field]))

        # Add any remaining fields not in FIELD_ORDER
        for adif_field, value in field_values.items():
            if adif_field not in self.FIELD_ORDER:
                fields.append(self._format_field(adif_field, value))

        # End of record
        fields.append("<EOR>")

        # Return pretty-printed format (each field on its own line)
        return '\n'.join(fields)

    def _format_field(self, field_name: str, value: Any) -> str:
        """Format a single ADIF field

        Format: <FIELDNAME:LENGTH>VALUE

        Args:
            field_name: ADIF field name (e.g., "CALL")
            value: Field value

        Returns:
            Formatted ADIF field string
        """
        # Convert value to string
        if isinstance(value, bool):
            value_str = 'Y' if value else 'N'
        elif isinstance(value, (int, float)):
            value_str = str(value)
        else:
            value_str = str(value)

        # Get length in bytes (UTF-8)
        value_bytes = value_str.encode('utf-8')
        length = len(value_bytes)

        return f"<{field_name}:{length}>{value_str}"

    def _convert_time_format(self, time_str: str) -> str:
        """Convert time from HHMM to HHMMSS format

        Args:
            time_str: Time in HHMM format (e.g., "1704")

        Returns:
            Time in HHMMSS format (e.g., "170400")
        """
        if not time_str:
            return time_str

        # If already 6 digits, return as-is
        if len(str(time_str)) >= 6:
            return str(time_str)

        # Convert HHMM to HHMMSS by adding :00 seconds
        time_str = str(time_str).strip()
        if len(time_str) == 4:
            return f"{time_str}00"
        elif len(time_str) == 6:
            return time_str
        else:
            # Handle unexpected formats gracefully
            return time_str.ljust(6, '0')[:6]

    def export_adi(
        self,
        filename: str,
        contacts: List[Any],
        my_skcc: Optional[str] = None,
        my_callsign: Optional[str] = None
    ) -> None:
        """Export contacts to ADI (text) format in SKCCLogger format

        Args:
            filename: Output file path
            contacts: List of Contact objects
            my_skcc: Operator's SKCC number
            my_callsign: Operator's callsign
        """
        self.export_to_file(filename, contacts, my_skcc, my_callsign=my_callsign)

    def export_adx(
        self,
        filename: str,
        contacts: List[Any],
        my_skcc: Optional[str] = None
    ) -> None:
        """Export contacts to ADX (XML) format

        Note: This is a placeholder. ADX format is XML-based and more complex.
        For now, we recommend using ADI format which is simpler and more widely supported.

        Args:
            filename: Output file path
            contacts: List of Contact objects
            my_skcc: Operator's SKCC number
        """
        raise NotImplementedError("ADX export not yet implemented. Please use ADI format.")
