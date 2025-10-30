"""
Contact Repository - Contact CRUD Operations

Handles all contact-related database operations including:
- Adding, updating, deleting contacts
- Searching and filtering contacts
- ADIF import/export
- Contact statistics and queries
"""

import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func

from .base_repository import BaseRepository
from .models import Contact

logger = logging.getLogger(__name__)


class ContactRepository(BaseRepository):
    """Repository for contact database operations"""

    def __init__(self, db_path: str, award_cache=None, signals=None):
        """
        Initialize contact repository

        Args:
            db_path: Path to SQLite database file
            award_cache: Shared award progress cache instance
            signals: Shared app signals instance
        """
        super().__init__(db_path)
        self.award_cache = award_cache
        self.signals = signals

    # ==================== Contact CRUD Operations ====================

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

            # Invalidate caches and emit batched signal (OPTIMIZED: single signal emission)
            if self.award_cache:
                self.award_cache.invalidate_all_award_caches()
            if self.signals:
                self.signals.emit_contact_change('added', {
                    'callsign': contact.callsign,
                    'band': contact.band,
                    'mode': contact.mode
                })

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

                # Invalidate caches and emit batched signal (OPTIMIZED: single signal emission)
                if self.award_cache:
                    self.award_cache.invalidate_all_award_caches()
                if self.signals:
                    self.signals.emit_contact_change('modified', {
                        'contact_id': contact_id,
                        'callsign': contact.callsign
                    })

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
                # Save info before deletion
                callsign = contact.callsign
                session.delete(contact)
                session.commit()
                logger.info(f"Contact deleted: {contact_id}")

                # Invalidate caches and emit batched signal (OPTIMIZED: single signal emission)
                if self.award_cache:
                    self.award_cache.invalidate_all_award_caches()
                if self.signals:
                    self.signals.emit_contact_change('deleted', {
                        'contact_id': contact_id,
                        'callsign': callsign
                    })

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

    # ==================== SKCC-Specific Contact Operations ====================

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

    # ==================== Contact History ====================

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

    # ==================== Canadian Contacts ====================

    def get_canadian_contacts(self, province: str = None) -> List[Contact]:
        """Get all Canadian contacts

        Args:
            province: Optional specific province filter (e.g., "ON", "BC")

        Returns:
            List of Canadian contacts
        """
        session = self.get_session()
        try:
            query = session.query(Contact).filter(
                Contact.country.ilike("%Canada%") | Contact.dxcc == 1
            )
            if province:
                query = query.filter(Contact.state == province.upper())
            return query.all()
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

            # Emit batched signal to refresh all widgets after successful import (OPTIMIZED)
            if (stats['imported'] > 0 or stats['updated'] > 0) and self.signals:
                self.signals.emit_contact_change('bulk_import', {
                    'imported': stats['imported'],
                    'updated': stats['updated'],
                    'total': stats['imported'] + stats['updated']
                })
                logger.info(f"Emitted batched signal for {stats['imported'] + stats['updated']} contacts")

        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error during import: {e}")
            stats["errors"].insert(0, f"Database error: {str(e)}")
        finally:
            session.close()

        return stats

    # ==================== Utilities ====================

    def backfill_contact_distances(self, home_grid: str) -> Dict[str, int]:
        """
        Calculate and populate distance field for all contacts missing it.

        Processes contacts that have a grid square but no distance calculated.
        Uses the Haversine formula to calculate great-circle distance.

        Args:
            home_grid: Your home Maidenhead grid square

        Returns:
            Dict with 'updated', 'skipped', and 'errors' counts
        """
        from src.services.voacap_muf_fetcher import VOACAPMUFFetcher

        session = self.get_session()
        try:
            # Get all contacts with grid squares but no distance
            contacts_to_update = session.query(Contact).filter(
                Contact.gridsquare.isnot(None),
                Contact.gridsquare != "",
                Contact.distance.is_(None)
            ).all()

            updated = 0
            skipped = 0
            errors = 0

            logger.info(f"Found {len(contacts_to_update)} contacts to calculate distances for")

            for contact in contacts_to_update:
                try:
                    contact_grid = contact.gridsquare.strip()

                    # Validate grid square (at least 4 characters)
                    if not contact_grid or len(contact_grid) < 4:
                        skipped += 1
                        continue

                    # Calculate distance
                    distance_km = VOACAPMUFFetcher._grid_distance(home_grid, contact_grid)

                    # Update contact
                    contact.distance = distance_km
                    updated += 1

                    if updated % 100 == 0:
                        logger.info(f"Processed {updated} contacts...")
                        session.commit()  # Commit in batches

                except Exception as e:
                    logger.warning(f"Error calculating distance for {contact.callsign} ({contact.gridsquare}): {e}")
                    errors += 1
                    continue

            # Final commit
            session.commit()

            result = {
                'updated': updated,
                'skipped': skipped,
                'errors': errors,
                'total': len(contacts_to_update)
            }

            logger.info(f"Distance backfill complete: {updated} updated, {skipped} skipped, {errors} errors")
            return result

        except Exception as e:
            logger.error(f"Error during distance backfill: {e}", exc_info=True)
            session.rollback()
            raise
        finally:
            session.close()

    def _contact_to_dict(self, contact: Contact) -> dict:
        """Convert Contact ORM object to dictionary for award calculations"""
        return {
            'callsign': contact.callsign,
            'qso_date': contact.qso_date,
            'time_on': contact.time_on,
            'band': contact.band,
            'mode': contact.mode,
            'country': contact.country,
            'state': contact.state,
            'skcc_number': contact.skcc_number,
            'tx_power': contact.tx_power,
            'rx_power': contact.rx_power,
        }
