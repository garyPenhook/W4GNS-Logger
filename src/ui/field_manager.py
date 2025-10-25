"""
UI Field Manager

Manages which ADIF fields are displayed in the GUI.
Users can enable/disable extended fields via checkboxes.
"""

from typing import List, Dict, Any


class FieldManager:
    """Manages contact field display in GUI"""

    # Basic fields - always shown
    BASIC_FIELDS = [
        ("callsign", "Callsign", "QSO"),
        ("qso_date", "Date", "QSO"),
        ("time_on", "Time", "QSO"),
        ("band", "Band", "QSO"),
        ("mode", "Mode", "QSO"),
    ]

    # Extended field categories with their fields
    EXTENDED_FIELDS = {
        "QSO Details": [
            ("time_off", "Time Off"),
            ("frequency", "Frequency (MHz)"),
            ("freq_rx", "RX Frequency"),
            ("rst_sent", "RST Sent"),
            ("rst_rcvd", "RST Received"),
            ("tx_power", "TX Power (W)"),
            ("rx_power", "RX Power (W)"),
        ],
        "Location": [
            ("gridsquare", "Grid Square"),
            ("my_gridsquare", "My Grid"),
            ("qth", "QTH"),
            ("name", "Operator Name"),
            ("country", "Country"),
            ("state", "State"),
            ("county", "County"),
        ],
        "Station": [
            ("station_callsign", "Station Call"),
            ("operator", "Operator"),
            ("rig_make", "Rig Make"),
            ("rig_model", "Rig Model"),
            ("antenna_make", "Antenna Make"),
            ("antenna_model", "Antenna Model"),
        ],
        "Awards": [
            ("dxcc", "DXCC"),
            ("arrl_sect", "ARRL Section"),
            ("iota", "IOTA"),
            ("sota_ref", "SOTA"),
            ("pota_ref", "POTA"),
            ("vucc_grids", "VUCC Grids"),
        ],
        "QSL": [
            ("qsl_rcvd", "QSL Received"),
            ("qsl_sent", "QSL Sent"),
            ("qsl_rcvd_date", "QSL RX Date"),
            ("qsl_sent_date", "QSL TX Date"),
            ("lotw_qsl_rcvd", "LoTW RX"),
            ("eqsl_qsl_rcvd", "eQSL RX"),
        ],
        "Technical": [
            ("propagation_mode", "Propagation"),
            ("sat_name", "Satellite"),
            ("a_index", "A-Index"),
            ("k_index", "K-Index"),
            ("sfi", "SFI"),
            ("antenna_az", "Antenna AZ"),
            ("antenna_el", "Antenna EL"),
            ("distance", "Distance (km)"),
        ],
        "Notes": [
            ("notes", "Notes"),
            ("comment", "Comment"),
            ("qslmsg", "QSL Message"),
        ],
    }

    @classmethod
    def get_basic_fields(cls) -> List[Dict[str, str]]:
        """Get basic fields that are always shown"""
        return [
            {"field_name": f[0], "display_name": f[1], "category": f[2]}
            for f in cls.BASIC_FIELDS
        ]

    @classmethod
    def get_extended_fields(cls) -> Dict[str, List[Dict[str, str]]]:
        """Get extended fields organized by category"""
        result = {}
        for category, fields in cls.EXTENDED_FIELDS.items():
            result[category] = [
                {"field_name": f[0], "display_name": f[1], "category": category}
                for f in fields
            ]
        return result

    @classmethod
    def get_all_fields(cls) -> List[Dict[str, str]]:
        """Get all fields (basic + extended)"""
        all_fields = cls.get_basic_fields()
        for category_fields in cls.get_extended_fields().values():
            all_fields.extend(category_fields)
        return all_fields

    @classmethod
    def get_list_columns(cls, user_preferences: Dict[str, bool]) -> List[str]:
        """
        Get field names to display in contacts list based on user preferences

        Args:
            user_preferences: Dict of field_name: enabled (boolean)

        Returns:
            List of field names to display
        """
        # Always include basic fields
        columns = [f[0] for f in cls.BASIC_FIELDS]

        # Add extended fields that user enabled
        for category, fields in cls.EXTENDED_FIELDS.items():
            for field_name, display_name in fields:
                if user_preferences.get(field_name, False):
                    columns.append(field_name)

        return columns

    @classmethod
    def get_form_fields(cls, user_preferences: Dict[str, bool]) -> Dict[str, List[str]]:
        """
        Get field names organized by category for contact form

        Args:
            user_preferences: Dict of field_name: enabled (boolean)

        Returns:
            Dict of category: [field_names]
        """
        form_fields = {}

        # Basic fields section
        form_fields["Basic Information"] = [f[0] for f in cls.BASIC_FIELDS]

        # Extended fields by category
        for category, fields in cls.EXTENDED_FIELDS.items():
            enabled_fields = [
                f[0] for f in fields
                if user_preferences.get(f[0], False)
            ]
            if enabled_fields:
                form_fields[category] = enabled_fields

        return form_fields

    @classmethod
    def get_field_display_name(cls, field_name: str) -> str:
        """Get human-readable display name for a field"""
        # Check basic fields
        for f_name, display_name, _ in cls.BASIC_FIELDS:
            if f_name == field_name:
                return display_name

        # Check extended fields
        for category, fields in cls.EXTENDED_FIELDS.items():
            for f_name, display_name in fields:
                if f_name == field_name:
                    return display_name

        # Default: convert underscore to title case
        return field_name.replace("_", " ").title()
