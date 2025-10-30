"""
Award Application Generator

Generates award application forms for all SKCC awards based on their specific rules.
Supports generating applications for:
- Centurion
- Tribune (with endorsements)
- Senator (with endorsements)
- WAC (Worked All Continents)
- WAS (Worked All States)
- Rag Chew
- DXCC
- Canadian Maple
- PFX
- Triple Key
- SKCC DX

Each application is formatted according to award-specific submission requirements.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Set, Tuple
from pathlib import Path

from src.database.repository import DatabaseRepository
from src.database.models import Contact
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class AwardApplicationGenerator:
    """Generate award applications for all SKCC awards"""

    def __init__(self, db: DatabaseRepository, my_callsign: str, my_skcc: str):
        """
        Initialize application generator

        Args:
            db: DatabaseRepository instance
            my_callsign: Operator's call sign
            my_skcc: Operator's SKCC number
        """
        self.db = db
        self.my_callsign = my_callsign
        self.my_skcc = my_skcc

    def generate_centurion_application(self, format: str = 'text') -> str:
        """
        Generate Centurion award application (100+ SKCC members)

        Args:
            format: Output format ('text', 'csv', 'html')

        Returns:
            Formatted application
        """
        session = self.db.get_session()
        try:
            from src.awards.centurion import CenturionAward
            centurion = CenturionAward(session)

            contacts = self._get_award_contacts(session, 'centurion')
            progress = self._calculate_progress(session, contacts, centurion)

            # Convert contacts to dictionaries BEFORE session closes
            contact_list = [self._contact_to_dict(c) for c in contacts]

            application_data = {
                'award_name': 'Centurion',
                'award_manager': 'See SKCC website for current manager',
                'requirement': f"100 unique SKCC members (Current: {progress['current']})",
                'contacts': contact_list,
                'summary': progress,
                'rules': [
                    'Both operators must hold SKCC membership at time of contact',
                    'CW mode only',
                    'SKCC number exchange required',
                    'Mechanical key required (STRAIGHT, BUG, SIDESWIPER)',
                    'Club calls and special event calls don\'t count after Dec 1, 2009',
                    'Any band allowed',
                    'Each call sign counts only once'
                ]
            }

            if format.lower() == 'csv':
                result = self._format_application_csv(application_data)
            elif format.lower() == 'html':
                result = self._format_application_html(application_data)
            elif format.lower() == 'skcc':
                result = self._format_application_skcc_official(application_data, 'centurion')
            else:
                result = self._format_application_text(application_data)
            
            return result

        except Exception as e:
            logger.error(f"Error generating Centurion application: {e}", exc_info=True)
            raise
        finally:
            session.close()

    def generate_tribune_application(
        self,
        format: str = 'text',
        achievement_date: Optional[str] = None,
        endorsement_level: Optional[int] = None
    ) -> str:
        """
        Generate Tribune award application (50+ Tribune/Senator members)

        Args:
            format: Output format ('text', 'csv', 'html')
            achievement_date: Deprecated - official achievement date from SKCC database is used automatically
            endorsement_level: Specific endorsement level requested

        Returns:
            Formatted application
        """
        session = self.db.get_session()
        try:
            from src.awards.tribune import TribuneAward
            tribune = TribuneAward(session)

            # Get official Tribune achievement date from database (not user input)
            tribune_progress = self.db.analyze_tribune_award_progress()
            official_achievement_date = tribune_progress.get('tribune_achievement_date')

            contacts = self._get_award_contacts(session, 'tribune', official_achievement_date)
            progress = self._calculate_progress(session, contacts, tribune)

            # Convert contacts to dictionaries BEFORE session closes
            contact_list = [self._contact_to_dict(c) for c in contacts]

            application_data = {
                'award_name': 'Tribune',
                'award_manager': 'TX1: AC2C@skccgroup.com | TX2+: TX2manager@skccgroup.com',
                'requirement': f"50 unique Tribune/Senator members (Current: {progress['current']})",
                'endorsement': progress.get('endorsement', 'Not Yet'),
                'contacts': contact_list,
                'summary': progress,
                'rules': [
                    'Must be Centurion first (100+ SKCC members)',
                    'Contact 50+ Tribune/Senator/Senators',
                    'Both operators must hold Centurion status at time of contact',
                    'CW mode only',
                    'SKCC number exchange required',
                    'Mechanical key required (STRAIGHT, BUG, SIDESWIPER)',
                    'Club calls and special event calls excluded after Oct 1, 2008',
                    'Contacts valid on or after March 1, 2007',
                    'Any band allowed',
                    'Each call sign counts only once',
                    'Multi-band and single-band endorsements available'
                ]
            }

            if format.lower() == 'csv':
                result = self._format_application_csv(application_data)
            elif format.lower() == 'html':
                result = self._format_application_html(application_data)
            elif format.lower() == 'skcc':
                result = self._format_application_skcc_official(application_data, 'tribune')
            else:
                result = self._format_application_text(application_data)
            
            return result

        except Exception as e:
            logger.error(f"Error generating Tribune application: {e}", exc_info=True)
            raise
        finally:
            session.close()

    def generate_senator_application(
        self,
        format: str = 'text',
        achievement_date: Optional[str] = None
    ) -> str:
        """
        Generate Senator award application (200+ Tribune/Senator contacts after Tribune x8)

        Args:
            format: Output format ('text', 'csv', 'html')
            achievement_date: Deprecated - official Tribune x8 achievement date is calculated automatically

        Returns:
            Formatted application
        """
        session = self.db.get_session()
        try:
            from src.awards.senator import SenatorAward
            senator = SenatorAward(session)

            # Get official Tribune x8 achievement date from database (not user input)
            senator_progress = self.db.analyze_senator_award_progress()
            official_achievement_date = senator_progress.get('tribune_x8_achievement_date')

            contacts = self._get_award_contacts(session, 'senator', official_achievement_date)
            progress = self._calculate_progress(session, contacts, senator)

            # Convert contacts to dictionaries BEFORE session closes
            contact_list = [self._contact_to_dict(c) for c in contacts]

            application_data = {
                'award_name': 'Senator',
                'award_manager': 'TX2manager@skccgroup.com',
                'requirement': f"200 unique Tribune/Senator contacts after Tribune x8 (Current: {progress['current']})",
                'prerequisite': 'Tribune x8 (400+ Tribune/Senator contacts)',
                'contacts': contact_list,
                'summary': progress,
                'rules': [
                    'Must achieve Tribune x8 first (400+ Tribune/Senator contacts)',
                    'Contact 200+ Tribune/Senator on or after Tribune x8 achievement',
                    'Both operators must hold Tribune status at time of contact',
                    'CW mode only',
                    'SKCC number exchange required',
                    'Mechanical key required (STRAIGHT, BUG, SIDESWIPER)',
                    'Club calls and special event calls excluded',
                    'Contacts valid on or after August 1, 2013',
                    'Any band allowed',
                    'Each call sign counts only once',
                    'Multi-band and single-band endorsements available'
                ]
            }

            if format.lower() == 'csv':
                result = self._format_application_csv(application_data)
            elif format.lower() == 'html':
                result = self._format_application_html(application_data)
            else:
                result = self._format_application_text(application_data)
            
            return result

        except Exception as e:
            logger.error(f"Error generating Senator application: {e}", exc_info=True)
            raise
        finally:
            session.close()

    def generate_was_application(self, format: str = 'text') -> str:
        """
        Generate WAS award application (all 50 US states)

        Args:
            format: Output format ('text', 'csv', 'html')

        Returns:
            Formatted application
        """
        session = self.db.get_session()
        try:
            from src.awards.was import WASAward
            was = WASAward(session)

            contacts = self._get_award_contacts(session, 'was')
            progress = self._calculate_progress(session, contacts, was)

            # Convert contacts to dictionaries BEFORE session closes
            contact_list = [self._contact_to_dict(c) for c in contacts]

            application_data = {
                'award_name': 'WAS (Worked All States)',
                'requirement': f"All 50 US states (Current: {progress['current']}/50)",
                'missing_states': progress.get('missing_states', []),
                'contacts': contact_list,
                'summary': progress,
                'rules': [
                    'Both operators must hold SKCC membership',
                    'CW mode only',
                    'SKCC number exchange required',
                    'Mechanical key required (STRAIGHT, BUG, SIDESWIPER)',
                    'Contact required with members in all 50 US states',
                    'Any band allowed',
                    'Single-band endorsements available',
                    'WAS-QRP endorsement available (≤5W power)'
                ]
            }

            if format.lower() == 'csv':
                result = self._format_application_csv(application_data)
            elif format.lower() == 'html':
                result = self._format_application_html(application_data)
            else:
                result = self._format_application_text(application_data)
            
            return result

        except Exception as e:
            logger.error(f"Error generating WAS application: {e}", exc_info=True)
            raise
        finally:
            session.close()

    def generate_wac_application(self, format: str = 'text') -> str:
        """
        Generate WAC award application (all 6 continents)

        Args:
            format: Output format ('text', 'csv', 'html')

        Returns:
            Formatted application
        """
        session = self.db.get_session()
        try:
            from src.awards.wac import WACAward
            wac = WACAward(session)

            contacts = self._get_award_contacts(session, 'wac')
            progress = self._calculate_progress(session, contacts, wac)

            # Convert contacts to dictionaries BEFORE session closes
            contact_list = [self._contact_to_dict(c) for c in contacts]

            application_data = {
                'award_name': 'WAC (Worked All Continents)',
                'requirement': f"All 6 continents (Current: {progress['current']}/6)",
                'missing_continents': progress.get('missing_continents', []),
                'contacts': contact_list,
                'summary': progress,
                'rules': [
                    'Both operators must hold SKCC membership',
                    'CW mode only',
                    'SKCC number exchange required',
                    'Mechanical key required (STRAIGHT, BUG, SIDESWIPER)',
                    'Contacts required with members in all 6 continents',
                    'Contacts valid on or after October 9, 2011',
                    'Any band allowed',
                    'Band endorsements available (per band worked)',
                    'QRP endorsement available (≤5W power)'
                ]
            }

            if format.lower() == 'csv':
                result = self._format_application_csv(application_data)
            elif format.lower() == 'html':
                result = self._format_application_html(application_data)
            else:
                result = self._format_application_text(application_data)
            
            return result

        except Exception as e:
            logger.error(f"Error generating WAC application: {e}", exc_info=True)
            raise
        finally:
            session.close()

    def generate_rag_chew_application(self, format: str = 'text') -> str:
        """
        Generate Rag Chew award application (300+ minutes)

        Args:
            format: Output format ('text', 'csv', 'html')

        Returns:
            Formatted application
        """
        session = self.db.get_session()
        try:
            from src.awards.rag_chew import RagChewAward
            rag_chew = RagChewAward(session)

            contacts = self._get_award_contacts(session, 'rag_chew')
            progress = self._calculate_progress(session, contacts, rag_chew)

            # Convert contacts to dictionaries BEFORE session closes
            contact_list = [self._contact_to_dict(c) for c in contacts]

            application_data = {
                'award_name': 'Rag Chew Award',
                'requirement': f"300+ minutes CW conversation (Current: {progress['current']} min)",
                'contacts': contact_list,
                'summary': progress,
                'rules': [
                    'Both operators must hold SKCC membership',
                    'CW mode exclusively',
                    'Minimum 30 minutes per contact (40 minutes for multi-station)',
                    'SKCC number exchange required',
                    'Mechanical key required (STRAIGHT, BUG, SIDESWIPER)',
                    'Back-to-back contacts with same member prohibited',
                    'Contacts valid on or after July 1, 2013',
                    'Any band allowed',
                    'Duration must be logged in minutes',
                    'Endorsements: x2 (600 min), x3 (900 min), etc.'
                ]
            }

            if format.lower() == 'csv':
                result = self._format_application_csv(application_data)
            elif format.lower() == 'html':
                result = self._format_application_html(application_data)
            else:
                result = self._format_application_text(application_data)
            
            return result

        except Exception as e:
            logger.error(f"Error generating Rag Chew application: {e}", exc_info=True)
            raise
        finally:
            session.close()

    def generate_dxcc_application(self, format: str = 'text') -> str:
        """
        Generate DXCC award application (worked 100+ countries)

        Args:
            format: Output format ('text', 'csv', 'html')

        Returns:
            Formatted application
        """
        session = self.db.get_session()
        try:
            from src.awards.dxcc import DXCCAward
            dxcc = DXCCAward()

            contacts = self._get_award_contacts(session, 'dxcc')
            progress = self._calculate_progress(session, contacts, dxcc)

            # Convert contacts to dictionaries BEFORE session closes
            contact_list = [self._contact_to_dict(c) for c in contacts]

            application_data = {
                'award_name': 'DXCC Award',
                'requirement': f"100+ countries worked (Current: {progress['current']})",
                'contacts': contact_list,
                'summary': progress,
                'rules': [
                    'CW mode only',
                    'Any band allowed',
                    'At least 100 different countries',
                    'ARRL DXCC entity list used for validation',
                    'Both operators must be licensed amateurs',
                    'Contacts must be two-way valid',
                    'Contacts can be mixed bands and modes (CW for this logger)',
                    'Endorsements available: x2 (150), x3 (200), etc.'
                ]
            }

            if format.lower() == 'csv':
                result = self._format_application_csv(application_data)
            elif format.lower() == 'html':
                result = self._format_application_html(application_data)
            else:
                result = self._format_application_text(application_data)
            
            return result

        except Exception as e:
            logger.error(f"Error generating DXCC application: {e}", exc_info=True)
            raise
        finally:
            session.close()

    def generate_canadian_maple_application(self, format: str = 'text') -> str:
        """
        Generate Canadian Maple award application (all Canadian provinces)

        Args:
            format: Output format ('text', 'csv', 'html')

        Returns:
            Formatted application
        """
        session = self.db.get_session()
        try:
            from src.awards.canadian_maple import CanadianMapleAward
            maple = CanadianMapleAward(session)

            contacts = self._get_award_contacts(session, 'canadian_maple')
            progress = self._calculate_progress(session, contacts, maple)

            # Convert contacts to dictionaries BEFORE session closes
            contact_list = [self._contact_to_dict(c) for c in contacts]

            application_data = {
                'award_name': 'Canadian Maple Award',
                'requirement': f"All Canadian provinces and territories (Level: {progress.get('current_level', 'None')})",
                'contacts': contact_list,
                'summary': progress,
                'rules': [
                    'CW mode only',
                    'All 10 Canadian provinces and 3 territories must be worked',
                    'Two-way communication required',
                    'Mechanical key required',
                    'SKCC number exchange preferred but not required',
                    'Provinces: AB, BC, MB, NB, NS, ON, PE, QC, SK, NL',
                    'Territories: NT, NU, YT',
                    'Any band allowed',
                    'Contacts on or after January 1, 2000'
                ]
            }

            if format.lower() == 'csv':
                result = self._format_application_csv(application_data)
            elif format.lower() == 'html':
                result = self._format_application_html(application_data)
            else:
                result = self._format_application_text(application_data)
            
            return result

        except Exception as e:
            logger.error(f"Error generating Canadian Maple application: {e}", exc_info=True)
            raise
        finally:
            session.close()

    def generate_pfx_application(self, format: str = 'text') -> str:
        """
        Generate PFX award application (prefix awards)

        Args:
            format: Output format ('text', 'csv', 'html')

        Returns:
            Formatted application
        """
        session = self.db.get_session()
        try:
            from src.awards.pfx import PFXAward
            pfx = PFXAward(session)

            contacts = self._get_award_contacts(session, 'pfx')
            progress = self._calculate_progress(session, contacts, pfx)

            # Convert contacts to dictionaries BEFORE session closes
            contact_list = [self._contact_to_dict(c) for c in contacts]

            application_data = {
                'award_name': 'PFX Award',
                'requirement': f"Prefix challenge (Current: {progress['current']})",
                'contacts': contact_list,
                'summary': progress,
                'rules': [
                    'CW mode only',
                    'Unique amateur radio call sign prefixes collected',
                    'Two-way communication required',
                    'Any band allowed',
                    'Mechanical key required',
                    'Scoring based on cumulative prefixes worked',
                    'Multiple endorsement levels available'
                ]
            }

            if format.lower() == 'csv':
                result = self._format_application_csv(application_data)
            elif format.lower() == 'html':
                result = self._format_application_html(application_data)
            else:
                result = self._format_application_text(application_data)
            
            return result

        except Exception as e:
            logger.error(f"Error generating PFX application: {e}", exc_info=True)
            raise
        finally:
            session.close()

    def generate_triple_key_application(self, format: str = 'text') -> str:
        """
        Generate Triple Key award application (three key types)

        Args:
            format: Output format ('text', 'csv', 'html')

        Returns:
            Formatted application
        """
        session = self.db.get_session()
        try:
            from src.awards.triple_key import TripleKeyAward
            triple_key = TripleKeyAward(session)

            contacts = self._get_award_contacts(session, 'triple_key')
            progress = self._calculate_progress(session, contacts, triple_key)

            # Convert contacts to dictionaries BEFORE session closes
            contact_list = [self._contact_to_dict(c) for c in contacts]

            application_data = {
                'award_name': 'Triple Key Award',
                'requirement': f"CW with three key types (Current: {progress['current']})",
                'contacts': contact_list,
                'summary': progress,
                'rules': [
                    'CW mode only',
                    'Contacts using three different key types:',
                    '  - Straight key',
                    '  - Bug/semi-automatic',
                    '  - Fully automatic/keyer',
                    'Two-way communication with each key type required',
                    'SKCC number exchange required',
                    'Mechanical key required (at least one contact)',
                    'Any band allowed',
                    'Minimum 1 contact with each key type'
                ]
            }

            if format.lower() == 'csv':
                result = self._format_application_csv(application_data)
            elif format.lower() == 'html':
                result = self._format_application_html(application_data)
            else:
                result = self._format_application_text(application_data)
            
            return result

        except Exception as e:
            logger.error(f"Error generating Triple Key application: {e}", exc_info=True)
            raise
        finally:
            session.close()

    def generate_skcc_dx_application(self, format: str = 'text') -> str:
        """
        Generate SKCC DX award application (DX with SKCC members)

        Args:
            format: Output format ('text', 'csv', 'html')

        Returns:
            Formatted application
        """
        session = self.db.get_session()
        try:
            from src.awards.skcc_dx import DXQAward
            skcc_dx = DXQAward(session)

            contacts = self._get_award_contacts(session, 'skcc_dx')
            progress = self._calculate_progress(session, contacts, skcc_dx)

            # Convert contacts to dictionaries BEFORE session closes
            contact_list = [self._contact_to_dict(c) for c in contacts]

            application_data = {
                'award_name': 'SKCC DX Award',
                'requirement': f"DX SKCC members worked (Current: {progress['current']})",
                'contacts': contact_list,
                'summary': progress,
                'rules': [
                    'CW mode only',
                    'DX (outside US/Canada) SKCC members only',
                    'SKCC number exchange required',
                    'Two-way communication required',
                    'Mechanical key required',
                    'Any HF band allowed',
                    'Includes countries as recognized by ARRL DXCC list',
                    'Contacts on or after January 1, 2000',
                    'Multiple endorsement levels: x2, x3, x4, etc.'
                ]
            }

            if format.lower() == 'csv':
                result = self._format_application_csv(application_data)
            elif format.lower() == 'html':
                result = self._format_application_html(application_data)
            else:
                result = self._format_application_text(application_data)
            
            return result

        except Exception as e:
            logger.error(f"Error generating SKCC DX application: {e}", exc_info=True)
            raise
        finally:
            session.close()

    def generate_application(
        self,
        award_name: str,
        format: str = 'text',
        achievement_date: Optional[str] = None
    ) -> str:
        """
        Generate award application for any award (universal method)

        Args:
            award_name: Name of award (e.g., 'Centurion', 'Tribune', 'DXCC', etc.)
            format: Output format ('text', 'csv', 'html')
            achievement_date: Date for endorsement filtering (YYYYMMDD format)

        Returns:
            Formatted application string
        """
        award_name_lower = award_name.lower().strip()

        try:
            if award_name_lower == 'centurion':
                return self.generate_centurion_application(format)
            elif award_name_lower == 'tribune':
                return self.generate_tribune_application(
                    format=format,
                    achievement_date=achievement_date
                )
            elif award_name_lower == 'senator':
                return self.generate_senator_application(
                    format=format,
                    achievement_date=achievement_date
                )
            elif award_name_lower == 'was':
                return self.generate_was_application(format)
            elif award_name_lower == 'wac':
                return self.generate_wac_application(format)
            elif award_name_lower == 'rag chew':
                return self.generate_rag_chew_application(format)
            elif award_name_lower == 'dxcc':
                return self.generate_dxcc_application(format)
            elif award_name_lower == 'canadian maple':
                return self.generate_canadian_maple_application(format)
            elif award_name_lower == 'pfx':
                return self.generate_pfx_application(format)
            elif award_name_lower == 'triple key':
                return self.generate_triple_key_application(format)
            elif award_name_lower == 'skcc dx':
                return self.generate_skcc_dx_application(format)
            else:
                return f"Error: Unknown award type '{award_name}'. Supported awards: Centurion, Tribune, Senator, WAS, WAC, Rag Chew, DXCC, Canadian Maple, PFX, Triple Key, SKCC DX"

        except Exception as e:
            logger.error(f"Error generating application for {award_name}: {e}", exc_info=True)
            return f"Error generating application: {str(e)}"

    def _get_award_contacts(
        self,
        session: Session,
        award_type: str,
        achievement_date: Optional[str] = None
    ) -> List[Contact]:
        """Get contacts that qualify for a specific award"""
        from src.awards.centurion import CenturionAward
        from src.awards.tribune import TribuneAward
        from src.awards.senator import SenatorAward
        from src.awards.was import WASAward
        from src.awards.wac import WACAward
        from src.awards.rag_chew import RagChewAward
        from src.awards.dxcc import DXCCAward
        from src.awards.canadian_maple import CanadianMapleAward
        from src.awards.pfx import PFXAward
        from src.awards.triple_key import TripleKeyAward
        from src.awards.skcc_dx import DXQAward

        # Get all contacts
        all_contacts = session.query(Contact).order_by(Contact.qso_date.asc()).all()

        # Create award instance
        if award_type.lower() == 'centurion':
            award = CenturionAward(session)
        elif award_type.lower() == 'tribune':
            award = TribuneAward(session)
        elif award_type.lower() == 'senator':
            award = SenatorAward(session)
        elif award_type.lower() == 'was':
            award = WASAward(session)
        elif award_type.lower() == 'wac':
            award = WACAward(session)
        elif award_type.lower() == 'rag_chew':
            award = RagChewAward(session)
        elif award_type.lower() == 'dxcc':
            award = DXCCAward()
        elif award_type.lower() == 'canadian_maple':
            award = CanadianMapleAward(session)
        elif award_type.lower() == 'pfx':
            award = PFXAward(session)
        elif award_type.lower() == 'triple_key':
            award = TripleKeyAward(session)
        elif award_type.lower() == 'skcc_dx':
            award = DXQAward(session)
        else:
            return []

        # Filter valid contacts
        # For awards that count unique members (Centurion, Tribune, Senator),
        # we need to track which members we've already counted
        valid_contacts = []
        seen_members = set()  # Track unique SKCC numbers for deduplication
        
        for contact in all_contacts:
            contact_dict = self._contact_to_dict(contact)
            if award.validate(contact_dict):
                # Filter by achievement date if provided
                if achievement_date and contact.qso_date is not None:
                    if str(contact.qso_date) < str(achievement_date):
                        continue
                
                # For Tribune/Centurion/Senator: only include first qualifying contact per member
                if award_type.lower() in ['centurion', 'tribune', 'senator']:
                    from src.utils.skcc_number import extract_base_skcc_number
                    base_skcc = extract_base_skcc_number(contact.skcc_number or '')
                    if base_skcc:
                        if base_skcc in seen_members:
                            continue  # Skip duplicate member
                        seen_members.add(base_skcc)
                
                valid_contacts.append(contact)

        return valid_contacts

    def _contact_to_dict(self, contact: Contact) -> Dict[str, Any]:
        """Convert Contact ORM object to dictionary"""
        return {
            'callsign': contact.callsign,
            'qso_date': contact.qso_date,
            'time_on': contact.time_on,
            'band': contact.band,
            'mode': contact.mode,
            'skcc_number': contact.skcc_number,
            'rst_sent': contact.rst_sent,
            'rst_rcvd': contact.rst_rcvd,
            'notes': contact.notes,
            'key_type': contact.key_type,
            'state': contact.state if contact.state else '',
            'country': contact.country if contact.country else '',
            'dxcc': contact.dxcc if contact.dxcc else '',
            'tx_power': contact.tx_power
        }

    def _calculate_progress(
        self,
        session: Session,
        contacts: List[Contact],
        award: Any
    ) -> Dict[str, Any]:
        """Calculate award progress"""
        contact_dicts = [self._contact_to_dict(c) for c in contacts]
        return award.calculate_progress(contact_dicts)

    def _format_application_text(self, app_data: Dict[str, Any]) -> str:
        """Format application as plain text"""
        lines: List[str] = []

        lines.append("=" * 90)
        lines.append(f"SKCC {app_data['award_name']} AWARD APPLICATION")
        lines.append("=" * 90)
        lines.append("")

        # Operator Information
        lines.append("APPLICANT INFORMATION")
        lines.append("-" * 90)
        lines.append(f"Call Sign: {self.my_callsign}")
        lines.append(f"SKCC Number: {self.my_skcc}")
        lines.append(f"Application Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}")
        lines.append(f"Application Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        lines.append("")

        # Award Information
        lines.append("AWARD INFORMATION")
        lines.append("-" * 90)
        lines.append(f"Award: {app_data['award_name']}")
        lines.append(f"Requirement: {app_data['requirement']}")
        if 'prerequisite' in app_data:
            lines.append(f"Prerequisite: {app_data['prerequisite']}")
        if 'endorsement' in app_data:
            lines.append(f"Current Level: {app_data['endorsement']}")
        if 'missing_states' in app_data and app_data['missing_states']:
            lines.append(f"Missing States: {', '.join(app_data['missing_states'])}")
        if 'missing_continents' in app_data and app_data['missing_continents']:
            lines.append(f"Missing Continents: {', '.join(app_data['missing_continents'])}")
        lines.append("")

        # Award Manager
        if 'award_manager' in app_data:
            lines.append("SUBMISSION INFORMATION")
            lines.append("-" * 90)
            lines.append(f"Award Manager(s): {app_data['award_manager']}")
            lines.append("")

        # Rules
        lines.append("AWARD RULES")
        lines.append("-" * 90)
        for i, rule in enumerate(app_data.get('rules', []), 1):
            lines.append(f"{i}. {rule}")
        lines.append("")

        # Summary Statistics
        if 'summary' in app_data:
            summary = app_data['summary']
            lines.append("SUMMARY STATISTICS")
            lines.append("-" * 90)
            lines.append(f"Total Qualifying QSOs: {len(app_data['contacts'])}")
            lines.append(f"Progress: {summary.get('current', 0)}/{summary.get('required', 'N/A')}")
            progress_pct = summary.get('progress_pct', 0)
            lines.append(f"Progress Percentage: {progress_pct:.1f}%")
            lines.append("")

        # Contact List
        lines.append("CONTACT LIST")
        lines.append("-" * 90)
        lines.append(f"{'Date':<12} {'Call':<12} {'SKCC':<15} {'Band':<8} {'Mode':<6} {'Time':<6} {'Notes':<30}")
        lines.append("-" * 90)

        for contact in app_data['contacts']:
            call = str(contact.get('callsign', '')) if contact.get('callsign') else ''
            skcc = str(contact.get('skcc_number', '')) if contact.get('skcc_number') else ''
            band = str(contact.get('band', '')) if contact.get('band') else ''
            mode = str(contact.get('mode', '')) if contact.get('mode') else ''
            qso_date = str(contact.get('qso_date', '')) if contact.get('qso_date') is not None else ''
            time_on = str(contact.get('time_on', '')) if contact.get('time_on') else ''
            notes = str(contact.get('notes', '')) if contact.get('notes') is not None else ''
            notes = notes[:27] + '...' if len(notes) > 30 else notes

            lines.append(f"{qso_date:<12} {call:<12} {skcc:<15} {band:<8} {mode:<6} {time_on:<6} {notes:<30}")

        lines.append("-" * 90)
        lines.append(f"Total Contacts: {len(app_data['contacts'])}")
        lines.append("=" * 90)
        lines.append("")
        lines.append("SUBMISSION INSTRUCTIONS")
        lines.append("-" * 90)
        lines.append("1. Review this application carefully for accuracy")
        lines.append("2. Verify all call signs and SKCC numbers are correct")
        lines.append("3. Remove any duplicate entries")
        lines.append("4. Include your call sign and award name in the email subject line")
        lines.append("5. Submit to the award manager at the email address listed above")
        lines.append("")

        return "\n".join(lines)

    def _format_application_csv(self, app_data: Dict[str, Any]) -> str:
        """Format application as CSV"""
        lines: List[str] = []

        # Header with applicant info
        lines.append(f"SKCC Award Application: {app_data['award_name']}")
        lines.append(f"Applicant: {self.my_callsign}")
        lines.append(f"SKCC Number: {self.my_skcc}")
        lines.append(f"Date Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        lines.append(f"Requirement: {app_data['requirement']}")
        lines.append("")

        # Column headers
        lines.append("QSO Date,Call Sign,SKCC Number,Band,Mode,Time UTC,RST Sent,RST Rcvd,Notes")

        # Data rows
        for contact in app_data['contacts']:
            row = [
                str(contact.get('qso_date', '')) if contact.get('qso_date') is not None else '',
                str(contact.get('callsign', '')) if contact.get('callsign') else '',
                str(contact.get('skcc_number', '')) if contact.get('skcc_number') else '',
                str(contact.get('band', '')) if contact.get('band') else '',
                str(contact.get('mode', '')) if contact.get('mode') else '',
                str(contact.get('time_on', '')) if contact.get('time_on') else '',
                str(contact.get('rst_sent', '')) if contact.get('rst_sent') is not None else '',
                str(contact.get('rst_rcvd', '')) if contact.get('rst_rcvd') is not None else '',
                str(contact.get('notes', '')) if contact.get('notes') is not None else ''
            ]
            # Escape quotes in fields
            row = [f'"{field}"' for field in row]
            lines.append(','.join(row))

        return "\n".join(lines)

    def _format_application_html(self, app_data: Dict[str, Any]) -> str:
        """Format application as HTML"""
        lines: List[str] = []

        lines.append("<!DOCTYPE html>")
        lines.append("<html>")
        lines.append("<head>")
        lines.append(f"<title>SKCC {app_data['award_name']} Application - {self.my_callsign}</title>")
        lines.append("<style>")
        lines.append("""
            body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
            .header { background-color: #1E88E5; color: white; padding: 20px; border-radius: 5px; margin-bottom: 20px; }
            .section { background-color: white; padding: 15px; margin: 15px 0; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .section h2 { color: #1E88E5; border-bottom: 2px solid #1E88E5; padding-bottom: 10px; }
            table { width: 100%; border-collapse: collapse; margin-top: 15px; }
            th { background-color: #1E88E5; color: white; padding: 10px; text-align: left; }
            td { padding: 8px; border-bottom: 1px solid #ddd; }
            tr:hover { background-color: #f5f5f5; }
            .info-row { display: flex; margin: 8px 0; }
            .info-label { font-weight: bold; width: 200px; }
            .rules-list { padding-left: 20px; }
            .rules-list li { margin: 5px 0; }
            .footer { text-align: center; margin-top: 30px; color: #666; font-size: 12px; }
        """)
        lines.append("</style>")
        lines.append("</head>")
        lines.append("<body>")

        # Header
        lines.append("<div class='header'>")
        lines.append(f"<h1>SKCC {app_data['award_name']} Award Application</h1>")
        lines.append("</div>")

        # Applicant Information
        lines.append("<div class='section'>")
        lines.append("<h2>Applicant Information</h2>")
        lines.append(f"<div class='info-row'><div class='info-label'>Call Sign:</div><div>{self.my_callsign}</div></div>")
        lines.append(f"<div class='info-row'><div class='info-label'>SKCC Number:</div><div>{self.my_skcc}</div></div>")
        lines.append(f"<div class='info-row'><div class='info-label'>Application Date:</div><div>{datetime.now(timezone.utc).strftime('%Y-%m-%d')}</div></div>")
        lines.append("</div>")

        # Award Information
        lines.append("<div class='section'>")
        lines.append("<h2>Award Information</h2>")
        lines.append(f"<div class='info-row'><div class='info-label'>Award:</div><div>{app_data['award_name']}</div></div>")
        lines.append(f"<div class='info-row'><div class='info-label'>Requirement:</div><div>{app_data['requirement']}</div></div>")
        if 'prerequisite' in app_data:
            lines.append(f"<div class='info-row'><div class='info-label'>Prerequisite:</div><div>{app_data['prerequisite']}</div></div>")
        if 'award_manager' in app_data:
            lines.append(f"<div class='info-row'><div class='info-label'>Award Manager:</div><div>{app_data['award_manager']}</div></div>")
        lines.append("</div>")

        # Rules
        lines.append("<div class='section'>")
        lines.append("<h2>Award Rules</h2>")
        lines.append("<ul class='rules-list'>")
        for rule in app_data.get('rules', []):
            lines.append(f"<li>{rule}</li>")
        lines.append("</ul>")
        lines.append("</div>")

        # Contact List
        lines.append("<div class='section'>")
        lines.append("<h2>Contact List</h2>")
        lines.append("<table>")
        lines.append("<thead>")
        lines.append("<tr><th>QSO Date</th><th>Call Sign</th><th>SKCC Number</th><th>Band</th><th>Mode</th><th>Time UTC</th><th>Notes</th></tr>")
        lines.append("</thead>")
        lines.append("<tbody>")

        for contact in app_data['contacts']:
            lines.append("<tr>")
            lines.append(f"<td>{contact.get('qso_date') if contact.get('qso_date') is not None else ''}</td>")
            lines.append(f"<td>{contact.get('callsign') if contact.get('callsign') else ''}</td>")
            lines.append(f"<td>{contact.get('skcc_number') if contact.get('skcc_number') else ''}</td>")
            lines.append(f"<td>{contact.get('band') if contact.get('band') else ''}</td>")
            lines.append(f"<td>{contact.get('mode') if contact.get('mode') else ''}</td>")
            lines.append(f"<td>{contact.get('time_on') if contact.get('time_on') else ''}</td>")
            lines.append(f"<td>{contact.get('notes') if contact.get('notes') is not None else ''}</td>")
            lines.append("</tr>")

        lines.append("</tbody>")
        lines.append("</table>")
        lines.append(f"<p><strong>Total Contacts:</strong> {len(app_data['contacts'])}</p>")
        lines.append("</div>")

        # Footer
        lines.append("<div class='footer'>")
        lines.append(f"<p>Generated by W4GNS Logger on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</p>")
        lines.append("</div>")

        lines.append("</body>")
        lines.append("</html>")

        return "\n".join(lines)

    def _format_application_skcc_official(self, app_data: Dict[str, Any], award_type: str = 'tribune') -> str:
        """Format application in SKCC official format matching the ODF template"""
        from src.database.models import Contact
        from src.config.settings import get_config_manager
        
        lines: List[str] = []
        
        # Get operator info
        config_manager = get_config_manager()
        operator_name = config_manager.get('general', {}).get('operator_name', '')
        operator_city = config_manager.get('general', {}).get('operator_city', '')
        operator_state = config_manager.get('general', {}).get('operator_state', '')
        city_state = f"{operator_city}, {operator_state}".strip(', ')
        
        # Header section matching ODF template
        if award_type.lower() == 'tribune':
            lines.append("SKCC Tribune Award & Endorsements Application")
        elif award_type.lower() == 'centurion':
            lines.append("SKCC Centurion Award & Endorsements Application")
        elif award_type.lower() == 'senator':
            lines.append("SKCC Senator Award & Endorsements Application")
        else:
            lines.append(f"SKCC {app_data['award_name']} Award Application")
        
        lines.append(f"Version: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}")
        lines.append("")
        lines.append(f"Name: {operator_name}")
        lines.append(f"Call: {self.my_callsign}")
        lines.append(f"SKCC #: {self.my_skcc}")
        lines.append(f"City & State: {city_state}")
        lines.append("")
        lines.append("=" * 110)
        lines.append("CHECK YOUR LOG CAREFULLY FOR DUPLICATE CALLSIGNS AND SKCC NUMBERS.")
        lines.append("THESE ARE CAUSE FOR IMMEDIATE REJECTION.")
        lines.append("=" * 110)
        lines.append("")
        
        # Table header matching ODF template columns
        lines.append(f"{'QSO':<4} {'Date':<12} {'Call':<12} {'SKCC':<12} {'Name':<20} {'SPC':<15} {'Band':<8}")
        lines.append(f"{'#':<4} {'MM/DD/YY':<12} {'':<12} {'':<12} {'':<20} {'':<15} {'':<8}")
        lines.append("-" * 110)
        
        # Data rows - get name from contacts if available
        for idx, contact in enumerate(app_data['contacts'], 1):
            qso_date = contact.get('qso_date', '')
            # Format date as MM/DD/YY
            if qso_date and len(str(qso_date)) == 8:
                date_str = str(qso_date)
                formatted_date = f"{date_str[4:6]}/{date_str[6:8]}/{date_str[2:4]}"
            else:
                formatted_date = str(qso_date) if qso_date else ''
            
            call = str(contact.get('callsign', ''))[:12] if contact.get('callsign') else ''
            skcc = str(contact.get('skcc_number', ''))[:12] if contact.get('skcc_number') else ''
            
            # Try to get name from notes if it's formatted as "name, location"
            name = ''
            notes = contact.get('notes', '')
            if notes and isinstance(notes, str):
                # Common format: "NAME, CITY"
                parts = notes.split(',')
                if parts:
                    name = parts[0].strip()[:20]
            
            # SPC = State/Province/Country
            state = str(contact.get('state', ''))[:15] if contact.get('state') else ''
            country = str(contact.get('country', ''))[:15] if contact.get('country') else ''
            spc = state if state else country
            
            band = str(contact.get('band', ''))[:8] if contact.get('band') else ''
            
            lines.append(f"{idx:<4} {formatted_date:<12} {call:<12} {skcc:<12} {name:<20} {spc:<15} {band:<8}")
        
        lines.append("-" * 110)
        lines.append("")
        lines.append("*SPC: State/Province/Country")
        lines.append("")
        lines.append("")
        lines.append("I certify that the above contacts were made as stated.")
        lines.append("")
        lines.append("__________________________")
        lines.append("Your signature")
        lines.append("( Type in full name if filing electronically )")
        lines.append("")
        lines.append("__________________________")
        lines.append("Your callsign")
        lines.append("")
        lines.append(f"Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}")
        lines.append("")
        lines.append("")
        
        # Submission instructions matching ODF template
        if award_type.lower() == 'tribune':
            lines.append("Submit initial award application by email to:")
            lines.append("Ron Bower, AC2C, eMail address: AC2C@SKCCgroup.com")
            lines.append("Tribune Award Administrator")
            lines.append("")
            lines.append("Submit additional award applications by email to:")
            lines.append("Tx2Manager@SKCCgroup.com")
            lines.append("Asst. Tribune Award Administrator")
            lines.append("")
            lines.append("Please do not use US Mail without first contacting AC2C.")
        else:
            lines.append(f"Submit to: {app_data.get('award_manager', 'See SKCC website for current manager')}")
        
        lines.append("")
        lines.append(f"Generated by W4GNS Logger on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        
        return "\n".join(lines)

    def export_application_to_file(
        self,
        application_text: str,
        file_path: str
    ) -> bool:
        """
        Export application to file

        Args:
            application_text: Formatted application text
            file_path: Path to save file

        Returns:
            True if successful, False otherwise
        """
        try:
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)

            with open(path, 'w', encoding='utf-8') as f:
                f.write(application_text)

            logger.info(f"Award application exported to {file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to export application to {file_path}: {e}")
            return False
