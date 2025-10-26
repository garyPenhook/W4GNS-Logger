"""
SKCC Canadian Maple Award - Contact Canadian SKCC Members from Provinces/Territories

The Canadian Maple Award is earned by making contact with SKCC members from Canadian
provinces and territories. Four levels of achievement are available:

1. Yellow Maple: 10 contacts from any 10 provinces/territories (mixed bands)
2. Orange Maple: 10 contacts from same 10 provinces/territories on single band (one per band)
3. Red Maple: 90 contacts - 10 from each province/territory across 9 HF bands
4. Gold Maple: 90 QRP contacts (≤5W) across all 9 HF bands

Rules (ALL CRITICAL):
- Contacts must be with SKCC members (remote station has SKCC number)
- QSOs must be CW mode only
- Valid HF bands: 160M, 80M, 60M, 40M, 30M, 20M, 17M, 15M, 12M, 10M
- For Red/Gold Maple: contacts must be across 9 bands (160, 80, 60, 40, 30, 20, 17, 15, 12, 10)
- Contacts valid from: Sept 1, 2009 (provinces), Jan 2014 (territories)
- Mechanical Key Policy: Contact must use mechanical key (STRAIGHT, BUG, or SIDESWIPER)
- Remote operator must hold SKCC membership at time of contact

Canadian Provinces (10 - required for all awards):
- BC (British Columbia), AB (Alberta), SK (Saskatchewan), MB (Manitoba)
- ON (Ontario), QC (Quebec), NB (New Brunswick), NS (Nova Scotia)
- PE (Prince Edward Island), NL (Newfoundland & Labrador)

Territories and Special (optional):
- YT (Yukon), NT (Northwest Territories), NU (Nunavut)
- VE0 (Stations at sea), VY9 (Government of Canada)
"""

import logging
from typing import Dict, List, Any, Set
from sqlalchemy.orm import Session

from src.awards.base import AwardProgram

logger = logging.getLogger(__name__)

# Canadian provinces (the 10 required)
CANADIAN_PROVINCES = {"BC", "AB", "SK", "MB", "ON", "QC", "NB", "NS", "PE", "NL"}

# Territories and special callsigns
CANADIAN_TERRITORIES = {"YT", "NT", "NU", "VE0", "VY9"}

# All valid Canadian regions
CANADIAN_REGIONS = CANADIAN_PROVINCES | CANADIAN_TERRITORIES

# Valid HF bands for Canadian Maple
HF_BANDS = {"160M", "80M", "60M", "40M", "30M", "20M", "17M", "15M", "12M", "10M"}

# 9 main HF bands for Red/Gold Maple
MAIN_HF_BANDS = {"160M", "80M", "40M", "30M", "20M", "17M", "15M", "12M", "10M"}


class CanadianMapleAward(AwardProgram):
    """SKCC Canadian Maple Award - Multiple levels for Canadian provinces/territories"""

    def __init__(self, db: Session):
        """
        Initialize Canadian Maple award

        Args:
            db: SQLAlchemy database session
        """
        super().__init__(name="Canadian Maple", program_id="CANADIAN_MAPLE")
        self.db = db

    def validate(self, contact: Dict[str, Any]) -> bool:
        """
        Check if a contact qualifies for Canadian Maple award

        Requirements:
        - CW mode only
        - Remote station must be in Canada (country field = "Canada")
        - Remote station must have a valid Canadian province/territory in state field
        - Remote station must have SKCC number
        - Contact on valid HF band
        - Contact date valid: Sept 1, 2009 (provinces), Jan 2014 (territories)
        - Mechanical key policy: Contact must use straight key (STRAIGHT, BUG, or SIDESWIPER)

        Args:
            contact: Contact record dictionary

        Returns:
            True if contact qualifies for Canadian Maple award
        """
        # Must be CW mode
        if contact.get('mode', '').upper() != 'CW':
            return False

        # Must be with Canada
        if contact.get('country', '').strip().upper() != 'CANADA':
            return False

        # Must have Canadian province/territory in state field
        state = contact.get('state', '').strip().upper()
        if state not in CANADIAN_REGIONS:
            return False

        # Must have SKCC number (remote station is SKCC member)
        if not contact.get('skcc_number'):
            return False

        # Must be on valid HF band
        band = contact.get('band', '').strip().upper()
        if band not in HF_BANDS:
            return False

        # CRITICAL RULE: Contact date validation
        # Provinces valid from Sept 1, 2009 (20090901)
        # Territories valid from Jan 2014 (20140101)
        qso_date = contact.get('qso_date', '')
        if qso_date:
            if state in CANADIAN_PROVINCES:
                # Provinces: Sept 1, 2009 or later
                if qso_date < '20090901':
                    logger.debug(f"Contact with {state} before Sept 1, 2009: {qso_date}")
                    return False
            elif state in CANADIAN_TERRITORIES:
                # Territories: Jan 2014 or later
                if qso_date < '20140101':
                    logger.debug(f"Contact with {state} before Jan 2014: {qso_date}")
                    return False

        # CRITICAL RULE: SKCC Mechanical Key Policy
        # Contact must use mechanical key (STRAIGHT, BUG, or SIDESWIPER)
        key_type = contact.get('key_type', '').upper()
        if key_type and key_type not in ['STRAIGHT', 'BUG', 'SIDESWIPER']:
            logger.debug(f"Invalid key type for Canadian Maple: {key_type}")
            return False

        return True

    def calculate_progress(self, contacts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate Canadian Maple award progress for all four levels

        Args:
            contacts: List of contact records

        Returns:
            {
                'yellow': {...},      # Yellow Maple progress (any 10 provinces)
                'orange': {...},      # Orange Maple progress (10 provinces per band)
                'red': {...},         # Red Maple progress (90 total across 9 bands)
                'gold': {...},        # Gold Maple progress (90 QRP across 9 bands)
                'current_level': str  # Highest level achieved
            }
        """
        # Filter to valid Canadian Maple contacts
        valid_contacts = [c for c in contacts if self.validate(c)]

        # Calculate each level
        yellow_progress = self._calculate_yellow(valid_contacts)
        orange_progress = self._calculate_orange(valid_contacts)
        red_progress = self._calculate_red(valid_contacts)
        gold_progress = self._calculate_gold(valid_contacts)

        # Determine highest achieved level
        current_level = self._get_current_level(yellow_progress, orange_progress, red_progress, gold_progress)

        return {
            'yellow': yellow_progress,
            'orange': orange_progress,
            'red': red_progress,
            'gold': gold_progress,
            'current_level': current_level,
            'total_contacts': len(valid_contacts),
            'provinces_contacted': self._get_provinces_contacted(valid_contacts)
        }

    def _calculate_yellow(self, contacts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Yellow Maple: 10 contacts from any 10 provinces/territories (mixed bands)

        Args:
            contacts: List of valid Canadian Maple contacts

        Returns:
            Progress dictionary for Yellow Maple
        """
        # Count unique provinces/territories contacted
        provinces = set()
        contact_count = 0

        for contact in contacts:
            state = contact.get('state', '').strip().upper()
            if state in CANADIAN_REGIONS:
                provinces.add(state)
                contact_count += 1

        unique_provinces = len(provinces)
        required = 10

        return {
            'name': 'Yellow Maple',
            'achieved': unique_provinces >= required,
            'current': unique_provinces,
            'required': required,
            'progress_pct': min(100.0, (unique_provinces / required) * 100),
            'provinces': sorted(list(provinces)),
            'total_contacts': contact_count
        }

    def _calculate_orange(self, contacts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Orange Maple: 10 contacts from same 10 provinces/territories on single band
        (This is one award PER band, so we calculate the best band)

        Args:
            contacts: List of valid Canadian Maple contacts

        Returns:
            Progress dictionary for Orange Maple (best band)
        """
        # Group contacts by band
        band_provinces: Dict[str, Set[str]] = {}

        for contact in contacts:
            band = contact.get('band', '').strip().upper()
            state = contact.get('state', '').strip().upper()

            if band not in band_provinces:
                band_provinces[band] = set()
            band_provinces[band].add(state)

        # Find band with most provinces
        best_band = None
        best_count = 0
        best_provinces = set()

        for band, provinces in band_provinces.items():
            count = len(provinces)
            if count > best_count:
                best_count = count
                best_band = band
                best_provinces = provinces

        required = 10
        achieved = best_count >= required

        return {
            'name': 'Orange Maple',
            'achieved': achieved,
            'current': best_count,
            'required': required,
            'progress_pct': min(100.0, (best_count / required) * 100),
            'best_band': best_band,
            'provinces': sorted(list(best_provinces)),
            'band_status': {band: len(prov) for band, prov in sorted(band_provinces.items())}
        }

    def _calculate_red(self, contacts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Red Maple: 90 contacts - 10 from each province across 9 HF bands
        (Need contacts from all 10 provinces, spread across 9+ bands)

        Args:
            contacts: List of valid Canadian Maple contacts

        Returns:
            Progress dictionary for Red Maple
        """
        # Count contacts per province
        province_contacts: Dict[str, int] = {}
        band_contacts: Dict[str, int] = {}

        for contact in contacts:
            state = contact.get('state', '').strip().upper()
            band = contact.get('band', '').strip().upper()

            if state in CANADIAN_PROVINCES:
                province_contacts[state] = province_contacts.get(state, 0) + 1
            if band in MAIN_HF_BANDS:
                band_contacts[band] = band_contacts.get(band, 0) + 1

        total_contacts = len(contacts)
        required = 90

        # Calculate progress: need 10 from each province AND across 9 bands
        min_per_province = min(province_contacts.values()) if province_contacts else 0
        bands_represented = len([b for b, c in band_contacts.items() if c >= 10])

        achieved = (
            total_contacts >= required and
            len(province_contacts) == 10 and  # All 10 provinces
            min_per_province >= 10 and  # At least 10 from each
            bands_represented >= 9  # Across 9 bands
        )

        return {
            'name': 'Red Maple',
            'achieved': achieved,
            'current': total_contacts,
            'required': required,
            'progress_pct': min(100.0, (total_contacts / required) * 100),
            'provinces_count': len(province_contacts),
            'provinces_required': 10,
            'min_per_province': min_per_province,
            'min_required_per_province': 10,
            'bands_represented': bands_represented,
            'bands_required': 9,
            'province_status': {prov: province_contacts.get(prov, 0) for prov in sorted(CANADIAN_PROVINCES)},
            'band_status': {band: band_contacts.get(band, 0) for band in sorted(MAIN_HF_BANDS)}
        }

    def _calculate_gold(self, contacts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Gold Maple: 90 QRP contacts (≤5W) across all 9 HF bands

        Args:
            contacts: List of valid Canadian Maple contacts

        Returns:
            Progress dictionary for Gold Maple
        """
        # Filter for QRP contacts (tx_power <= 5W)
        qrp_contacts = [
            c for c in contacts
            if c.get('tx_power') and float(c.get('tx_power', 0)) <= 5.0
        ]

        # Count by band
        band_qrp: Dict[str, int] = {}
        for contact in qrp_contacts:
            band = contact.get('band', '').strip().upper()
            if band in MAIN_HF_BANDS:
                band_qrp[band] = band_qrp.get(band, 0) + 1

        total_qrp = len(qrp_contacts)
        required = 90
        bands_represented = len([b for b, c in band_qrp.items() if c > 0])

        achieved = (
            total_qrp >= required and
            bands_represented >= 9
        )

        return {
            'name': 'Gold Maple',
            'achieved': achieved,
            'current': total_qrp,
            'required': required,
            'progress_pct': min(100.0, (total_qrp / required) * 100),
            'bands_represented': bands_represented,
            'bands_required': 9,
            'band_status': {band: band_qrp.get(band, 0) for band in sorted(MAIN_HF_BANDS)}
        }

    def _get_current_level(self, yellow: Dict, orange: Dict, red: Dict, gold: Dict) -> str:
        """Determine highest level achieved"""
        if gold['achieved']:
            return 'Gold Maple'
        elif red['achieved']:
            return 'Red Maple'
        elif orange['achieved']:
            return 'Orange Maple'
        elif yellow['achieved']:
            return 'Yellow Maple'
        else:
            return 'Not Yet'

    def _get_provinces_contacted(self, contacts: List[Dict[str, Any]]) -> Dict[str, int]:
        """Get count of contacts by province"""
        provinces = {}
        for contact in contacts:
            state = contact.get('state', '').strip().upper()
            if state in CANADIAN_REGIONS:
                provinces[state] = provinces.get(state, 0) + 1
        return provinces
