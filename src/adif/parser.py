"""
ADIF Parser Module

Handles parsing of ADIF (ADI and ADX) format files.
Implements ADIF 3.x specification compliance.
"""

import logging
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)


class ADIFParser:
    """Parser for ADIF files (both ADI text and ADX XML formats)

    Supports ADIF 3.1.5 specification with all standard fields.
    Reference: https://adif.org/315/ADIF_315.htm
    """

    # ADIF field pattern: <FIELDNAME:length>value
    FIELD_PATTERN = re.compile(r"<([A-Z_0-9]+):(\d+)>([^<]*)")

    # Required fields per ADIF spec
    REQUIRED_FIELDS = {
        "CALL",           # Contacted station callsign
        "QSO_DATE",       # Date of contact (YYYYMMDD)
        "TIME_ON",        # Time of contact (HHMM)
        "BAND",           # Band of contact or FREQ
        "MODE"            # Operating mode
    }

    # ADIF 3.1.5 Core QSO Fields
    CORE_QSO_FIELDS = {
        "CALL", "QSO_DATE", "TIME_ON", "TIME_OFF", "BAND", "FREQ",
        "FREQ_RX", "MODE", "RST_SENT", "RST_RCVD", "TX_PWR", "RX_PWR",
        "BAND_RX", "MODE_RX"
    }

    # Station Information Fields
    STATION_INFO_FIELDS = {
        "OPERATOR", "STATION_CALLSIGN", "MY_GRIDSQUARE", "GRIDSQUARE",
        "NAME", "QTH", "MY_CITY", "MY_COUNTRY", "MY_COUNTY", "MY_STATE",
        "MY_POSTAL_CODE", "MY_RIG", "MY_RIG_MAKE", "MY_RIG_MODEL",
        "MY_ANTENNA", "MY_ANTENNA_MAKE", "MY_ANTENNA_MODEL",
        "RIG_MAKE", "RIG_MODEL", "ANT_MAKE", "ANT_MODEL"
    }

    # Location/Geographic Fields
    LOCATION_FIELDS = {
        "COUNTRY", "STATE", "COUNTY", "DXCC", "CQZ", "ITUZ",
        "ARRL_SECT", "IOTA", "IOTA_ISLAND_ID", "SOTA_REF",
        "MY_ARRL_SECT", "MY_CQZ", "MY_ITUZ", "MY_COUNTY",
        "PRIMARY_ADMINISTRATIVE_SUBDIVISION",
        "SECONDARY_ADMINISTRATIVE_SUBDIVISION"
    }

    # Award/Contest Fields
    AWARD_FIELDS = {
        "ARRL_SECT", "AWARD_SUBMITTED", "AWARD_GRANTED",
        "CONTEST_ID", "CLASS", "CHECK", "POWER",
        "POTA_REF", "POTA_PARKS", "SOTA_PARKS",
        "VUCC_GRIDS", "KEY_TYPE", "SKCC", "APP_SKCCLOGGER_KEYTYPE"
    }

    # QSL/Confirmation Fields
    QSL_FIELDS = {
        "QSL_RCVD", "QSL_SENT", "QSL_RCVD_DATE", "QSL_SENT_DATE",
        "QSL_VIA", "QSL_MAILED_DATE", "QSL_REC_DATE",
        "LOTW_QSL_RCVD", "LOTW_QSL_SENT", "LOTW_QSL_REC_DATE",
        "EQSL_QSL_RCVD", "EQSL_QSL_SENT", "EQSL_QSL_REC_DATE",
        "CLUBLOG_QSO_UPLOAD_STATUS", "CLUBLOG_QSO_UPLOAD_DATE",
        "QSLMSG", "QSLRDATE", "QSLSDATE"
    }

    # Propagation/Technical Fields
    TECHNICAL_FIELDS = {
        "PROPAGATION_MODE", "SAT_NAME", "SAT_MODE",
        "SAT_AOS", "SAT_LOS", "MAX_BURSTS", "MS_SHOWER",
        "A_INDEX", "K_INDEX", "SFI", "ANTENNA_AZ", "ANTENNA_EL",
        "DISTANCE", "LATITUDE", "LONGITUDE",
        "MY_LATITUDE", "MY_LONGITUDE", "MY_DISTANCE"
    }

    # Notes/Comments Fields
    NOTES_FIELDS = {
        "NOTES", "COMMENT", "PUBLIC_COMMENTS"
    }

    # All supported fields combined
    ALL_SUPPORTED_FIELDS = (
        CORE_QSO_FIELDS | STATION_INFO_FIELDS | LOCATION_FIELDS |
        AWARD_FIELDS | QSL_FIELDS | TECHNICAL_FIELDS | NOTES_FIELDS
    )

    def __init__(self):
        """Initialize ADIF parser"""
        self.records: List[Dict[str, Any]] = []
        self.header: Dict[str, Any] = {}
        self.errors: List[Tuple[int, str]] = []

    def parse_file(self, file_path: str) -> Tuple[List[Dict], Dict[str, Any]]:
        """
        Parse ADIF file (ADI or ADX format)

        Args:
            file_path: Path to ADIF file

        Returns:
            Tuple of (records, header)
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"ADIF file not found: {file_path}")

        file_ext = file_path.suffix.lower()

        if file_ext == ".adx":
            return self._parse_adx(file_path)
        else:
            return self._parse_adi(file_path)

    def _parse_adi(self, file_path: Path) -> Tuple[List[Dict], Dict[str, Any]]:
        """
        Parse ADI (text) format ADIF file

        Args:
            file_path: Path to ADI file

        Returns:
            Tuple of (records, header)
        """
        self.records = []
        self.header = {}
        self.errors = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Split header and records
            if "<EOH>" in content:
                header_str, records_str = content.split("<EOH>", 1)
            else:
                header_str = ""
                records_str = content

            # Parse header
            self._parse_header(header_str)

            # Parse records (split by <EOR>)
            record_strings = records_str.split("<EOR>")

            for line_num, record_str in enumerate(record_strings, 1):
                if record_str.strip():
                    record = self._parse_record(record_str, line_num)
                    if record:
                        self.records.append(record)

            logger.info(f"Parsed {len(self.records)} records from {file_path}")
            return self.records, self.header

        except Exception as e:
            logger.error(f"Error parsing ADI file: {e}")
            raise

    def _parse_adx(self, file_path: Path) -> Tuple[List[Dict], Dict[str, Any]]:
        """
        Parse ADX (XML) format ADIF file

        Args:
            file_path: Path to ADX file

        Returns:
            Tuple of (records, header)
        """
        try:
            import xml.etree.ElementTree as ET

            tree = ET.parse(file_path)
            root = tree.getroot()

            self.records = []
            self.header = {}

            # Parse header
            header_elem = root.find(".//HEADER")
            if header_elem is not None:
                for child in header_elem:
                    self.header[child.tag] = child.text

            # Parse records
            for qso_elem in root.findall(".//QSO"):
                record = {}
                for child in qso_elem:
                    record[child.tag] = child.text
                self.records.append(record)

            logger.info(f"Parsed {len(self.records)} records from {file_path}")
            return self.records, self.header

        except Exception as e:
            logger.error(f"Error parsing ADX file: {e}")
            raise

    def _parse_header(self, header_str: str) -> None:
        """Parse ADIF header"""
        matches = self.FIELD_PATTERN.findall(header_str)
        for field_name, length, value in matches:
            self.header[field_name] = value

    def _parse_record(self, record_str: str, line_num: int) -> Dict[str, Any]:
        """Parse single ADIF record"""
        record = {}
        matches = self.FIELD_PATTERN.findall(record_str)

        for field_name, length, value in matches:
            record[field_name] = value

        return record if record else None

    def validate_records(self) -> List[Dict[str, Any]]:
        """
        Validate parsed records against ADIF 3.1.5 specification

        Returns:
            List of validation errors
        """
        validation_errors = []

        for idx, record in enumerate(self.records):
            # Check required fields
            if "CALL" not in record:
                validation_errors.append({
                    "record": idx,
                    "field": "CALL",
                    "error": "Missing required field: CALL"
                })

            if "QSO_DATE" not in record:
                validation_errors.append({
                    "record": idx,
                    "field": "QSO_DATE",
                    "error": "Missing required field: QSO_DATE"
                })

            # Must have BAND or FREQ
            if "BAND" not in record and "FREQ" not in record:
                validation_errors.append({
                    "record": idx,
                    "field": "BAND/FREQ",
                    "error": "Must have either BAND or FREQ field"
                })

            if "MODE" not in record:
                validation_errors.append({
                    "record": idx,
                    "field": "MODE",
                    "error": "Missing required field: MODE"
                })

            # Validate individual fields
            if "CALL" in record:
                if not self._is_valid_callsign(record["CALL"]):
                    validation_errors.append({
                        "record": idx,
                        "field": "CALL",
                        "error": f"Invalid callsign format: {record['CALL']}"
                    })

            if "QSO_DATE" in record:
                if not self._is_valid_date(record["QSO_DATE"]):
                    validation_errors.append({
                        "record": idx,
                        "field": "QSO_DATE",
                        "error": f"Invalid date format: {record['QSO_DATE']} (expected YYYYMMDD)"
                    })

            if "TIME_ON" in record:
                if not self._is_valid_time(record["TIME_ON"]):
                    validation_errors.append({
                        "record": idx,
                        "field": "TIME_ON",
                        "error": f"Invalid time format: {record['TIME_ON']} (expected HHMM)"
                    })

            if "BAND" in record:
                if not self._is_valid_band(record["BAND"]):
                    validation_errors.append({
                        "record": idx,
                        "field": "BAND",
                        "error": f"Invalid band: {record['BAND']}"
                    })

            if "MODE" in record:
                if not self._is_valid_mode(record["MODE"]):
                    validation_errors.append({
                        "record": idx,
                        "field": "MODE",
                        "error": f"Invalid mode: {record['MODE']}"
                    })

            if "RST_SENT" in record:
                if not self._is_valid_rst(record["RST_SENT"]):
                    validation_errors.append({
                        "record": idx,
                        "field": "RST_SENT",
                        "error": f"Invalid RST format: {record['RST_SENT']} (expected 3 digits)"
                    })

            if "RST_RCVD" in record:
                if not self._is_valid_rst(record["RST_RCVD"]):
                    validation_errors.append({
                        "record": idx,
                        "field": "RST_RCVD",
                        "error": f"Invalid RST format: {record['RST_RCVD']} (expected 3 digits)"
                    })

            if "GRIDSQUARE" in record:
                if not self._is_valid_grid(record["GRIDSQUARE"]):
                    validation_errors.append({
                        "record": idx,
                        "field": "GRIDSQUARE",
                        "error": f"Invalid grid square: {record['GRIDSQUARE']}"
                    })

        return validation_errors

    # ADIF 3.1.5 Valid modes
    VALID_MODES = {
        "AM", "ARDOP", "ASCI", "ATV", "CHIP", "CLO", "CONTESTI",
        "CW", "DIGITALVOICE", "DOMINO", "DSTAR", "FAX", "FM", "FSK441",
        "FST4", "FT4", "FT8", "HELL", "HELLSCHREIBER", "HFDL",
        "ISCAT", "JT4", "JT6M", "JT9", "JT65", "JTMS", "MFSK",
        "MSK144", "MT63", "OLIVIA", "OPERA", "PAC", "PAX", "PKT",
        "PSK", "PSK2K", "PSK63", "PSK63F", "PSK125", "PSKFEC", "PSKOTHER",
        "Q15", "QPSK", "ROS", "RTTY", "RTTYM", "SSB", "SSTV", "T10",
        "THOR", "THROB", "TOR", "V4", "VOI", "VOICE", "WSJT", "WSPR"
    }

    # Valid bands per ADIF 3.1.5
    VALID_BANDS = {
        "2190M", "600M", "160M", "80M", "60M", "40M", "30M", "20M",
        "17M", "15M", "12M", "10M", "6M", "4M", "2M", "1.25M",
        "70CM", "33CM", "23CM", "13CM", "9CM", "5CM", "3CM", "1.25CM",
        "6MM", "4MM", "2.5MM", "2MM", "1MM"
    }

    @staticmethod
    def _is_valid_callsign(callsign: str) -> bool:
        """Check if callsign is valid format per ADIF spec"""
        if not callsign or len(callsign) > 12:
            return False
        # Allow alphanumeric and slash (e.g., W1AW/VE3, 4Z5XY)
        pattern = r"^[A-Z0-9/]+$"
        return bool(re.match(pattern, callsign, re.IGNORECASE))

    @staticmethod
    def _is_valid_date(date_str: str) -> bool:
        """Check if date is valid YYYYMMDD format"""
        if len(date_str) != 8 or not date_str.isdigit():
            return False
        year = int(date_str[:4])
        month = int(date_str[4:6])
        day = int(date_str[6:8])
        return 1900 <= year <= 2100 and 1 <= month <= 12 and 1 <= day <= 31

    @staticmethod
    def _is_valid_time(time_str: str) -> bool:
        """Check if time is valid HHMM format"""
        if len(time_str) != 4 or not time_str.isdigit():
            return False
        hours = int(time_str[:2])
        minutes = int(time_str[2:4])
        return 0 <= hours <= 23 and 0 <= minutes <= 59

    def _is_valid_band(self, band: str) -> bool:
        """Check if band is valid per ADIF spec"""
        return band.upper() in self.VALID_BANDS

    def _is_valid_mode(self, mode: str) -> bool:
        """Check if mode is valid per ADIF spec"""
        return mode.upper() in self.VALID_MODES

    @staticmethod
    def _is_valid_rst(rst: str) -> bool:
        """Check if RST (signal report) is valid format"""
        if len(rst) != 3 or not rst.isdigit():
            return False
        readability = int(rst[0])
        strength = int(rst[1])
        tone = int(rst[2])
        return 1 <= readability <= 5 and 1 <= strength <= 9 and 1 <= tone <= 9

    @staticmethod
    def _is_valid_grid(grid: str) -> bool:
        """Check if grid square is valid Maidenhead format"""
        if not grid or len(grid) < 4 or len(grid) > 10:
            return False
        # Grid pattern: 2 letters, 2 digits, optionally 4 more chars
        pattern = r"^[A-X]{2}[0-9]{2}([a-x]{2}[0-9]{2})?$"
        return bool(re.match(pattern, grid, re.IGNORECASE))
