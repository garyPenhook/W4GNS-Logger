"""
Power Statistics Dashboard Widget

Displays comprehensive power statistics and distribution across all contacts.
"""

import logging
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QTableWidget,
    QTableWidgetItem
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor

from src.database.repository import DatabaseRepository
from src.ui.signals import get_app_signals

logger = logging.getLogger(__name__)


class PowerStatsWidget(QWidget):
    """Displays comprehensive power statistics"""

    def __init__(self, db: DatabaseRepository, parent: Optional[QWidget] = None):
        """
        Initialize power statistics widget

        Args:
            db: Database repository instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.db = db

        # Visibility-aware refresh state
        self._needs_refresh = False
        self._has_initial_data = False

        self._init_ui()
        # Defer initial refresh to avoid blocking GUI initialization
        QTimer.singleShot(300, self._initial_refresh)

        # Connect to signals - but refresh intelligently based on visibility
        signals = get_app_signals()
        signals.contacts_changed.connect(self._on_data_changed)
        signals.contact_added.connect(self._on_data_changed)
        signals.contact_modified.connect(self._on_data_changed)
        signals.contact_deleted.connect(self._on_data_changed)

    def _initial_refresh(self) -> None:
        """Initial refresh - only if widget is visible"""
        try:
            if self.isVisible():
                self.refresh()
            else:
                # Widget not visible yet, mark for refresh when shown
                self._needs_refresh = True
        except Exception as e:
            logger.error(f"Error in initial refresh: {e}", exc_info=True)

    def _init_ui(self) -> None:
        """Initialize UI components"""
        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)

        # Summary statistics section
        summary_group = self._create_summary_section()
        main_layout.addWidget(summary_group)

        # Power distribution section
        dist_group = self._create_distribution_section()
        main_layout.addWidget(dist_group)

        # Band breakdown section
        band_group = self._create_band_section()
        main_layout.addWidget(band_group)

        main_layout.addStretch()
        self.setLayout(main_layout)

    def _create_summary_section(self) -> QGroupBox:
        """Create summary statistics section"""
        group = QGroupBox("Overall Statistics")
        layout = QVBoxLayout()

        stats_layout = QHBoxLayout()

        # Total contacts with power
        total_layout = QVBoxLayout()
        total_label = QLabel("Total Contacts")
        total_label.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        self.total_label = QLabel("0")
        self.total_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        total_layout.addWidget(total_label)
        total_layout.addWidget(self.total_label)
        stats_layout.addLayout(total_layout)

        stats_layout.addSpacing(30)

        # Average power
        avg_layout = QVBoxLayout()
        avg_label = QLabel("Average Power")
        avg_label.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        self.avg_label = QLabel("0.0 W")
        self.avg_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        avg_label_units = QLabel("Watts")
        avg_label_units.setFont(QFont("Arial", 8))
        avg_layout.addWidget(avg_label)
        avg_layout.addWidget(self.avg_label)
        avg_layout.addWidget(avg_label_units)
        stats_layout.addLayout(avg_layout)

        stats_layout.addSpacing(30)

        # Min/Max range
        range_layout = QVBoxLayout()
        range_label = QLabel("Power Range")
        range_label.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        self.range_label = QLabel("0 - 0 W")
        self.range_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        range_layout.addWidget(range_label)
        range_layout.addWidget(self.range_label)
        stats_layout.addLayout(range_layout)

        stats_layout.addStretch()
        layout.addLayout(stats_layout)
        group.setLayout(layout)
        return group

    def _create_distribution_section(self) -> QGroupBox:
        """Create power distribution section"""
        group = QGroupBox("Power Category Distribution")
        layout = QVBoxLayout()

        # Create distribution table
        self.dist_table = QTableWidget()
        self.dist_table.setColumnCount(3)
        self.dist_table.setHorizontalHeaderLabels(["Category", "Count", "Percentage"])
        self.dist_table.setMaximumHeight(200)
        self.dist_table.setColumnWidth(0, 150)
        self.dist_table.setColumnWidth(1, 80)
        self.dist_table.setColumnWidth(2, 100)

        # Add rows for categories
        categories = [
            ("QRPp (<0.5W)", "Extreme QRP", QColor(255, 100, 0)),  # Orange
            ("QRP (0.5-5W)", "Standard QRP", QColor(76, 175, 80)),  # Green
            ("Standard (5-100W)", "Normal Power", QColor(33, 150, 243)),  # Blue
            ("QRO (>100W)", "High Power", QColor(244, 67, 54)),  # Red
        ]

        self.dist_table.setRowCount(len(categories))
        self.category_labels = {}

        for row, (category, description, color) in enumerate(categories):
            # Category name
            cat_item = QTableWidgetItem(category)
            cat_item.setToolTip(description)
            self.dist_table.setItem(row, 0, cat_item)

            # Count
            count_item = QTableWidgetItem("0")
            count_item.setForeground(color)
            count_item.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            self.dist_table.setItem(row, 1, count_item)
            self.category_labels[category] = (count_item, None)

            # Percentage
            pct_item = QTableWidgetItem("0%")
            pct_item.setForeground(color)
            self.dist_table.setItem(row, 2, pct_item)
            # Store the percentage item for later updates
            old_item, _ = self.category_labels[category]
            self.category_labels[category] = (old_item, pct_item)

        layout.addWidget(self.dist_table)
        group.setLayout(layout)
        return group

    def _create_band_section(self) -> QGroupBox:
        """Create band power breakdown section"""
        group = QGroupBox("Power Statistics by Band")
        layout = QVBoxLayout()

        # Create band table
        self.band_table = QTableWidget()
        self.band_table.setColumnCount(4)
        self.band_table.setHorizontalHeaderLabels([
            "Band", "Avg Power", "Contacts", "QRP Count"
        ])
        self.band_table.setMaximumHeight(250)

        layout.addWidget(self.band_table)
        group.setLayout(layout)
        return group

    def _on_data_changed(self) -> None:
        """Handle data change signal - refresh if visible, mark for refresh if hidden"""
        try:
            if self.isVisible():
                # Widget is visible, refresh immediately to show fresh data
                self.refresh()
            else:
                # Widget is hidden, just mark that refresh is needed
                self._needs_refresh = True
                logger.debug("PowerStatsWidget: Data changed while hidden, marked for refresh")
        except Exception as e:
            logger.error(f"Error handling data change: {e}", exc_info=True)

    def showEvent(self, event) -> None:
        """Handle widget becoming visible - refresh if needed"""
        try:
            super().showEvent(event)

            # If data changed while hidden, refresh now to show fresh data
            if self._needs_refresh:
                logger.info("PowerStatsWidget: Refreshing on show (data changed while hidden)")
                self.refresh()
                self._needs_refresh = False
            elif not self._has_initial_data:
                # First time showing, ensure we have data
                logger.info("PowerStatsWidget: Loading initial data on first show")
                self.refresh()
        except Exception as e:
            logger.error(f"Error in showEvent: {e}", exc_info=True)

    def refresh(self) -> None:
        """Refresh all power statistics displays"""
        try:
            self._has_initial_data = True
            # Get power statistics
            stats = self.db.get_power_statistics()

            # Update summary
            total = stats['total_with_power']
            self.total_label.setText(str(total))
            self.avg_label.setText(f"{stats['average_power']:.1f}")
            self.range_label.setText(f"{stats['min_power']:.1f} - {stats['max_power']:.1f} W")

            # Update distribution
            categories_data = [
                ("QRPp (<0.5W)", stats['qrpp_count']),
                ("QRP (0.5-5W)", stats['qrp_count']),
                ("Standard (5-100W)", stats['standard_count']),
                ("QRO (>100W)", stats['qro_count']),
            ]

            for row, (category, count) in enumerate(categories_data):
                count_item, pct_item = self.category_labels[category]

                # Update count
                count_item.setText(str(count))

                # Update percentage
                if total > 0:
                    pct = (count / total) * 100
                    if pct_item:
                        pct_item.setText(f"{pct:.1f}%")
                else:
                    if pct_item:
                        pct_item.setText("0%")

            # Get QRP contacts for band breakdown
            self._update_band_breakdown()

        except Exception as e:
            logger.error(f"Error refreshing power statistics: {e}", exc_info=True)

    def _update_band_breakdown(self) -> None:
        """Update band-by-band power breakdown"""
        try:
            qrp_contacts = self.db.get_qrp_contacts()
            all_contacts = self.db.get_all_contacts(limit=10000)

            # Group by band
            band_stats = {}
            for contact in all_contacts:
                if contact.band not in band_stats:
                    band_stats[contact.band] = {
                        'powers': [],
                        'total': 0,
                        'qrp': 0
                    }

                band_stats[contact.band]['total'] += 1

                if contact.tx_power is not None and contact.tx_power > 0:
                    band_stats[contact.band]['powers'].append(contact.tx_power)

                if contact.is_qrp_contact():
                    band_stats[contact.band]['qrp'] += 1

            # Sort by band name
            sorted_bands = sorted(band_stats.keys())

            # Populate table
            self.band_table.setRowCount(len(sorted_bands))

            for row, band in enumerate(sorted_bands):
                stats = band_stats[band]

                # Band name
                band_item = QTableWidgetItem(band)
                self.band_table.setItem(row, 0, band_item)

                # Average power
                avg_power = (
                    sum(stats['powers']) / len(stats['powers'])
                    if stats['powers'] else 0
                )
                avg_item = QTableWidgetItem(f"{avg_power:.1f} W")
                self.band_table.setItem(row, 1, avg_item)

                # Total contacts
                total_item = QTableWidgetItem(str(stats['total']))
                self.band_table.setItem(row, 2, total_item)

                # QRP count
                qrp_item = QTableWidgetItem(f"{stats['qrp']}/{stats['total']}")
                if stats['qrp'] > 0:
                    qrp_item.setForeground(QColor(76, 175, 80))  # Green
                    qrp_item.setFont(QFont("Arial", 9, QFont.Weight.Bold))
                self.band_table.setItem(row, 3, qrp_item)

            # Resize columns
            self.band_table.resizeColumnsToContents()

        except Exception as e:
            logger.error(f"Error updating band breakdown: {e}", exc_info=True)
