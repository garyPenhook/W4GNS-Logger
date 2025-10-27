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

    Supports ADIF 3.1.5 specification for exporting contact records.
    Reference: https://adif.org/315/ADIF_315.htm
    """

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
        'key_type': 'KEY_TYPE',

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
        include_fields: Optional[List[str]] = None
    ) -> None:
        """Export contacts to ADIF file

        Args:
            filename: Output file path
            contacts: List of Contact objects to export
            my_skcc: Operator's SKCC number (will be included as MY_SKCC)
            include_fields: List of field names to include. None = all non-empty fields

        Raises:
            IOError: If file cannot be written
            ValueError: If contacts list is empty
        """
        if not contacts:
            raise ValueError("No contacts to export")

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                # Write ADIF header
                header = self._build_header(my_skcc)
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

    def _build_header(self, my_skcc: Optional[str] = None) -> str:
        """Build ADIF header

        Args:
            my_skcc: Operator's SKCC number

        Returns:
            ADIF header string
        """
        header_lines = []
        header_lines.append("ADIF specification by N0TA Version 3.1.5")
        header_lines.append(f"<PROGRAMID:17>W4GNS SKCC Logger")
        header_lines.append(f"<PROGRAMVERSION:6>1.0.0")
        header_lines.append(f"<CREATED_TIMESTAMP:{len(datetime.utcnow().isoformat())}>{datetime.utcnow().isoformat()}")

        # Include MY_SKCC if provided
        if my_skcc:
            skcc_field = self._format_field('MY_SKCC', my_skcc)
            header_lines.append(skcc_field)

        header_lines.append("<EOH>")

        return '\n'.join(header_lines)

    def _build_record(
        self,
        contact: Any,
        include_fields: Optional[List[str]] = None
    ) -> str:
        """Build ADIF record from contact object

        Args:
            contact: Contact object
            include_fields: List of field names to include. None = all non-empty fields

        Returns:
            ADIF record string
        """
        fields = []

        # Required fields first
        required = ['callsign', 'qso_date', 'time_on', 'band', 'mode']

        for field_name in required:
            value = getattr(contact, field_name, None)
            if value is not None:
                adif_name = self.FIELD_MAPPINGS.get(field_name)
                if adif_name:
                    fields.append(self._format_field(adif_name, value))

        # Optional fields
        for db_field, adif_field in self.FIELD_MAPPINGS.items():
            if db_field not in required:
                # Check if we should include this field
                if include_fields is not None and db_field not in include_fields:
                    continue

                value = getattr(contact, db_field, None)
                if value is not None and value != '':
                    fields.append(self._format_field(adif_field, value))

        # End of record
        fields.append("<EOR>")

        return ''.join(fields)

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

    def export_adi(
        self,
        filename: str,
        contacts: List[Any],
        my_skcc: Optional[str] = None
    ) -> None:
        """Export contacts to ADI (text) format

        Args:
            filename: Output file path
            contacts: List of Contact objects
            my_skcc: Operator's SKCC number
        """
        self.export_to_file(filename, contacts, my_skcc)

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
