"""
Award Report Generator

Generates formatted reports for SKCC award submissions to award managers.
Supports Tribune, Centurion, Senator, and all other SKCC awards.

Report Formats:
- Plain Text: Tab-separated format for Excel/spreadsheet import
- CSV: Comma-separated values
- HTML: Formatted HTML report
- Text: Simple text report with summary and contact list

Dynamically discovers and uses award rules from award implementations.
"""
# pyright: reportOptionalMemberAccess=false, reportUnknownVariableType=false, reportGeneralTypeIssues=false, reportOptionalSubscript=false, reportIncompatibleMethodOverride=false

import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Type
from pathlib import Path
import importlib

from src.database.repository import DatabaseRepository
from src.database.models import Contact
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class AwardReportGenerator:
    """Generate formatted award reports for submission to award managers"""

    # Column headers for report formats
    REPORT_COLUMNS = [
        'QSO Date',
        'Call Sign',
        'SKCC Number',
        'Band',
        'Mode',
        'Time (UTC)',
        'RST Sent',
        'RST Rcvd',
        'Notes'
    ]

    def __init__(self, db: DatabaseRepository, my_callsign: str, my_skcc: str):
        """
        Initialize report generator

        Args:
            db: DatabaseRepository instance
            my_callsign: Operator's call sign
            my_skcc: Operator's SKCC number
        """
        self.db = db
        self.my_callsign = my_callsign
        self.my_skcc = my_skcc
        self._award_classes_cache: Dict[str, Type[Any]] = {}

    def get_available_awards(self) -> List[str]:
        """
        Get list of all available awards

        Returns:
            List of award names (e.g., ['Centurion', 'Tribune', 'Senator', 'WAS', 'WAC'])
        """
        awards = []
        award_modules = [
            'centurion', 'tribune', 'senator', 'was', 'wac', 'dxcc',
            'canadian_maple', 'rag_chew', 'pfx', 'triple_key', 'skcc_dx'
        ]

        for module_name in award_modules:
            try:
                module = importlib.import_module(f'src.awards.{module_name}')
                # Find the award class in the module
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if isinstance(attr, type) and attr_name.endswith('Award'):
                        awards.append(attr_name.replace('Award', ''))
                        self._award_classes_cache[attr_name.replace('Award', '')] = attr
            except ImportError:
                pass

        return sorted(awards)

    def get_award_class(self, award_name: str) -> Optional[Type[Any]]:
        """
        Get award class for a given award name

        Args:
            award_name: Name of award (e.g., 'Tribune', 'Centurion')

        Returns:
            Award class or None if not found
        """
        if award_name in self._award_classes_cache:
            return self._award_classes_cache[award_name]

        # Try to load it
        award_module_map = {
            'Centurion': ('src.awards.centurion', 'CenturionAward'),
            'Tribune': ('src.awards.tribune', 'TribuneAward'),
            'Senator': ('src.awards.senator', 'SenatorAward'),
            'WAS': ('src.awards.was', 'WASAward'),
            'WAC': ('src.awards.wac', 'WACAward'),
            'DXCC': ('src.awards.dxcc', 'DXCCAward'),
            'CanadianMaple': ('src.awards.canadian_maple', 'CanadianMapleAward'),
            'RagChew': ('src.awards.rag_chew', 'RagChewAward'),
            'PFX': ('src.awards.pfx', 'PFXAward'),
            'TripleKey': ('src.awards.triple_key', 'TripleKeyAward'),
            'SKCCDx': ('src.awards.skcc_dx', 'DXQAward'),
        }

        if award_name in award_module_map:
            module_path, class_name = award_module_map[award_name]
            try:
                module = importlib.import_module(module_path)
                award_class = getattr(module, class_name)
                self._award_classes_cache[award_name] = award_class
                return award_class
            except (ImportError, AttributeError):
                logger.warning(f"Could not load award class {class_name}")
                return None

        return None

    def generate_report(
        self,
        award_name: str,
        format: str = 'text',
        include_summary: bool = True,
        achievement_date: Optional[str] = None
    ) -> str:
        """
        Generate award report for any SKCC award

        Args:
            award_name: Name of award ('Tribune', 'Centurion', 'Senator', etc.)
            format: Report format ('text', 'csv', 'html', 'tsv')
            include_summary: Include summary statistics
            achievement_date: Date award was achieved (YYYYMMDD) for endorsements

        Returns:
            Formatted report string
        """
        session = self.db.get_session()
        try:
            # Get award class
            award_class = self.get_award_class(award_name)
            if not award_class:
                return f"Error: Award '{award_name}' not found"

            # Get all contacts that could be valid for this award
            contacts = session.query(Contact).filter(
                Contact.mode == 'CW',
                Contact.skcc_number.isnot(None)
            ).order_by(Contact.qso_date.asc()).all()

            # Validate contacts using award rules
            # Special handling for DXCC which doesn't take session parameter
            if award_name == 'DXCC':
                award_instance = award_class()
            else:
                award_instance = award_class(session)
            
            # Track validation results for user visibility
            valid_contacts = []
            failed_validations = []
            
            for contact in contacts:
                try:
                    contact_dict = self._contact_to_dict(contact)
                    if award_instance.validate(contact_dict):
                        valid_contacts.append(contact)
                    else:
                        # Track why contact didn't qualify (for debugging)
                        failed_validations.append((contact.callsign, "Did not meet award requirements"))
                except Exception as e:
                    # Track validation errors
                    failed_validations.append((contact.callsign, str(e)))
                    logger.warning(f"Validation error for {contact.callsign}: {e}")
                    continue
            
            # Report significant validation failures to help user identify issues
            if len(failed_validations) > 0:
                logger.info(f"Award '{award_name}': {len(valid_contacts)} contacts qualified, "
                          f"{len(failed_validations)} contacts did not qualify")
                if len(failed_validations) <= 10:
                    # Show details for small number of failures
                    for call, reason in failed_validations:
                        logger.debug(f"  {call}: {reason}")

            # Filter by achievement date if provided (for endorsements)
            if achievement_date:
                filtered_contacts = [
                    c for c in valid_contacts
                    if c.qso_date is not None and str(c.qso_date) >= str(achievement_date)
                ]
            else:
                filtered_contacts = valid_contacts

            # Generate report in requested format
            if format.lower() == 'csv':
                return self._format_csv(filtered_contacts, award_name)
            elif format.lower() == 'tsv':
                return self._format_tsv(filtered_contacts, award_name)
            elif format.lower() == 'html':
                return self._format_html(filtered_contacts, award_name, include_summary)
            else:  # default to text
                return self._format_text(filtered_contacts, award_name, include_summary)

        except Exception as e:
            logger.error(f"Error generating report for {award_name}: {e}", exc_info=True)
            return f"Error generating report: {str(e)}"
        finally:
            session.close()

    def generate_tribune_report(
        self,
        format: str = 'text',
        include_summary: bool = True,
        achievement_date: Optional[str] = None
    ) -> str:
        """
        Generate Tribune award report

        Args:
            format: Report format ('text', 'csv', 'html', 'tsv')
            include_summary: Include summary statistics
            achievement_date: Date Tribune was achieved (YYYYMMDD format)

        Returns:
            Formatted report string
        """
        # Get all Tribune-eligible contacts
        session = self.db.get_session()
        try:
            contacts = self._get_tribune_contacts(session)

            # Filter to contacts AFTER achievement date if provided
            if achievement_date:
                filtered_contacts = [
                    c for c in contacts
                    if c.qso_date is not None and str(c.qso_date) >= str(achievement_date)
                ]
            else:
                filtered_contacts = contacts

            # Format based on requested format
            if format.lower() == 'csv':
                return self._format_csv(filtered_contacts, 'Tribune')
            elif format.lower() == 'tsv':
                return self._format_tsv(filtered_contacts, 'Tribune')
            elif format.lower() == 'html':
                return self._format_html(filtered_contacts, 'Tribune', include_summary)
            else:  # default to text
                return self._format_text(filtered_contacts, 'Tribune', include_summary)

        finally:
            session.close()

    def generate_centurion_report(
        self,
        format: str = 'text',
        include_summary: bool = True
    ) -> str:
        """
        Generate Centurion award report

        Args:
            format: Report format ('text', 'csv', 'html', 'tsv')
            include_summary: Include summary statistics

        Returns:
            Formatted report string
        """
        session = self.db.get_session()
        try:
            contacts = self._get_centurion_contacts(session)

            if format.lower() == 'csv':
                return self._format_csv(contacts, 'Centurion')
            elif format.lower() == 'tsv':
                return self._format_tsv(contacts, 'Centurion')
            elif format.lower() == 'html':
                return self._format_html(contacts, 'Centurion', include_summary)
            else:
                return self._format_text(contacts, 'Centurion', include_summary)

        finally:
            session.close()

    def generate_senator_report(
        self,
        format: str = 'text',
        include_summary: bool = True,
        achievement_date: Optional[str] = None
    ) -> str:
        """
        Generate Senator award report

        Args:
            format: Report format ('text', 'csv', 'html', 'tsv')
            include_summary: Include summary statistics
            achievement_date: Date Senator was achieved (YYYYMMDD format)

        Returns:
            Formatted report string
        """
        session = self.db.get_session()
        try:
            contacts = self._get_senator_contacts(session)

            if achievement_date:
                filtered_contacts = [
                    c for c in contacts
                    if c.qso_date is not None and str(c.qso_date) >= str(achievement_date)
                ]
            else:
                filtered_contacts = contacts

            if format.lower() == 'csv':
                return self._format_csv(filtered_contacts, 'Senator')
            elif format.lower() == 'tsv':
                return self._format_tsv(filtered_contacts, 'Senator')
            elif format.lower() == 'html':
                return self._format_html(filtered_contacts, 'Senator', include_summary)
            else:
                return self._format_text(filtered_contacts, 'Senator', include_summary)

        finally:
            session.close()

    def generate_generic_award_report(
        self,
        award_name: str,
        contacts: List[Contact],
        format: str = 'text',
        include_summary: bool = True
    ) -> str:
        """
        Generate report for any SKCC award

        Args:
            award_name: Name of award (e.g., 'Tribune', 'WAC', 'DXCC')
            contacts: List of Contact objects
            format: Report format ('text', 'csv', 'html', 'tsv')
            include_summary: Include summary statistics

        Returns:
            Formatted report string
        """
        if format.lower() == 'csv':
            return self._format_csv(contacts, award_name)
        elif format.lower() == 'tsv':
            return self._format_tsv(contacts, award_name)
        elif format.lower() == 'html':
            return self._format_html(contacts, award_name, include_summary)
        else:
            return self._format_text(contacts, award_name, include_summary)

    def _get_tribune_contacts(self, session: Session) -> List[Contact]:
        """Get all Tribune-eligible contacts"""
        from src.awards.tribune import TribuneAward

        tribune = TribuneAward(session)

        # Get all CW contacts with SKCC numbers
        contacts = session.query(Contact).filter(
            Contact.mode == 'CW',
            Contact.skcc_number.isnot(None)
        ).order_by(Contact.qso_date.asc()).all()

        # Filter to valid Tribune contacts
        valid_contacts = []
        for contact in contacts:
            if tribune.validate(self._contact_to_dict(contact)):
                valid_contacts.append(contact)

        return valid_contacts

    def _get_centurion_contacts(self, session: Session) -> List[Contact]:
        """Get all Centurion-eligible contacts"""
        from src.awards.centurion import CenturionAward

        centurion = CenturionAward(session)

        # Get all CW contacts with SKCC numbers
        contacts = session.query(Contact).filter(
            Contact.mode == 'CW',
            Contact.skcc_number.isnot(None)
        ).order_by(Contact.qso_date.asc()).all()

        # Filter to valid Centurion contacts
        valid_contacts = []
        for contact in contacts:
            if centurion.validate(self._contact_to_dict(contact)):
                valid_contacts.append(contact)

        return valid_contacts

    def _get_senator_contacts(self, session: Session) -> List[Contact]:
        """Get all Senator-eligible contacts"""
        from src.awards.senator import SenatorAward

        senator = SenatorAward(session)

        # Get all CW contacts with SKCC numbers
        contacts = session.query(Contact).filter(
            Contact.mode == 'CW',
            Contact.skcc_number.isnot(None)
        ).order_by(Contact.qso_date.asc()).all()

        # Filter to valid Senator contacts
        valid_contacts = []
        for contact in contacts:
            if senator.validate(self._contact_to_dict(contact)):
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
            'frequency': contact.frequency
        }

    def _format_text(
        self,
        contacts: List[Contact],
        award_name: str,
        include_summary: bool = True
    ) -> str:
        """Format report as plain text with sections"""
        lines: List[str] = []

        # Header
        lines.append("=" * 80)
        lines.append(f"SKCC {award_name} AWARD APPLICATION REPORT")
        lines.append("=" * 80)
        lines.append("")

        # Operator Information
        lines.append("OPERATOR INFORMATION")
        lines.append("-" * 80)
        lines.append(f"Call Sign: {self.my_callsign}")
        lines.append(f"SKCC Number: {self.my_skcc}")
        lines.append(f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        lines.append("")

        # Summary
        if include_summary:
            unique_calls = len(set(c.callsign for c in contacts))
            unique_skcc = len(set(c.skcc_number for c in contacts if c.skcc_number is not None))
            date_range = self._get_date_range(contacts)

            lines.append("SUMMARY")
            lines.append("-" * 80)
            lines.append(f"Total QSOs: {len(contacts)}")
            lines.append(f"Unique Call Signs: {unique_calls}")
            lines.append(f"Unique SKCC Members: {unique_skcc}")
            if date_range:
                lines.append(f"Date Range: {date_range[0]} to {date_range[1]}")
            lines.append("")

        # Contact List Header
        lines.append("CONTACT LIST")
        lines.append("-" * 80)
        lines.append(self._format_table_header())

        # Contact List
        for i, contact in enumerate(contacts, 1):
            lines.append(self._format_contact_row(contact, i))

        lines.append("-" * 80)
        lines.append(f"Total Contacts: {len(contacts)}")
        lines.append("=" * 80)

        return "\n".join(lines)

    def _format_csv(self, contacts: List[Contact], award_name: str) -> str:
        """Format report as CSV"""
        output_lines: List[str] = []

        # Header row
        output_lines.append(','.join(self.REPORT_COLUMNS))

        # Data rows
        for contact in contacts:
            row: List[str] = [
                str(contact.qso_date) if contact.qso_date is not None else '',
                str(contact.callsign) if contact.callsign is not None else '',
                str(contact.skcc_number) if contact.skcc_number is not None else '',
                str(contact.band) if contact.band is not None else '',
                str(contact.mode) if contact.mode is not None else '',
                str(contact.time_on) if contact.time_on is not None else '',
                str(contact.rst_sent) if contact.rst_sent is not None else '',
                str(contact.rst_rcvd) if contact.rst_rcvd is not None else '',
                (str(contact.notes) if contact.notes is not None else '').replace(',', ';')  # Escape commas in notes
            ]
            output_lines.append(','.join(f'"{field}"' for field in row))

        return "\n".join(output_lines)

    def _format_tsv(self, contacts: List[Contact], award_name: str) -> str:
        """Format report as Tab-Separated Values"""
        output_lines: List[str] = []

        # Header row
        output_lines.append('\t'.join(self.REPORT_COLUMNS))

        # Data rows
        for contact in contacts:
            row: List[str] = [
                str(contact.qso_date) if contact.qso_date is not None else '',
                str(contact.callsign) if contact.callsign is not None else '',
                str(contact.skcc_number) if contact.skcc_number is not None else '',
                str(contact.band) if contact.band is not None else '',
                str(contact.mode) if contact.mode is not None else '',
                str(contact.time_on) if contact.time_on is not None else '',
                str(contact.rst_sent) if contact.rst_sent is not None else '',
                str(contact.rst_rcvd) if contact.rst_rcvd is not None else '',
                (str(contact.notes) if contact.notes is not None else '').replace('\t', ' ')  # Replace tabs with spaces
            ]
            output_lines.append('\t'.join(row))

        return "\n".join(output_lines)

    def _format_html(
        self,
        contacts: List[Contact],
        award_name: str,
        include_summary: bool = True
    ) -> str:
        """Format report as HTML"""
        lines: List[str] = []

        lines.append("<!DOCTYPE html>")
        lines.append("<html>")
        lines.append("<head>")
        lines.append(f"<title>SKCC {award_name} Award Report - {self.my_callsign}</title>")
        lines.append("<style>")
        lines.append("""
            body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
            .header { background-color: #1E88E5; color: white; padding: 20px; border-radius: 5px; }
            .header h1 { margin: 0; }
            .operator-info { background-color: white; padding: 15px; margin: 20px 0; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .operator-info p { margin: 5px 0; }
            .summary { background-color: white; padding: 15px; margin: 20px 0; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .summary p { margin: 5px 0; }
            table { width: 100%; border-collapse: collapse; background-color: white; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            th { background-color: #1E88E5; color: white; padding: 10px; text-align: left; }
            td { padding: 8px; border-bottom: 1px solid #ddd; }
            tr:hover { background-color: #f5f5f5; }
            .footer { text-align: center; margin-top: 20px; color: #666; font-size: 12px; }
        """)
        lines.append("</style>")
        lines.append("</head>")
        lines.append("<body>")

        # Header
        lines.append("<div class='header'>")
        lines.append(f"<h1>SKCC {award_name} Award Application Report</h1>")
        lines.append("</div>")

        # Operator Information
        lines.append("<div class='operator-info'>")
        lines.append("<h2>Operator Information</h2>")
        lines.append(f"<p><strong>Call Sign:</strong> {self.my_callsign}</p>")
        lines.append(f"<p><strong>SKCC Number:</strong> {self.my_skcc}</p>")
        lines.append(f"<p><strong>Report Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>")
        lines.append("</div>")

        # Summary
        if include_summary:
            unique_calls = len(set(c.callsign for c in contacts))
            unique_skcc = len(set(c.skcc_number for c in contacts if c.skcc_number is not None))
            date_range = self._get_date_range(contacts)

            lines.append("<div class='summary'>")
            lines.append("<h2>Summary</h2>")
            lines.append(f"<p><strong>Total QSOs:</strong> {len(contacts)}</p>")
            lines.append(f"<p><strong>Unique Call Signs:</strong> {unique_calls}</p>")
            lines.append(f"<p><strong>Unique SKCC Members:</strong> {unique_skcc}</p>")
            if date_range:
                lines.append(f"<p><strong>Date Range:</strong> {date_range[0]} to {date_range[1]}</p>")
            lines.append("</div>")

        # Contact List
        lines.append("<h2>Contact List</h2>")
        lines.append("<table>")
        lines.append("<thead>")
        lines.append("<tr>")
        for col in self.REPORT_COLUMNS:
            lines.append(f"<th>{col}</th>")
        lines.append("</tr>")
        lines.append("</thead>")
        lines.append("<tbody>")

        for contact in contacts:
            lines.append("<tr>")
            lines.append(f"<td>{contact.qso_date or ''}</td>")
            lines.append(f"<td>{contact.callsign or ''}</td>")
            lines.append(f"<td>{contact.skcc_number or ''}</td>")
            lines.append(f"<td>{contact.band or ''}</td>")
            lines.append(f"<td>{contact.mode or ''}</td>")
            lines.append(f"<td>{contact.time_on or ''}</td>")
            lines.append(f"<td>{contact.rst_sent or ''}</td>")
            lines.append(f"<td>{contact.rst_rcvd or ''}</td>")
            lines.append(f"<td>{contact.notes or ''}</td>")
            lines.append("</tr>")

        lines.append("</tbody>")
        lines.append("</table>")

        lines.append("<div class='footer'>")
        lines.append(f"<p>Generated by W4GNS Logger on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>")
        lines.append("</div>")

        lines.append("</body>")
        lines.append("</html>")

        return "\n".join(lines)

    def _format_table_header(self) -> str:
        """Format table header row"""
        # Use fixed widths for readability
        widths = [10, 10, 15, 8, 6, 8, 6, 6, 30]
        row_parts: List[str] = []
        for col, width in zip(self.REPORT_COLUMNS, widths):
            row_parts.append(col.ljust(width))
        return "".join(row_parts)

    def _format_contact_row(self, contact: Contact, row_num: int) -> str:
        """Format contact data row"""
        widths = [10, 10, 15, 8, 6, 8, 6, 6, 30]
        values: List[str] = [
            str(contact.qso_date) if contact.qso_date is not None else '',
            str(contact.callsign) if contact.callsign is not None else '',
            str(contact.skcc_number) if contact.skcc_number is not None else '',
            str(contact.band) if contact.band is not None else '',
            str(contact.mode) if contact.mode is not None else '',
            str(contact.time_on) if contact.time_on is not None else '',
            str(contact.rst_sent) if contact.rst_sent is not None else '',
            str(contact.rst_rcvd) if contact.rst_rcvd is not None else '',
            (contact.notes or '')[:30]  # Truncate notes
        ]
        row_parts = []
        for val, width in zip(values, widths):
            row_parts.append(str(val).ljust(width))
        return "".join(row_parts)

    def _get_date_range(self, contacts: List[Contact]) -> Optional[Tuple[str, str]]:
        """Get min and max dates from contacts"""
        if not contacts:
            return None
        dates = [str(c.qso_date) for c in contacts if c.qso_date is not None]
        if not dates:
            return None
        return (min(dates), max(dates))

    def export_report_to_file(
        self,
        report_text: str,
        file_path: str,
        format: str = 'text'
    ) -> bool:
        """
        Export report to file

        Args:
            report_text: Formatted report text
            file_path: Path to save file
            format: File format extension

        Returns:
            True if successful, False otherwise
        """
        try:
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)

            with open(path, 'w', encoding='utf-8') as f:
                f.write(report_text)

            logger.info(f"Report exported to {file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to export report to {file_path}: {e}")
            return False
