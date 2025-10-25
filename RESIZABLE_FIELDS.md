# Resizable Fields Feature

## Overview

The logging form now includes user-movable, resizable label-field pairs. Users can drag the divider between labels and fields to customize the layout width.

## How to Use

1. **Locate the divider**: Between each label and field, there's a gray vertical bar (8px wide)
2. **Hover over divider**: Your cursor will automatically change to a resize cursor (↔️)
3. **Click and drag**: Click and hold the divider, then drag it left or right
   - Drag **LEFT** to make labels narrower and move fields left (closer to labels)
   - Drag **RIGHT** to make labels wider and move fields right

The divider features:
- Visible gray background (easier to see and grab than a thin line)
- 8px width for easier mouse targeting
- Resize cursor feedback
- Smooth dragging with live updates

## Technical Details

### DraggableDivider Widget
Located in: `src/ui/resizable_field.py`

A custom QWidget divider with:
- **8px width** for easy mouse targeting
- **Visual feedback**: Gray background with vertical lines
- **Cursor feedback**: Split cursor appears on hover
- **Event handling**: Proper mouse press/move/release events
- **Exception handling**: All events protected with try-catch and logging

### ResizableFieldRow Widget
Located in: `src/ui/resizable_field.py`

Features:
- Custom QWidget that wraps a label, DraggableDivider, and field widget
- Layout: `[Label | DraggableDivider | Field] [Stretch]`
- Minimum label width: 50px (prevents making too narrow)
- Smooth dragging with cursor feedback
- All mouse events routed through DraggableDivider callbacks

### Integration
All form sections now use ResizableFieldRow:
- Basic QSO Information (Callsign, Date & Time, Band, Mode)
- Frequency section (with Auto Fill button)
- Location section (Country, State, Grid Square, QTH)
- Signal Reports section (RST Sent/Received, TX Power, Operator Name)

### Example Usage
```python
from src.ui.resizable_field import ResizableFieldRow
from PyQt6.QtWidgets import QLineEdit

field = QLineEdit()
field.setPlaceholderText("Enter value")

# Create resizable row
row = ResizableFieldRow("Label:", field)
layout.addWidget(row)

# Get/set label width programmatically
current_width = row.get_label_width()
row.set_label_width(120)
```

## Future Enhancements

Potential improvements:
- Save user's column widths to config file
- Add double-click to auto-fit label width to text
- Synchronized resizing across multiple field groups
- Keyboard shortcuts for quick adjustments

## Troubleshooting

**Divider not responding to clicks?**
- Ensure you're clicking directly on the thin vertical line
- Try moving your cursor slightly to find the exact divider position

**Fields moved too far left?**
- Minimum label width is 50px, so fields can't go further left
- Try dragging right to expand the label area

**Divider hard to see?**
- The divider is a thin line (4px wide) between label and field
- Look for the cursor change to find it more easily
