# Exception Handling Implementation

## Overview
Comprehensive exception handling has been added to the logging form and resizable field widget to ensure robust error handling, logging, and user feedback.

## Files Updated

### 1. `src/ui/resizable_field.py`
**ResizableFieldRow Widget Exception Handling**

#### Constructor (`__init__`)
- **Validates input parameters:**
  - `label_text` must be a non-empty string
  - `field_widget` must be a QWidget instance
- **Raises:**
  - `TypeError` if invalid types provided
  - `ValueError` if label_text is empty
- **Logs:** `debug` on successful creation, `error` on failure

#### UI Initialization (`_init_ui`)
- **Try-catch wrapper** around entire UI setup
- **Validates widget creation** (checks for None after creation)
- **Logs:** `debug` on success, `error` with traceback on failure
- **Re-raises exceptions** to prevent silent failures

#### Mouse Event Handlers
- **`_on_divider_press()`:**
  - Handles None events gracefully
  - Validates `globalPosition()` result
  - Converts float coordinates to int (fixes type error)
  - Logs drag start position at debug level

- **`_on_divider_move()`:**
  - Guards against None events and dragging state
  - Validates label widget exists
  - Validates calculated width (minimum 50px)
  - Catches all exceptions and logs with traceback
  - Sets `is_dragging = False` on error to prevent stuck state

- **`_on_divider_release()`:**
  - Logs final label width on successful release
  - Catches any exceptions during cleanup

#### Public Methods
- **`set_label_width(width: int)`:**
  - Validates width is integer type
  - Checks label widget initialized
  - Logs successful width changes
  - Re-raises exceptions to caller

- **`get_label_width() -> int`:**
  - Validates label widget initialized
  - Returns current width
  - Logs errors with traceback

### 2. `src/ui/logging_form.py`
**LoggingForm Exception Handling**

#### Constructor (`__init__`)
- **Validates database instance:**
  - Checks for None
  - Checks isinstance(db, DatabaseRepository)
- **Logs:** `info` on success, `error` on failure
- **Re-raises exceptions** to prevent app startup with invalid database

#### UI Initialization (`_init_ui`)
- **Nested try-catch blocks** for each section creation:
  - Basic section
  - Frequency section
  - Location section
  - Signal section
  - Buttons section
- **Logs debug message** on each section creation
- **Detailed error logging** with section name and traceback
- **Rolls up** exceptions to parent handler

#### Save Contact (`save_contact`)
- **Comprehensive multi-stage error handling:**

1. **Form Validation Stage**
   - Logs debug when validation fails
   - Returns early if validation fails

2. **DateTime Parsing Stage**
   - Checks for None datetime value
   - Validates `toPython()` conversion
   - Logs parsed values at debug level
   - Raises ValueError with context on error

3. **Contact Creation Stage**
   - Validates callsign not empty after strip
   - Logs created contact callsign at debug
   - Raises ValueError on creation error

4. **Database Save Stage**
   - Validates database connection exists
   - Logs success at info level
   - Raises RuntimeError on database error

5. **User Feedback Stage**
   - Shows success message box on success
   - Catches outer exception and shows error dialog
   - Logs all errors with traceback

#### Clear Form (`clear_form`)
- **Try-catch wrapper** around all field clearing
- **Logs debug** on successful clear
- **Logs error with traceback** on failure
- **Re-raises exceptions** to caller

#### Set Field Width (`set_field_width`)
- **Input Validation:**
  - Checks field_name is non-empty string
  - Checks width is integer
  - Validates field_name is in known fields dict

- **Field Update Stage:**
  - Try-catch around all setMaximumWidth calls
  - Logs debug on successful update
  - Re-raises exceptions

- **Comprehensive Error Handling:**
  - Outer catch for TypeError and ValueError
  - All errors logged with traceback
  - Re-raised to caller

## Error Handling Patterns Used

### 1. Input Validation
```python
if not isinstance(value, ExpectedType):
    raise TypeError(f"Expected {ExpectedType}, got {type(value).__name__}")
if not value.strip():
    raise ValueError("Value cannot be empty")
```

### 2. Null/None Checks
```python
if widget is None:
    raise RuntimeError("Widget is not initialized")
```

### 3. Try-Catch with Logging
```python
try:
    operation()
    logger.debug("Operation succeeded")
except Exception as e:
    logger.error(f"Operation failed: {e}", exc_info=True)
    raise  # Re-raise unless handling is complete
```

### 4. Nested Try-Catch for Multi-Stage Operations
```python
try:
    try:
        stage_1()
    except Exception as e:
        logger.error(f"Stage 1 failed: {e}")
        raise

    try:
        stage_2()
    except Exception as e:
        logger.error(f"Stage 2 failed: {e}")
        raise

except Exception as e:
    logger.error(f"Overall operation failed: {e}")
    show_user_error()
```

## Logging Levels Used

- **DEBUG:** Successful operations, state changes, parameter values
- **INFO:** Important completed operations (contact saved)
- **ERROR:** Failures, invalid inputs, exceptions (all with traceback)

## User Feedback

- **Success Messages:** QMessageBox.information() for successful saves
- **Error Messages:** QMessageBox.critical() with error details
- **Never Silent Fails:** All errors are logged and either shown or re-raised

## Testing Exception Handling

Test scenarios:
```python
# Test invalid label_text
row = ResizableFieldRow(123, field_widget)  # TypeError

# Test invalid field_widget
row = ResizableFieldRow("Label", "not_a_widget")  # TypeError

# Test invalid field_name in set_field_width
form.set_field_width("invalid_field", 100)  # ValueError

# Test invalid width type
form.set_field_width("callsign", "not_int")  # TypeError

# Test None database
form = LoggingForm(None)  # TypeError
```

## Benefits

1. **Robustness:** Application handles edge cases gracefully
2. **Debuggability:** Comprehensive logging with tracebacks
3. **User Experience:** Clear error messages for user actions
4. **Type Safety:** Early detection of invalid parameters
5. **State Consistency:** Error handlers prevent stuck state (e.g., is_dragging flag)
6. **Maintainability:** Clear intent through explicit validation and error handling
