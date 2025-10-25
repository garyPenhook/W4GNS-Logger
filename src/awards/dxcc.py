"""
DXCC Award Implementation

Implements DXCC (DX Century Club) award tracking and calculation.
"""

from typing import Dict, List, Any
from .base import AwardProgram


class DXCCAward(AwardProgram):
    """DXCC Award (DX Century Club) - Mixed Mode"""

    ENTITY_REQUIREMENT = 100

    def __init__(self):
        """Initialize DXCC award"""
        super().__init__("DXCC Mixed", "DXCC_MIXED")

    def validate(self, contact: Dict[str, Any]) -> bool:
        """
        Check if contact qualifies for DXCC

        Args:
            contact: Contact record

        Returns:
            True if contact has valid DXCC entity and confirmation
        """
        # Must have DXCC entity number
        if "dxcc" not in contact or not contact["dxcc"]:
            return False

        # Must have QSL confirmation or LoTW confirmation
        qsl_rcvd = contact.get("qsl_rcvd", "").upper() == "Y"
        lotw_rcvd = contact.get("lotw_rcvd", "").upper() == "Y"

        return qsl_rcvd or lotw_rcvd

    def calculate_progress(self, contacts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate DXCC progress

        Args:
            contacts: List of contact records

        Returns:
            Progress dictionary
        """
        # Count unique confirmed DXCC entities
        confirmed_entities = set()

        for contact in contacts:
            if self.validate(contact):
                confirmed_entities.add(contact.get("dxcc"))

        current = len(confirmed_entities)
        required = self.ENTITY_REQUIREMENT
        achieved = current >= required
        progress_pct = min(100, (current / required) * 100) if required > 0 else 0

        return {
            "current": current,
            "required": required,
            "achieved": achieved,
            "progress_pct": progress_pct,
            "entities": list(confirmed_entities),
        }

    def get_requirements(self) -> Dict[str, Any]:
        """Get DXCC requirements"""
        return {
            "entity_count": self.ENTITY_REQUIREMENT,
            "confirmation": True,
            "mode": "MIXED",
            "description": "Confirmed contacts with 100 or more DXCC entities"
        }

    def get_endorsements(self) -> List[Dict[str, Any]]:
        """Get DXCC endorsement levels"""
        endorsements = [
            {
                "level": 100,
                "description": "DXCC Certificate",
                "points": 100
            }
        ]

        # Add 50-entity endorsements
        for level in range(150, 301, 50):
            endorsements.append({
                "level": level,
                "description": f"{level}-entity endorsement",
                "points": level
            })

        # Add 25-entity endorsements above 300
        for level in range(325, 400, 25):
            endorsements.append({
                "level": level,
                "description": f"{level}-entity endorsement",
                "points": level
            })

        return endorsements


class DXCCCWAward(AwardProgram):
    """DXCC Award - CW Mode Only"""

    ENTITY_REQUIREMENT = 100

    def __init__(self):
        """Initialize DXCC CW award"""
        super().__init__("DXCC CW", "DXCC_CW")

    def validate(self, contact: Dict[str, Any]) -> bool:
        """Check if contact qualifies for DXCC CW"""
        # Must be CW mode
        if contact.get("mode", "").upper() != "CW":
            return False

        # Must have DXCC entity
        if "dxcc" not in contact or not contact["dxcc"]:
            return False

        # Must have confirmation
        qsl_rcvd = contact.get("qsl_rcvd", "").upper() == "Y"
        lotw_rcvd = contact.get("lotw_rcvd", "").upper() == "Y"

        return qsl_rcvd or lotw_rcvd

    def calculate_progress(self, contacts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate DXCC CW progress"""
        confirmed_entities = set()

        for contact in contacts:
            if self.validate(contact):
                confirmed_entities.add(contact.get("dxcc"))

        current = len(confirmed_entities)
        required = self.ENTITY_REQUIREMENT
        achieved = current >= required
        progress_pct = min(100, (current / required) * 100) if required > 0 else 0

        return {
            "current": current,
            "required": required,
            "achieved": achieved,
            "progress_pct": progress_pct,
        }

    def get_requirements(self) -> Dict[str, Any]:
        """Get DXCC CW requirements"""
        return {
            "entity_count": self.ENTITY_REQUIREMENT,
            "confirmation": True,
            "mode": "CW",
            "description": "CW-only confirmed contacts with 100+ DXCC entities"
        }

    def get_endorsements(self) -> List[Dict[str, Any]]:
        """Get DXCC CW endorsement levels"""
        return [
            {
                "level": 100,
                "description": "DXCC CW Certificate"
            },
            {
                "level": 150,
                "description": "150-entity endorsement"
            },
            {
                "level": 200,
                "description": "200-entity endorsement"
            },
        ]
