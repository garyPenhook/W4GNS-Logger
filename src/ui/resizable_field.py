"""
Simple Form Field Widget

Basic widget that displays a label and field side by side.
"""

import logging
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel

logger = logging.getLogger(__name__)


class ResizableFieldRow(QWidget):
    """A simple label-field row"""

    def __init__(self, label_text: str, field_widget: QWidget, parent=None):
        """
        Initialize field row

        Args:
            label_text: Text for the label
            field_widget: The input widget (QLineEdit, QComboBox, etc.)
            parent: Parent widget

        Raises:
            TypeError: If label_text is not a string or field_widget is not a QWidget
            ValueError: If label_text is empty
        """
        try:
            # Validate inputs
            if not isinstance(label_text, str):
                raise TypeError(f"label_text must be str, got {type(label_text).__name__}")
            if not label_text.strip():
                raise ValueError("label_text cannot be empty")
            if not isinstance(field_widget, QWidget):
                raise TypeError(f"field_widget must be QWidget, got {type(field_widget).__name__}")

            super().__init__(parent)
            self.label_text = label_text
            self.field_widget = field_widget
            self.label = None  # Will be set in _init_ui

            self._init_ui()
            logger.debug(f"ResizableFieldRow created: '{label_text}'")

        except (TypeError, ValueError) as e:
            logger.error(f"Error initializing ResizableFieldRow: {e}")
            raise

    def _init_ui(self) -> None:
        """Initialize UI with simple horizontal layout"""
        try:
            layout = QHBoxLayout()
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(5)

            # Label widget
            self.label = QLabel(self.label_text)
            if self.label is None:
                raise RuntimeError("Failed to create QLabel")
            self.label.setMinimumWidth(80)  # Minimum label width
            self.label.setMaximumWidth(150)  # Maximum label width
            layout.addWidget(self.label)

            # Field widget
            if self.field_widget is None:
                raise RuntimeError("field_widget is None")
            layout.addWidget(self.field_widget)

            # Add stretch to push everything to the left
            layout.addStretch()

            self.setLayout(layout)
            logger.debug("ResizableFieldRow UI initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing ResizableFieldRow UI: {e}", exc_info=True)
            raise

    def set_label_width(self, width: int) -> None:
        """
        Set label width

        Args:
            width: Width in pixels (50-150px range)

        Raises:
            TypeError: If width is not an integer
        """
        try:
            if not isinstance(width, int):
                raise TypeError(f"width must be int, got {type(width).__name__}")

            if self.label is None:
                raise RuntimeError("label is not initialized")

            # Enforce min/max width
            width = max(50, min(150, width))

            self.label.setMinimumWidth(width)
            self.label.setMaximumWidth(width)
            logger.debug(f"Label width set to {width}px")

        except Exception as e:
            logger.error(f"Error setting label width: {e}", exc_info=True)
            raise

    def get_label_width(self) -> int:
        """
        Get current label width

        Returns:
            Width in pixels
        """
        try:
            if self.label is None:
                raise RuntimeError("label is not initialized")
            return self.label.width()
        except Exception as e:
            logger.error(f"Error getting label width: {e}", exc_info=True)
            raise
