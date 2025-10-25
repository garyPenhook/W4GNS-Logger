"""
Base Award Program Class

Abstract base class for all award programs using plugin architecture.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any


class AwardProgram(ABC):
    """Abstract base class for award programs"""

    def __init__(self, name: str, program_id: str):
        """
        Initialize award program

        Args:
            name: Human-readable award name (e.g., "DXCC")
            program_id: Unique program identifier (e.g., "DXCC_MIXED")
        """
        self.name = name
        self.program_id = program_id

    @abstractmethod
    def validate(self, contact: Dict[str, Any]) -> bool:
        """
        Check if a contact qualifies for this award

        Args:
            contact: Contact record dictionary

        Returns:
            True if contact qualifies, False otherwise
        """
        pass

    @abstractmethod
    def calculate_progress(self, contacts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate current progress toward award

        Args:
            contacts: List of contact records

        Returns:
            Dictionary with progress information:
            {
                'current': int,      # Current count/points
                'required': int,     # Required count/points
                'achieved': bool,    # Whether award is achieved
                'progress_pct': float  # Progress percentage
            }
        """
        pass

    @abstractmethod
    def get_requirements(self) -> Dict[str, Any]:
        """
        Return award requirements

        Returns:
            Dictionary with award requirements
        """
        pass

    @abstractmethod
    def get_endorsements(self) -> List[Dict[str, Any]]:
        """
        Return list of endorsement levels

        Returns:
            List of endorsement level dictionaries:
            [
                {'level': 100, 'description': 'Certificate'},
                {'level': 150, 'description': '50-entity endorsement'},
                ...
            ]
        """
        pass

    def get_name(self) -> str:
        """Get award name"""
        return self.name

    def get_program_id(self) -> str:
        """Get program ID"""
        return self.program_id

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self.program_id}, name={self.name})>"
