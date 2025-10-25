"""
Data Access Layer - Repository Pattern Implementation

Provides abstraction for database operations.
"""

import logging
from typing import List, Optional, Dict, Any
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError

from .models import Base, Contact, QSLRecord, AwardProgress, ClusterSpot, CenturionMember, TribuneeMember
from .skcc_membership import SKCCMembershipManager

logger = logging.getLogger(__name__)


class DatabaseRepository:
    """Repository for database operations"""

    def __init__(self, db_path: str):
        """
        Initialize database connection

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.engine = create_engine(f"sqlite:///{db_path}", echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

        # Create tables if they don't exist
        Base.metadata.create_all(self.engine)

        # Initialize SKCC membership manager
        self.skcc_members = SKCCMembershipManager(db_path)

        logger.info(f"Database initialized: {db_path}")

    def get_session(self) -> Session:
        """Get a new database session"""
        return self.SessionLocal()

    # ==================== Contact Operations ====================

    def add_contact(self, contact: Contact) -> Contact:
        """Add a new contact

        Validates SKCC contacts are CW-only.
        """
        session = self.get_session()
        try:
            # Validate SKCC constraints
            contact.validate_skcc()

            session.add(contact)
            session.commit()
            logger.info(f"Contact added: {contact.callsign}")
            return contact
        except ValueError as e:
            session.rollback()
            logger.error(f"Contact validation failed: {e}")
            raise
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Failed to add contact: {e}")
            raise
        finally:
            session.close()

    def get_contact(self, contact_id: int) -> Optional[Contact]:
        """Get contact by ID"""
        session = self.get_session()
        try:
            return session.query(Contact).filter(Contact.id == contact_id).first()
        finally:
            session.close()

    def get_contacts_by_callsign(self, callsign: str) -> List[Contact]:
        """Get all contacts for a callsign"""
        session = self.get_session()
        try:
            return session.query(Contact).filter(Contact.callsign == callsign).all()
        finally:
            session.close()

    def get_all_contacts(self, limit: int = 1000, offset: int = 0) -> List[Contact]:
        """Get all contacts with pagination"""
        session = self.get_session()
        try:
            return session.query(Contact).offset(offset).limit(limit).all()
        finally:
            session.close()

    def search_contacts(self, **filters) -> List[Contact]:
        """Search contacts by multiple criteria"""
        session = self.get_session()
        try:
            query = session.query(Contact)
            if "callsign" in filters:
                query = query.filter(Contact.callsign.ilike(f"%{filters['callsign']}%"))
            if "band" in filters:
                query = query.filter(Contact.band == filters["band"])
            if "mode" in filters:
                query = query.filter(Contact.mode == filters["mode"])
            if "country" in filters:
                query = query.filter(Contact.country.ilike(f"%{filters['country']}%"))
            if "date_from" in filters:
                query = query.filter(Contact.qso_date >= filters["date_from"])
            if "date_to" in filters:
                query = query.filter(Contact.qso_date <= filters["date_to"])
            return query.all()
        finally:
            session.close()

    def update_contact(self, contact_id: int, **updates) -> Optional[Contact]:
        """Update contact by ID

        Validates SKCC contacts remain CW-only after updates.
        """
        session = self.get_session()
        try:
            contact = session.query(Contact).filter(Contact.id == contact_id).first()
            if contact:
                for key, value in updates.items():
                    setattr(contact, key, value)
                # Validate SKCC constraints after updates
                contact.validate_skcc()
                session.commit()
                logger.info(f"Contact updated: {contact_id}")
            return contact
        except ValueError as e:
            session.rollback()
            logger.error(f"Contact validation failed: {e}")
            raise
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Failed to update contact: {e}")
            raise
        finally:
            session.close()

    def delete_contact(self, contact_id: int) -> bool:
        """Delete contact by ID"""
        session = self.get_session()
        try:
            contact = session.query(Contact).filter(Contact.id == contact_id).first()
            if contact:
                session.delete(contact)
                session.commit()
                logger.info(f"Contact deleted: {contact_id}")
                return True
            return False
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Failed to delete contact: {e}")
            raise
        finally:
            session.close()

    def get_contact_count(self) -> int:
        """Get total number of contacts"""
        session = self.get_session()
        try:
            return session.query(func.count(Contact.id)).scalar()
        finally:
            session.close()

    # ==================== Award Operations ====================

    def add_award_progress(self, award: AwardProgress) -> AwardProgress:
        """Add award progress record"""
        session = self.get_session()
        try:
            session.add(award)
            session.commit()
            logger.info(f"Award progress added: {award.award_name}")
            return award
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Failed to add award: {e}")
            raise
        finally:
            session.close()

    def get_award_progress(self, program: str, name: str) -> Optional[AwardProgress]:
        """Get award progress by program and name"""
        session = self.get_session()
        try:
            return session.query(AwardProgress).filter(
                AwardProgress.award_program == program,
                AwardProgress.award_name == name
            ).first()
        finally:
            session.close()

    def get_all_awards(self) -> List[AwardProgress]:
        """Get all award progress records"""
        session = self.get_session()
        try:
            return session.query(AwardProgress).all()
        finally:
            session.close()

    def update_award_progress(
        self, program: str, name: str, **updates
    ) -> Optional[AwardProgress]:
        """Update award progress"""
        session = self.get_session()
        try:
            award = session.query(AwardProgress).filter(
                AwardProgress.award_program == program,
                AwardProgress.award_name == name
            ).first()
            if award:
                for key, value in updates.items():
                    setattr(award, key, value)
                session.commit()
                logger.info(f"Award updated: {program} - {name}")
            return award
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Failed to update award: {e}")
            raise
        finally:
            session.close()

    # ==================== SKCC (Straight Key Century Club) Operations ====================

    def get_contacts_by_skcc(self, skcc_number: str) -> List[Contact]:
        """Get all CW contacts for a specific SKCC member number

        SKCC contacts are CW-only by definition.
        """
        session = self.get_session()
        try:
            return session.query(Contact).filter(
                Contact.skcc_number == skcc_number,
                Contact.mode == "CW"
            ).all()
        finally:
            session.close()

    def get_skcc_statistics(self) -> Dict[str, Any]:
        """Get SKCC award statistics (CW-only)"""
        session = self.get_session()
        try:
            skcc_contacts = session.query(func.count(Contact.id)).filter(
                Contact.skcc_number.isnot(None),
                Contact.mode == "CW"
            ).scalar()
            unique_skcc_members = session.query(func.count(func.distinct(Contact.skcc_number))).filter(
                Contact.skcc_number.isnot(None),
                Contact.mode == "CW"
            ).scalar()

            return {
                "total_skcc_contacts": skcc_contacts or 0,
                "unique_skcc_members": unique_skcc_members or 0,
            }
        finally:
            session.close()

    def search_skcc_by_band(self, skcc_number: str, band: str = None) -> List[Contact]:
        """Search SKCC contacts by band (CW-only, mode parameter not accepted)

        SKCC contacts are always CW mode.
        """
        session = self.get_session()
        try:
            query = session.query(Contact).filter(
                Contact.skcc_number == skcc_number,
                Contact.mode == "CW"
            )
            if band:
                query = query.filter(Contact.band == band)
            return query.all()
        finally:
            session.close()

    # ==================== Key Type Operations ====================

    def get_contacts_by_key_type(self, key_type: str) -> List[Contact]:
        """Get all contacts by key type (STRAIGHT, BUG, SIDESWIPER)"""
        session = self.get_session()
        try:
            return session.query(Contact).filter(Contact.key_type == key_type).all()
        finally:
            session.close()

    def get_key_type_statistics(self) -> Dict[str, Any]:
        """Get statistics for key type usage"""
        session = self.get_session()
        try:
            straight = session.query(func.count(Contact.id)).filter(
                Contact.key_type == "STRAIGHT"
            ).scalar()
            bug = session.query(func.count(Contact.id)).filter(
                Contact.key_type == "BUG"
            ).scalar()
            sideswiper = session.query(func.count(Contact.id)).filter(
                Contact.key_type == "SIDESWIPER"
            ).scalar()

            return {
                "straight_key": straight or 0,
                "bug": bug or 0,
                "sideswiper": sideswiper or 0,
                "total_key_contacts": (straight or 0) + (bug or 0) + (sideswiper or 0),
            }
        finally:
            session.close()

    def search_contacts_by_key_type_and_band(self, key_type: str, band: str = None) -> List[Contact]:
        """Search contacts by key type and optionally by band"""
        session = self.get_session()
        try:
            query = session.query(Contact).filter(Contact.key_type == key_type)
            if band:
                query = query.filter(Contact.band == band)
            return query.all()
        finally:
            session.close()

    def get_triple_key_progress(self, callsign: str = None) -> Dict[str, Any]:
        """Get Triple Key award progress (300 QSOs with 3 key types)

        Triple Key Award requires:
        - 300 total QSOs
        - Using all 3 key types (STRAIGHT, BUG, SIDESWIPER)

        Args:
            callsign: Optional specific callsign to track. If None, counts all contacts.

        Returns:
            Dict with progress toward Triple Key award
        """
        session = self.get_session()
        try:
            base_query = session.query(Contact)
            if callsign:
                base_query = base_query.filter(Contact.callsign == callsign)

            straight_count = base_query.filter(
                Contact.key_type == "STRAIGHT"
            ).count()
            bug_count = base_query.filter(Contact.key_type == "BUG").count()
            sideswiper_count = base_query.filter(
                Contact.key_type == "SIDESWIPER"
            ).count()

            total_contacts = base_query.count()
            key_types_used = sum([
                1 for count in [straight_count, bug_count, sideswiper_count]
                if count > 0
            ])

            return {
                "straight_key_qsos": straight_count,
                "bug_qsos": bug_count,
                "sideswiper_qsos": sideswiper_count,
                "total_qsos": total_contacts,
                "key_types_used": key_types_used,
                "triple_key_qualified": total_contacts >= 300 and key_types_used == 3,
                "progress_to_300": f"{min(total_contacts, 300)}/300",
                "all_key_types_used": key_types_used == 3,
            }
        finally:
            session.close()

    # ==================== SKCC Contact Window & Award Tracking ====================

    def get_skcc_contact_history(self, skcc_number: str) -> List[Dict[str, Any]]:
        """Get all SKCC contacts with contact history details

        Returns comprehensive contact history for a specific SKCC member
        including their suffix at contact time vs current suffix.

        Args:
            skcc_number: SKCC member number (with or without suffix)

        Returns:
            List of dicts with contact details and award info
        """
        session = self.get_session()
        try:
            # Remove suffix if included to search base number
            base_skcc = skcc_number.rstrip('CTStx0123456789') if skcc_number else None

            # Query for exact match or base number match
            contacts = session.query(Contact).filter(
                Contact.skcc_number.ilike(f"{base_skcc}%")
                if base_skcc else Contact.skcc_number == skcc_number
            ).order_by(Contact.qso_date.desc(), Contact.time_on.desc()).all()

            result = []
            for contact in contacts:
                result.append({
                    'contact_id': contact.id,
                    'callsign': contact.callsign,
                    'qso_date': contact.qso_date,
                    'time_on': contact.time_on,
                    'band': contact.band,
                    'mode': contact.mode,
                    'key_type': contact.key_type,
                    'skcc_number': contact.skcc_number,  # Historical suffix
                    'rst_sent': contact.rst_sent,
                    'rst_rcvd': contact.rst_rcvd,
                    'notes': contact.notes,
                })

            return result
        finally:
            session.close()

    def count_contacts_by_achievement_level(
        self, skcc_number: str, level_filter: str = None
    ) -> Dict[str, int]:
        """Count contacts by SKCC achievement level

        Analyzes contact history to count how many contacts were made
        with members at each achievement level (C, T, S).

        Args:
            skcc_number: SKCC member number to analyze
            level_filter: Optional filter (C, T, S) - if None, returns all

        Returns:
            Dict with counts: {centurion: X, tribune: Y, senator: Z}
        """
        session = self.get_session()
        try:
            base_skcc = skcc_number.rstrip('CTStx0123456789') if skcc_number else None

            # Get all contacts with this member
            contacts = session.query(Contact).filter(
                Contact.skcc_number.ilike(f"{base_skcc}%")
                if base_skcc else Contact.skcc_number == skcc_number
            ).all()

            counts = {
                'centurion': 0,
                'tribune': 0,
                'senator': 0,
                'total': len(contacts)
            }

            for contact in contacts:
                skcc = contact.skcc_number or ""
                if skcc.endswith('C'):
                    counts['centurion'] += 1
                elif 'T' in skcc or 'x' in skcc.lower():
                    counts['tribune'] += 1
                elif skcc.endswith('S'):
                    counts['senator'] += 1

            return counts
        finally:
            session.close()

    def analyze_skcc_award_eligibility(self, skcc_number: str) -> Dict[str, Any]:
        """Comprehensive SKCC award eligibility analysis

        Analyzes all SKCC awards and eligibility status for detailed
        contact window display.

        Args:
            skcc_number: SKCC member number

        Returns:
            Dict with eligibility info for all SKCC awards
        """
        session = self.get_session()
        try:
            # Get contact history
            contacts = session.query(Contact).filter(
                Contact.skcc_number.ilike(f"{skcc_number}%")
            ).all()

            total_contacts = len(contacts)

            # Count by level
            centurion_count = sum(1 for c in contacts if c.skcc_number.endswith('C'))
            tribune_count = sum(1 for c in contacts if 'T' in c.skcc_number or 'x' in c.skcc_number.lower())
            senator_count = sum(1 for c in contacts if c.skcc_number.endswith('S'))

            # Count by key type
            straight_count = sum(1 for c in contacts if c.key_type == "STRAIGHT")
            bug_count = sum(1 for c in contacts if c.key_type == "BUG")
            sideswiper_count = sum(1 for c in contacts if c.key_type == "SIDESWIPER")

            # Count unique states and countries
            unique_states = len(set(c.state for c in contacts if c.state))
            unique_countries = len(set(c.country for c in contacts if c.country))

            # Count unique continents (simplified)
            unique_continents = len(set(
                c.dxcc for c in contacts if c.dxcc
            )) // 20  # Rough estimate

            return {
                'total_contacts': total_contacts,
                'centurion': {
                    'qualified': centurion_count >= 100,
                    'count': centurion_count,
                    'requirement': 100,
                },
                'tribune': {
                    'qualified': tribune_count >= 50 and centurion_count >= 100,
                    'count': tribune_count,
                    'requirement': 50,
                    'prerequisite': 'Centurion',
                },
                'senator': {
                    'qualified': senator_count >= 200 and tribune_count >= 400,
                    'count': senator_count,
                    'requirement': 200,
                    'prerequisite': 'Tribune Tx8',
                    'total_requirement': 600,
                },
                'triple_key': {
                    'straight_key': straight_count,
                    'bug': bug_count,
                    'sideswiper': sideswiper_count,
                    'total': straight_count + bug_count + sideswiper_count,
                    'requirement': 300,
                    'all_types_used': all([straight_count > 0, bug_count > 0, sideswiper_count > 0]),
                    'qualified': (straight_count + bug_count + sideswiper_count >= 300
                                 and all([straight_count > 0, bug_count > 0, sideswiper_count > 0])),
                },
                'geographic': {
                    'was': {
                        'count': unique_states,
                        'requirement': 50,
                        'qualified': unique_states >= 50,
                    },
                    'continents': {
                        'count': unique_continents,
                        'requirement': 6,
                        'qualified': unique_continents >= 6,
                    },
                },
            }
        finally:
            session.close()

    def get_skcc_member_summary(self, skcc_number: str) -> Dict[str, Any]:
        """Get quick summary of SKCC member for contact window

        Returns summary info for display in contact history window.

        Args:
            skcc_number: SKCC member number

        Returns:
            Dict with current status and stats
        """
        session = self.get_session()
        try:
            # Get latest contact with this member
            latest = session.query(Contact).filter(
                Contact.skcc_number.ilike(f"{skcc_number}%")
            ).order_by(Contact.qso_date.desc()).first()

            if not latest:
                return {'found': False}

            # Count total contacts
            total = session.query(func.count(Contact.id)).filter(
                Contact.skcc_number.ilike(f"{skcc_number}%")
            ).scalar()

            # Count by key type
            by_key = session.query(
                Contact.key_type,
                func.count(Contact.id).label('count')
            ).filter(
                Contact.skcc_number.ilike(f"{skcc_number}%")
            ).group_by(Contact.key_type).all()

            key_breakdown = {key: count for key, count in by_key}

            return {
                'found': True,
                'callsign': latest.callsign,
                'skcc_number': latest.skcc_number,
                'total_contacts': total,
                'last_contact_date': latest.qso_date,
                'last_contact_time': latest.time_on,
                'last_band': latest.band,
                'key_breakdown': key_breakdown,
                'notes': latest.notes,
            }
        finally:
            session.close()

    # ==================== QRP Power Tracking ====================

    def get_qrp_contacts(self, skip_filter: bool = False) -> List[Contact]:
        """Get all QRP contacts (≤5W transmit power)

        Args:
            skip_filter: If True, return all contacts regardless of power

        Returns:
            List of contacts with tx_power ≤ 5W
        """
        session = self.get_session()
        try:
            query = session.query(Contact)
            if not skip_filter:
                query = query.filter(Contact.tx_power.isnot(None))
                query = query.filter(Contact.tx_power <= 5.0)
            return query.all()
        finally:
            session.close()

    def count_qrp_points_by_band(self) -> Dict[str, Any]:
        """Count QRP points per band for QRP x1 award

        SKCC QRP x1 point distribution:
        - 160m: 4 points
        - 80m, 10m: 3 points
        - 60m, 40m, 30m: 2 points
        - 20m, 17m, 15m, 12m: 1 point
        - 6m, 2m: 0.5 points

        Returns:
            Dict with band as key and points as value for all QRP contacts
        """
        point_map = {
            "160M": 4,
            "80M": 3,
            "60M": 2,
            "40M": 2,
            "30M": 2,
            "20M": 1,
            "17M": 1,
            "15M": 1,
            "12M": 1,
            "10M": 3,
            "6M": 0.5,
            "2M": 0.5,
        }

        session = self.get_session()
        try:
            # Get all QRP contacts grouped by band (one per band only)
            qrp_contacts = session.query(Contact).filter(
                Contact.tx_power.isnot(None),
                Contact.tx_power <= 5.0,
                Contact.mode == "CW"
            ).all()

            # Track one contact per band only
            band_contacts = {}
            for contact in qrp_contacts:
                band = contact.band
                if band not in band_contacts:
                    band_contacts[band] = contact

            # Calculate points
            band_points = {}
            total_points = 0
            for band, contact in band_contacts.items():
                points = point_map.get(band, 0)
                band_points[band] = points
                total_points += points

            return {
                "band_points": band_points,
                "total_points": total_points,
                "qrp_contacts_count": len(qrp_contacts),
                "unique_bands": len(band_contacts),
            }
        finally:
            session.close()

    def analyze_qrp_award_progress(self) -> Dict[str, Any]:
        """Complete QRP x1 and x2 award analysis

        Analyzes all QRP contacts and calculates progress toward:
        - QRP x1: 300 points (your power ≤5W)
        - QRP x2: 150 points (both stations ≤5W)

        Returns:
            Dict with QRP x1 and x2 progress analysis
        """
        session = self.get_session()
        try:
            point_map = {
                "160M": 4, "80M": 3, "60M": 2, "40M": 2, "30M": 2,
                "20M": 1, "17M": 1, "15M": 1, "12M": 1, "10M": 3,
                "6M": 0.5, "2M": 0.5,
            }

            # Get all CW QRP contacts
            qrp_contacts = session.query(Contact).filter(
                Contact.tx_power.isnot(None),
                Contact.tx_power <= 5.0,
                Contact.mode == "CW"
            ).order_by(Contact.qso_date).all()

            # Track one contact per band for points calculation
            band_contacts_x1 = {}
            qrp_x1_points = 0

            # Track 2-way QRP (both ≤5W)
            qrp_x2_contacts = []

            for contact in qrp_contacts:
                band = contact.band

                # QRP x1: Track first contact per band
                if band not in band_contacts_x1:
                    band_contacts_x1[band] = contact
                    points = point_map.get(band, 0)
                    qrp_x1_points += points

                # QRP x2: Check if other station also ≤5W
                if contact.rx_power is not None and contact.rx_power <= 5.0:
                    qrp_x2_contacts.append(contact)

            # Calculate points for QRP x2 (one per band)
            band_contacts_x2 = {}
            qrp_x2_points = 0
            for contact in qrp_x2_contacts:
                band = contact.band
                if band not in band_contacts_x2:
                    band_contacts_x2[band] = contact
                    points = point_map.get(band, 0)
                    qrp_x2_points += points

            return {
                "qrp_x1": {
                    "points": qrp_x1_points,
                    "requirement": 300,
                    "qualified": qrp_x1_points >= 300,
                    "progress": f"{qrp_x1_points}/300",
                    "unique_bands": len(band_contacts_x1),
                    "contacts": len(qrp_contacts),
                },
                "qrp_x2": {
                    "points": qrp_x2_points,
                    "requirement": 150,
                    "qualified": qrp_x2_points >= 150,
                    "progress": f"{qrp_x2_points}/150",
                    "unique_bands": len(band_contacts_x2),
                    "contacts": len(qrp_x2_contacts),
                },
                "band_breakdown": {
                    "x1": {band: point_map.get(band, 0) for band in band_contacts_x1},
                    "x2": {band: point_map.get(band, 0) for band in band_contacts_x2},
                },
            }
        finally:
            session.close()

    def calculate_mpw_qualifications(self) -> List[Dict[str, Any]]:
        """Find all MPW-qualifying contacts

        QRP MPW Award requires:
        - Distance / Power ≥ 1000 MPW
        - Power ≤ 5W
        - Entire QSO conducted at ≤5W

        Note: Requires distance field to be populated in contact record.
        Contacts without distance data are excluded.

        Returns:
            List of qualifying contacts with MPW calculation
        """
        session = self.get_session()
        try:
            qrp_contacts = session.query(Contact).filter(
                Contact.tx_power.isnot(None),
                Contact.tx_power <= 5.0,
                Contact.distance.isnot(None),
                Contact.distance > 0,
                Contact.mode == "CW"
            ).all()

            mpw_qualifications = []
            for contact in qrp_contacts:
                # Convert distance from km to miles if needed (assume already in miles)
                distance_miles = contact.distance
                mpw = contact.calculate_mpw(distance_miles)

                if contact.qualifies_for_mpw(distance_miles):
                    mpw_qualifications.append({
                        "contact_id": contact.id,
                        "callsign": contact.callsign,
                        "date": contact.qso_date,
                        "time": contact.time_on,
                        "band": contact.band,
                        "distance_miles": distance_miles,
                        "tx_power": contact.tx_power,
                        "mpw": mpw,
                        "qualified": True,
                    })

            return mpw_qualifications
        finally:
            session.close()

    def get_power_statistics(self) -> Dict[str, Any]:
        """Get overall power statistics across all contacts

        Returns:
            Dict with power category breakdown and statistics
        """
        session = self.get_session()
        try:
            # Get all contacts with power data
            contacts = session.query(Contact).filter(
                Contact.tx_power.isnot(None)
            ).all()

            if not contacts:
                return {
                    "total_with_power": 0,
                    "qrpp_count": 0,
                    "qrp_count": 0,
                    "standard_count": 0,
                    "qro_count": 0,
                    "unknown_count": 0,
                    "average_power": 0,
                    "min_power": 0,
                    "max_power": 0,
                }

            # Categorize by power level
            categories = {"QRPp": 0, "QRP": 0, "STANDARD": 0, "QRO": 0, "UNKNOWN": 0}
            powers = []

            for contact in contacts:
                category = contact.get_qrp_category()
                categories[category] += 1
                powers.append(contact.tx_power)

            return {
                "total_with_power": len(contacts),
                "qrpp_count": categories["QRPp"],
                "qrp_count": categories["QRP"],
                "standard_count": categories["STANDARD"],
                "qro_count": categories["QRO"],
                "unknown_count": categories["UNKNOWN"],
                "average_power": sum(powers) / len(powers) if powers else 0,
                "min_power": min(powers) if powers else 0,
                "max_power": max(powers) if powers else 0,
                "categories": categories,
            }
        finally:
            session.close()

    # ==================== Statistics ====================

    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics"""
        session = self.get_session()
        try:
            contact_count = session.query(func.count(Contact.id)).scalar()
            unique_callsigns = session.query(func.count(func.distinct(Contact.callsign))).scalar()
            unique_countries = session.query(func.count(func.distinct(Contact.country))).scalar()
            unique_bands = session.query(func.count(func.distinct(Contact.band))).scalar()

            return {
                "total_contacts": contact_count or 0,
                "unique_callsigns": unique_callsigns or 0,
                "unique_countries": unique_countries or 0,
                "unique_bands": unique_bands or 0,
            }
        finally:
            session.close()

    # ==================== ADIF Import/Export ====================

    def _clean_adif_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Clean and normalize ADIF record data

        Handles:
        - Stripping whitespace from all values
        - Converting HHMMSS time format to HHMM
        - Converting numeric fields
        - Removing invalid fields
        - Normalizing string values

        Args:
            record: Raw ADIF record dictionary

        Returns:
            Cleaned record dictionary
        """
        cleaned = {}

        for key, value in record.items():
            if value is None:
                continue

            # Skip unmapped or invalid fields
            if not hasattr(Contact, key):
                # Try lowercase version
                if not hasattr(Contact, key.lower()):
                    continue
                key = key.lower()

            # Convert value to string first to handle all types
            value_str = str(value).strip()

            if not value_str:
                continue

            # Handle time fields (convert HHMMSS to HHMM if needed)
            if key in ['time_on', 'time_off']:
                if len(value_str) == 6:  # HHMMSS format
                    value_str = value_str[:4]  # Take first 4 chars (HHMM)
                cleaned[key] = value_str
            # Handle numeric fields
            elif key in ['frequency', 'freq_rx', 'tx_power', 'rx_power', 'dxcc',
                        'cqz', 'ituz', 'a_index', 'k_index', 'sfi', 'antenna_az',
                        'antenna_el', 'distance']:
                try:
                    if key in ['frequency', 'freq_rx']:
                        cleaned[key] = float(value_str)
                    else:
                        cleaned[key] = int(float(value_str))
                except (ValueError, TypeError):
                    logger.debug(f"Could not convert {key}={value_str} to numeric")
            # Handle string fields
            else:
                cleaned[key] = value_str

        return cleaned

    def import_contacts_from_adif(
        self,
        adif_records: List[Dict[str, Any]],
        conflict_strategy: str = "skip"
    ) -> Dict[str, Any]:
        """Import contacts from parsed ADIF records

        Args:
            adif_records: List of contact dictionaries from ADIF parser
            conflict_strategy: How to handle duplicates - "skip", "update", or "append"
                - "skip": Don't import duplicates (default)
                - "update": Update existing contacts with new data
                - "append": Add all records even if duplicates exist

        Returns:
            Dictionary with import statistics:
            {
                "imported": count of newly imported contacts,
                "updated": count of updated contacts,
                "skipped": count of skipped duplicates,
                "failed": count of failed imports,
                "errors": list of error messages
            }
        """
        stats = {
            "imported": 0,
            "updated": 0,
            "skipped": 0,
            "failed": 0,
            "errors": []
        }

        session = self.get_session()
        try:
            for record_data in adif_records:
                try:
                    # Clean and prepare record data
                    cleaned_data = self._clean_adif_record(record_data)

                    # Check for existing contact
                    existing = session.query(Contact).filter(
                        Contact.callsign == cleaned_data.get("callsign"),
                        Contact.qso_date == cleaned_data.get("qso_date"),
                        Contact.time_on == cleaned_data.get("time_on"),
                        Contact.band == cleaned_data.get("band")
                    ).first()

                    if existing:
                        if conflict_strategy == "skip":
                            stats["skipped"] += 1
                            continue
                        elif conflict_strategy == "update":
                            # Update existing contact
                            for key, value in cleaned_data.items():
                                if hasattr(existing, key) and value is not None:
                                    setattr(existing, key, value)
                            existing.validate_skcc()
                            session.add(existing)
                            stats["updated"] += 1
                            continue
                        # "append" falls through to add new record

                    # Create new contact
                    contact = Contact()
                    for key, value in cleaned_data.items():
                        if hasattr(contact, key) and value is not None:
                            setattr(contact, key, value)

                    # Set defaults if not provided
                    if not contact.mode:
                        contact.mode = "CW"

                    # Validate SKCC constraints
                    contact.validate_skcc()

                    session.add(contact)
                    stats["imported"] += 1

                except ValueError as e:
                    stats["failed"] += 1
                    callsign = record_data.get('callsign', 'Unknown')
                    if isinstance(callsign, str):
                        callsign = callsign.replace('\n', '').strip()
                    stats["errors"].append(f"{callsign}: {str(e)}")
                    logger.warning(f"Failed to import contact: {e}")
                except Exception as e:
                    stats["failed"] += 1
                    callsign = record_data.get('callsign', 'Unknown')
                    if isinstance(callsign, str):
                        callsign = callsign.replace('\n', '').strip()
                    stats["errors"].append(f"{callsign}: {str(e)}")
                    logger.error(f"Error importing contact: {e}")

            # Commit all changes
            session.commit()
            logger.info(
                f"Import complete - Imported: {stats['imported']}, "
                f"Updated: {stats['updated']}, Skipped: {stats['skipped']}, "
                f"Failed: {stats['failed']}"
            )

        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error during import: {e}")
            stats["errors"].insert(0, f"Database error: {str(e)}")
        finally:
            session.close()

        return stats

    # ==================== Cluster Spot Operations ====================

    def add_cluster_spot(self, spot_data: Dict[str, Any]) -> Optional[ClusterSpot]:
        """Add a cluster spot to the database

        Args:
            spot_data: Dictionary with spot information

        Returns:
            The ClusterSpot object if successful, None otherwise
        """
        session = self.get_session()
        try:
            spot = ClusterSpot(**spot_data)
            session.add(spot)
            session.commit()
            logger.debug(f"Added cluster spot: {spot_data.get('dx_callsign')}")
            return spot
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error adding cluster spot: {e}")
            return None
        finally:
            session.close()

    def get_recent_spots(self, limit: int = 50) -> List[ClusterSpot]:
        """Get recent cluster spots

        Args:
            limit: Maximum number of spots to return

        Returns:
            List of recent ClusterSpot objects
        """
        session = self.get_session()
        try:
            spots = session.query(ClusterSpot).order_by(
                ClusterSpot.received_at.desc()
            ).limit(limit).all()
            return spots
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving spots: {e}")
            return []
        finally:
            session.close()

    def get_spots_by_band(self, band: str, limit: int = 50) -> List[ClusterSpot]:
        """Get cluster spots for a specific band

        Args:
            band: Band name (e.g., "20M", "40M")
            limit: Maximum number of spots to return

        Returns:
            List of ClusterSpot objects for the band
        """
        session = self.get_session()
        try:
            # Convert band to frequency range
            band_ranges = {
                "160M": (1.8, 2.0),
                "80M": (3.5, 4.0),
                "60M": (5.1, 5.4),
                "40M": (7.0, 7.3),
                "30M": (10.1, 10.15),
                "20M": (14.0, 14.35),
                "17M": (18.068, 18.168),
                "15M": (21.0, 21.45),
                "12M": (24.89, 24.99),
                "10M": (28.0, 29.7),
                "6M": (50.0, 54.0),
                "2M": (144.0, 148.0),
                "70cm": (420.0, 450.0),
            }

            freq_range = band_ranges.get(band)
            if not freq_range:
                return []

            spots = session.query(ClusterSpot).filter(
                ClusterSpot.frequency >= freq_range[0],
                ClusterSpot.frequency <= freq_range[1]
            ).order_by(
                ClusterSpot.received_at.desc()
            ).limit(limit).all()

            return spots
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving spots for band {band}: {e}")
            return []
        finally:
            session.close()

    def analyze_centurion_award_progress(self) -> Dict[str, Any]:
        """Analyze Centurion award progress

        Tracks unique SKCC members contacted via CW.
        Endorsements available in 100-contact increments up to Cx10,
        then in 500-contact increments (Cx15, Cx20, etc.).

        Returns:
            Dict with Centurion progress analysis
        """
        session = self.get_session()
        try:
            # Get all CW contacts with SKCC numbers
            centurion_contacts = session.query(Contact).filter(
                Contact.mode == "CW",
                Contact.skcc_number.isnot(None)
            ).order_by(Contact.qso_date).all()

            # Collect unique SKCC members (base number without suffixes)
            unique_members = set()
            member_details = {}

            for contact in centurion_contacts:
                skcc_num = contact.skcc_number.strip()
                if not skcc_num:
                    continue

                # Extract base number (remove suffix like C, T, S, x10, etc.)
                # SKCC numbers are: digits optionally followed by letter (C, T, S) or x number
                base_number = skcc_num.split()[0]  # Remove any spaces first
                # Remove letter suffix if present (C, T, S at the end)
                if base_number and base_number[-1] in 'CTS':
                    base_number = base_number[:-1]
                # Remove x multiplier if present (xN at the end)
                if base_number and 'x' in base_number:
                    base_number = base_number.split('x')[0]

                # Only add if it's a valid number
                if base_number and base_number.isdigit():
                    unique_members.add(base_number)
                    if base_number not in member_details:
                        member_details[base_number] = {
                            'callsign': contact.callsign,
                            'date': contact.qso_date,
                            'band': contact.band
                        }

            member_count = len(unique_members)

            # Calculate endorsement level
            if member_count < 100:
                endorsement = "Not Yet"
            elif member_count < 200:
                endorsement = "Centurion"
            elif member_count < 300:
                endorsement = "Centurion x2"
            elif member_count < 400:
                endorsement = "Centurion x3"
            elif member_count < 500:
                endorsement = "Centurion x4"
            elif member_count < 600:
                endorsement = "Centurion x5"
            elif member_count < 700:
                endorsement = "Centurion x6"
            elif member_count < 800:
                endorsement = "Centurion x7"
            elif member_count < 900:
                endorsement = "Centurion x8"
            elif member_count < 1000:
                endorsement = "Centurion x9"
            elif member_count < 1100:
                endorsement = "Centurion x10"
            elif member_count < 1500:
                endorsement = "Centurion x10+"
            elif member_count < 2000:
                endorsement = "Centurion x15"
            elif member_count < 2500:
                endorsement = "Centurion x20"
            elif member_count < 3000:
                endorsement = "Centurion x25"
            else:
                endorsement = f"Centurion x{(member_count // 500) * 5}"

            # Calculate next endorsement target
            next_level = ((member_count // 100) + 1) * 100
            if next_level > 1000:
                next_level = ((member_count // 500) + 1) * 500

            return {
                'unique_members': member_count,
                'required': 100,
                'achieved': member_count >= 100,
                'progress_pct': min(100.0, (member_count / 100) * 100),
                'endorsement': endorsement,
                'next_level': next_level,
                'members_to_next': max(0, next_level - member_count),
                'total_centurion_on_record': len(session.query(CenturionMember).all())
            }

        except SQLAlchemyError as e:
            logger.error(f"Error analyzing Centurion progress: {e}")
            return {
                'unique_members': 0,
                'required': 100,
                'achieved': False,
                'progress_pct': 0.0,
                'endorsement': 'Error',
                'next_level': 100,
                'members_to_next': 100
            }
        finally:
            session.close()

    def analyze_tribune_award_progress(self) -> Dict[str, Any]:
        """Analyze Tribune award progress

        Tracks unique Tribune/Senator members contacted via CW.
        Requires user to be a Centurion first (100+ unique SKCC members).
        Endorsements available in 50-contact increments up to Tx10,
        then in 250-contact increments (Tx15, Tx20, etc.).

        Returns:
            Dict with Tribune progress analysis
        """
        session = self.get_session()
        try:
            from src.services.tribune_fetcher import TribuneFetcher

            # First check if user is a Centurion
            centurion_contacts = session.query(Contact).filter(
                Contact.mode == "CW",
                Contact.skcc_number.isnot(None)
            ).all()

            unique_centurions = set()
            for contact in centurion_contacts:
                skcc_num = contact.skcc_number.strip()
                if skcc_num:
                    base_number = skcc_num.split()[0]
                    if base_number and base_number[-1] in 'CTS':
                        base_number = base_number[:-1]
                    if base_number and 'x' in base_number:
                        base_number = base_number.split('x')[0]
                    if base_number and base_number.isdigit():
                        unique_centurions.add(base_number)

            is_centurion = len(unique_centurions) >= 100

            # Get all Tribune-eligible contacts (CW + valid date + Tribune/Senator)
            tribune_eligible_date = "20070301"  # March 1, 2007

            tribune_contacts = session.query(Contact).filter(
                Contact.mode == "CW",
                Contact.skcc_number.isnot(None),
                Contact.qso_date >= tribune_eligible_date
            ).all()

            # Collect unique Tribune members
            unique_tribunes = set()
            for contact in tribune_contacts:
                skcc_num = contact.skcc_number.strip()
                if not skcc_num:
                    continue

                # Check if this is a Tribune/Senator member
                is_tribune = TribuneFetcher.is_tribune_member(session, skcc_num)
                if is_tribune:
                    base_number = skcc_num.split()[0]
                    if base_number and base_number[-1] in 'CTS':
                        base_number = base_number[:-1]
                    if base_number and 'x' in base_number:
                        base_number = base_number.split('x')[0]
                    if base_number and base_number.isdigit():
                        unique_tribunes.add(base_number)

            tribune_count = len(unique_tribunes)

            # Calculate endorsement level
            if tribune_count < 50:
                endorsement = "Not Yet"
            elif tribune_count < 100:
                endorsement = "Tribune"
            elif tribune_count < 150:
                endorsement = "Tribune x2"
            elif tribune_count < 200:
                endorsement = "Tribune x3"
            elif tribune_count < 250:
                endorsement = "Tribune x4"
            elif tribune_count < 300:
                endorsement = "Tribune x5"
            elif tribune_count < 350:
                endorsement = "Tribune x6"
            elif tribune_count < 400:
                endorsement = "Tribune x7"
            elif tribune_count < 450:
                endorsement = "Tribune x8"
            elif tribune_count < 500:
                endorsement = "Tribune x9"
            elif tribune_count < 550:
                endorsement = "Tribune x10"
            elif tribune_count < 750:
                endorsement = "Tribune x10+"
            elif tribune_count < 1000:
                endorsement = "Tribune x15"
            elif tribune_count < 1250:
                endorsement = "Tribune x20"
            else:
                endorsement = f"Tribune x{(tribune_count // 250) * 5}"

            # Calculate next endorsement target
            if tribune_count < 50:
                next_level = 50
            elif tribune_count < 550:
                next_level = ((tribune_count // 50) + 1) * 50
            else:
                next_level = ((tribune_count // 250) + 1) * 250

            return {
                'unique_tribunes': tribune_count,
                'required': 50,
                'achieved': is_centurion and tribune_count >= 50,
                'progress_pct': min(100.0, (tribune_count / 50) * 100),
                'endorsement': endorsement,
                'next_level': next_level,
                'tribunes_to_next': max(0, next_level - tribune_count),
                'is_centurion': is_centurion,
                'centurion_count': len(unique_centurions),
                'total_tribune_on_record': len(session.query(TribuneeMember).all())
            }

        except SQLAlchemyError as e:
            logger.error(f"Error analyzing Tribune progress: {e}")
            return {
                'unique_tribunes': 0,
                'required': 50,
                'achieved': False,
                'progress_pct': 0.0,
                'endorsement': 'Error',
                'next_level': 50,
                'tribunes_to_next': 50,
                'is_centurion': False,
                'centurion_count': 0
            }
        finally:
            session.close()

    def get_spots_by_callsign(self, callsign: str) -> List[ClusterSpot]:
        """Get all spots for a specific DX callsign

        Args:
            callsign: DX station callsign

        Returns:
            List of ClusterSpot objects for the callsign
        """
        session = self.get_session()
        try:
            spots = session.query(ClusterSpot).filter(
                ClusterSpot.dx_callsign == callsign.upper()
            ).order_by(
                ClusterSpot.received_at.desc()
            ).all()
            return spots
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving spots for {callsign}: {e}")
            return []
        finally:
            session.close()

    def delete_old_spots(self, hours: int = 24) -> int:
        """Delete spots older than specified hours

        Args:
            hours: Age threshold in hours

        Returns:
            Number of spots deleted
        """
        session = self.get_session()
        try:
            from datetime import datetime, timedelta
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            result = session.query(ClusterSpot).filter(
                ClusterSpot.received_at < cutoff_time
            ).delete()
            session.commit()
            logger.info(f"Deleted {result} spots older than {hours} hours")
            return result
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error deleting old spots: {e}")
            return 0
        finally:
            session.close()
