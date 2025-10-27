"""
Theme Manager for W4GNS SKCC Logger

Handles light and dark theme application to the entire application.
Provides functions to switch themes and apply stored theme on startup.
"""

import logging
from typing import Optional
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QApplication

logger = logging.getLogger(__name__)


class ThemeManager:
    """Manages application themes (light and dark)"""

    # Light theme colors
    LIGHT_PALETTE = {
        'window': '#ffffff',
        'base': '#ffffff',
        'alternate_base': '#f0f0f0',
        'text': '#000000',
        'button_text': '#000000',
        'button': '#f0f0f0',
        'highlight': '#0078d4',
        'highlight_text': '#ffffff',
        'link': '#0078d4',
        'link_visited': '#804080',
        'light': '#ffffff',
        'midlight': '#f5f5f5',
        'dark': '#808080',
        'mid': '#c0c0c0',
        'shadow': '#808080',
        'tool_tip_base': '#fffacd',
        'tool_tip_text': '#000000',
        'menu_bar': '#f0f0f0',
        'menu': '#f0f0f0',
    }

    # Dark theme colors
    DARK_PALETTE = {
        'window': '#1e1e1e',
        'base': '#2d2d2d',
        'alternate_base': '#3d3d3d',
        'text': '#e0e0e0',
        'button_text': '#e0e0e0',
        'button': '#3d3d3d',
        'highlight': '#0078d4',
        'highlight_text': '#ffffff',
        'link': '#0078d4',
        'link_visited': '#9370db',
        'light': '#3d3d3d',
        'midlight': '#2d2d2d',
        'dark': '#1e1e1e',
        'mid': '#3d3d3d',
        'shadow': '#000000',
        'tool_tip_base': '#2d2d2d',
        'tool_tip_text': '#e0e0e0',
        'menu_bar': '#2d2d2d',
        'menu': '#2d2d2d',
    }

    # Light theme stylesheet
    LIGHT_STYLESHEET = """
        QMainWindow, QWidget {
            background-color: #ffffff;
            color: #000000;
        }
        QMenuBar {
            background-color: #f0f0f0;
            color: #000000;
            border-bottom: 1px solid #cccccc;
        }
        QMenuBar::item:selected {
            background-color: #e0e0e0;
        }
        QMenu {
            background-color: #f0f0f0;
            color: #000000;
            border: 1px solid #cccccc;
        }
        QMenu::item:selected {
            background-color: #0078d4;
            color: #ffffff;
        }
        QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox {
            background-color: #ffffff;
            color: #000000;
            border: 1px solid #cccccc;
            border-radius: 3px;
            padding: 2px;
        }
        QComboBox:hover, QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover {
            border: 1px solid #0078d4;
        }
        QComboBox::drop-down {
            border-left: 1px solid #cccccc;
        }
        QPushButton {
            background-color: #f0f0f0;
            color: #000000;
            border: 1px solid #cccccc;
            border-radius: 3px;
            padding: 4px 12px;
        }
        QPushButton:hover {
            background-color: #e0e0e0;
            border: 1px solid #0078d4;
        }
        QPushButton:pressed {
            background-color: #d0d0d0;
        }
        QGroupBox {
            color: #000000;
            border: 1px solid #cccccc;
            border-radius: 5px;
            margin-top: 10px;
            padding-top: 10px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 3px 0 3px;
        }
        QTabBar::tab {
            background-color: #e0e0e0;
            color: #000000;
            padding: 5px 15px;
            border: 1px solid #cccccc;
            border-bottom: none;
        }
        QTabBar::tab:selected {
            background-color: #ffffff;
            color: #000000;
            border-bottom: 2px solid #0078d4;
        }
        QTabWidget::pane {
            border: 1px solid #cccccc;
        }
        QTableWidget {
            background-color: #ffffff;
            color: #000000;
            gridline-color: #cccccc;
        }
        QHeaderView::section {
            background-color: #f0f0f0;
            color: #000000;
            padding: 5px;
            border: 1px solid #cccccc;
        }
        QTableWidget::item:selected {
            background-color: #0078d4;
            color: #ffffff;
        }
        QScrollBar:vertical {
            background-color: #f5f5f5;
            width: 12px;
            border: 1px solid #cccccc;
        }
        QScrollBar::handle:vertical {
            background-color: #cccccc;
            border-radius: 6px;
            min-height: 20px;
        }
        QScrollBar::handle:vertical:hover {
            background-color: #999999;
        }
    """

    # Dark theme stylesheet
    DARK_STYLESHEET = """
        QMainWindow, QWidget {
            background-color: #1e1e1e;
            color: #e0e0e0;
        }
        QMenuBar {
            background-color: #2d2d2d;
            color: #e0e0e0;
            border-bottom: 1px solid #404040;
        }
        QMenuBar::item:selected {
            background-color: #404040;
        }
        QMenu {
            background-color: #2d2d2d;
            color: #e0e0e0;
            border: 1px solid #404040;
        }
        QMenu::item:selected {
            background-color: #0078d4;
            color: #ffffff;
        }
        QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox {
            background-color: #3d3d3d;
            color: #e0e0e0;
            border: 1px solid #404040;
            border-radius: 3px;
            padding: 2px;
        }
        QComboBox:hover, QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover {
            border: 1px solid #0078d4;
        }
        QComboBox::drop-down {
            border-left: 1px solid #404040;
        }
        QPushButton {
            background-color: #3d3d3d;
            color: #e0e0e0;
            border: 1px solid #404040;
            border-radius: 3px;
            padding: 4px 12px;
        }
        QPushButton:hover {
            background-color: #4d4d4d;
            border: 1px solid #0078d4;
        }
        QPushButton:pressed {
            background-color: #5d5d5d;
        }
        QGroupBox {
            color: #e0e0e0;
            border: 1px solid #404040;
            border-radius: 5px;
            margin-top: 10px;
            padding-top: 10px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 3px 0 3px;
        }
        QTabBar::tab {
            background-color: #404040;
            color: #e0e0e0;
            padding: 5px 15px;
            border: 1px solid #5d5d5d;
            border-bottom: none;
        }
        QTabBar::tab:selected {
            background-color: #2d2d2d;
            color: #e0e0e0;
            border-bottom: 2px solid #0078d4;
        }
        QTabWidget::pane {
            border: 1px solid #404040;
        }
        QTableWidget {
            background-color: #2d2d2d;
            color: #e0e0e0;
            gridline-color: #404040;
        }
        QHeaderView::section {
            background-color: #3d3d3d;
            color: #e0e0e0;
            padding: 5px;
            border: 1px solid #404040;
        }
        QTableWidget::item:selected {
            background-color: #0078d4;
            color: #ffffff;
        }
        QScrollBar:vertical {
            background-color: #2d2d2d;
            width: 12px;
            border: 1px solid #404040;
        }
        QScrollBar::handle:vertical {
            background-color: #5d5d5d;
            border-radius: 6px;
            min-height: 20px;
        }
        QScrollBar::handle:vertical:hover {
            background-color: #7d7d7d;
        }
    """

    @staticmethod
    def apply_theme(app: QApplication, theme: str = "light") -> bool:
        """
        Apply a theme to the application

        Args:
            app: QApplication instance
            theme: Theme name ('light' or 'dark')

        Returns:
            True if successful, False otherwise
        """
        try:
            if theme.lower() == "dark":
                app.setStyle("Fusion")
                palette = QPalette()
                palette.setColor(QPalette.ColorRole.Window, QColor(ThemeManager.DARK_PALETTE['window']))
                palette.setColor(QPalette.ColorRole.WindowText, QColor(ThemeManager.DARK_PALETTE['text']))
                palette.setColor(QPalette.ColorRole.Base, QColor(ThemeManager.DARK_PALETTE['base']))
                palette.setColor(QPalette.ColorRole.AlternateBase, QColor(ThemeManager.DARK_PALETTE['alternate_base']))
                palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(ThemeManager.DARK_PALETTE['tool_tip_base']))
                palette.setColor(QPalette.ColorRole.ToolTipText, QColor(ThemeManager.DARK_PALETTE['tool_tip_text']))
                palette.setColor(QPalette.ColorRole.Text, QColor(ThemeManager.DARK_PALETTE['text']))
                palette.setColor(QPalette.ColorRole.Button, QColor(ThemeManager.DARK_PALETTE['button']))
                palette.setColor(QPalette.ColorRole.ButtonText, QColor(ThemeManager.DARK_PALETTE['button_text']))
                palette.setColor(QPalette.ColorRole.BrightText, QColor("#ffffff"))
                palette.setColor(QPalette.ColorRole.Link, QColor(ThemeManager.DARK_PALETTE['link']))
                palette.setColor(QPalette.ColorRole.Highlight, QColor(ThemeManager.DARK_PALETTE['highlight']))
                palette.setColor(QPalette.ColorRole.HighlightedText, QColor(ThemeManager.DARK_PALETTE['highlight_text']))
                app.setPalette(palette)
                app.setStyleSheet(ThemeManager.DARK_STYLESHEET)
                logger.info("Applied DARK theme")
                return True
            else:  # light theme
                app.setStyle("Fusion")
                palette = QPalette()
                palette.setColor(QPalette.ColorRole.Window, QColor(ThemeManager.LIGHT_PALETTE['window']))
                palette.setColor(QPalette.ColorRole.WindowText, QColor(ThemeManager.LIGHT_PALETTE['text']))
                palette.setColor(QPalette.ColorRole.Base, QColor(ThemeManager.LIGHT_PALETTE['base']))
                palette.setColor(QPalette.ColorRole.AlternateBase, QColor(ThemeManager.LIGHT_PALETTE['alternate_base']))
                palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(ThemeManager.LIGHT_PALETTE['tool_tip_base']))
                palette.setColor(QPalette.ColorRole.ToolTipText, QColor(ThemeManager.LIGHT_PALETTE['tool_tip_text']))
                palette.setColor(QPalette.ColorRole.Text, QColor(ThemeManager.LIGHT_PALETTE['text']))
                palette.setColor(QPalette.ColorRole.Button, QColor(ThemeManager.LIGHT_PALETTE['button']))
                palette.setColor(QPalette.ColorRole.ButtonText, QColor(ThemeManager.LIGHT_PALETTE['button_text']))
                palette.setColor(QPalette.ColorRole.BrightText, QColor("#ffffff"))
                palette.setColor(QPalette.ColorRole.Link, QColor(ThemeManager.LIGHT_PALETTE['link']))
                palette.setColor(QPalette.ColorRole.Highlight, QColor(ThemeManager.LIGHT_PALETTE['highlight']))
                palette.setColor(QPalette.ColorRole.HighlightedText, QColor(ThemeManager.LIGHT_PALETTE['highlight_text']))
                app.setPalette(palette)
                app.setStyleSheet(ThemeManager.LIGHT_STYLESHEET)
                logger.info("Applied LIGHT theme")
                return True

        except Exception as e:
            logger.error(f"Error applying theme '{theme}': {e}", exc_info=True)
            return False
