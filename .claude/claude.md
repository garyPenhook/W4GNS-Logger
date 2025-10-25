# W4GNS Ham Radio Logger - Project Context

## Project Overview

**W4GNS Ham Radio Logger** is a professional-grade contact logging application for ham radio operators. It provides comprehensive QSO (contact) management with ADIF 3.1.5 standard compliance, award tracking, DX cluster integration, and QRZ.com synchronization.

**Status**: Phase 1-2 complete (skeleton + core systems), actively developing GUI and business logic

## Key Technologies

- **Language**: Python 3.14.0
- **Package Manager**: UV (Rust-based, 100x faster than pip)
- **GUI Framework**: PyQt6 (cross-platform)
- **Database**: SQLite3 with SQLAlchemy ORM
- **Configuration**: YAML-based
- **ADIF Support**: Full 3.1.5 standard (99 fields)

## Architecture

### Directory Structure

```
src/
├── main.py                 # Application entry point
├── config/                 # Configuration management
│   └── settings.py        # ConfigManager for YAML files
├── database/              # Data persistence
│   ├── models.py          # SQLAlchemy ORM (Contact, Award, QSL, etc.)
│   └── repository.py      # Data access layer (Repository pattern)
├── adif/                  # ADIF file handling
│   └── parser.py          # Full ADIF 3.1.5 parser (99 fields, 57 modes, 29 bands)
├── awards/                # Award tracking system
│   ├── base.py            # Abstract AwardProgram class
│   ├── dxcc.py            # DXCC award implementation
│   └── registry.py        # (TODO) Award factory/registry
├── ui/                    # GUI components
│   ├── main_window.py     # PyQt6 main window scaffold
│   ├── field_manager.py   # Dynamic field display preferences
│   ├── tabs/              # (TODO) Tab implementations
│   └── dialogs/           # (TODO) Dialog windows
├── business_logic/        # Service layer (scaffolding)
├── utils/                 # Utilities
│   └── validators.py      # Data validation (callsigns, dates, modes, bands, RST, grids)
└── tests/                 # Unit tests (scaffolding)

config/
├── awards.yaml            # Award program definitions
├── clusters.yaml          # DX cluster node configuration
└── qrz.yaml               # QRZ.com API settings
```

### Design Patterns Used

1. **MVC Pattern**: Model (Contact ORM), View (PyQt6 GUI), Controller (Business logic services)
2. **Repository Pattern**: Abstract data access via DatabaseRepository
3. **Plugin Architecture**: Awards system with AwardProgram base class for extensibility
4. **Singleton Pattern**: ConfigManager, database connection pooling
5. **Factory Pattern**: Award creation and component instantiation
6. **Strategy Pattern**: ADIF parsers (ADI vs ADX), validators

## Current Implementation Status

### ✅ Completed

- **Python 3.14.0 setup** with UV package manager
- **Database schema** (Contact model with 80+ ADIF fields)
- **ADIF 3.1.5 parser** supporting ADI/ADX formats
  - 99 ADIF fields organized by category
  - 57 valid operating modes (CW, SSB, FT8, WSPR, etc.)
  - 29 valid bands (160m to 1mm)
  - Full validation for all required fields
- **Configuration system** with YAML support
- **Data validators** for callsigns, dates, times, RST, modes, bands, grids
- **Award system architecture** with DXCC implementation
- **UI Field Manager** for dynamic field display preferences
- **SQLAlchemy ORM models** with relationships and constraints
- **Repository pattern** data access layer
- **Documentation** (README, UV_GUIDE, ANSWER_TO_YOUR_QUESTION)

### 🚧 In Progress / TODO

**Phase 2 - GUI Development**
- [ ] Contact logging tab implementation
- [ ] Contacts list view with sorting/filtering
- [ ] Search functionality
- [ ] Contact editing dialogs
- [ ] Field display preferences dialog (checkboxes for extended fields)

**Phase 3 - Core Features**
- [ ] ADIF export (serializer)
- [ ] Award calculator engine (all awards)
- [ ] WAS, WAC, SKCC award plugins
- [ ] Award progress dashboard

**Phase 4 - Advanced Features**
- [ ] DX Cluster integration (Telnet client)
- [ ] QRZ.com integration (upload service)
- [ ] Import/export workflows
- [ ] Settings management
- [ ] Backup/restore functionality

**Phase 5 - Polish**
- [ ] Comprehensive testing
- [ ] Performance optimization
- [ ] User documentation
- [ ] Packaging

## Key Design Decisions

### Basic vs Extended Fields

**Basic Fields** (always visible):
- callsign, qso_date, time_on, band, mode

**Extended Fields** (user toggles via checkboxes):
- 75+ ADIF fields organized in categories: QSO Details, Location, Station, Awards, QSL, Technical, Notes
- FieldManager handles dynamic display preferences
- UIFieldPreference table tracks user selections

### Database Schema

**Contact Model**:
- 80+ columns covering all ADIF 3.1.5 fields
- Indexed on: callsign, qso_date, band, mode, country
- Unique constraint: (callsign, qso_date, time_on, band)
- Relationships to QSLRecord, Awards, etc.

**UIFieldPreference Table**:
- Tracks which fields to display in list view
- Tracks which fields to display in form view
- Allows custom column ordering
- Organizes fields by category

### ADIF Parser Strategy

- **Supports both ADI (text) and ADX (XML)** formats
- **99 fields** covering all ADIF 3.1.5 categories
- **57 valid modes** including all digital modes
- **29 valid bands** from 2190m to 1mm
- **Comprehensive validation** for required and optional fields
- **Extensible design** to accept custom fields gracefully

## Important Files to Know

### Configuration Files

- `config/awards.yaml` - Defines enabled awards and their rules
- `config/clusters.yaml` - DX cluster node list and settings
- `config/qrz.yaml` - QRZ.com API configuration
- `pyproject.toml` - Modern Python project config (PEP 517/518)
- `uv.lock` - Reproducible dependency lock file

### Core Modules

- `src/config/settings.py` - Configuration management (load/save YAML)
- `src/database/models.py` - ORM models (Contact, Award, QSL, etc.)
- `src/database/repository.py` - Data access layer (CRUD operations)
- `src/adif/parser.py` - ADIF file parser with full 3.1.5 support
- `src/ui/field_manager.py` - Dynamic field display preferences
- `src/awards/base.py` - Abstract award program class
- `src/awards/dxcc.py` - DXCC award implementation

### Documentation

- `README.md` - User guide and quick start
- `UV_GUIDE.md` - Complete UV command reference
- `ANSWER_TO_YOUR_QUESTION.md` - Why UV can download Python
- `Ham_Radio_Logging_Program_Design_Document.txt` - Full technical specifications

## Development Workflow

### Setup

```bash
cd "W4GNS Logger"
uv venv --python 3.14 venv
source venv/bin/activate
uv pip install -r uv.lock  # or requirements.txt
```

### Testing

```bash
# Run all tests
pytest src/tests/

# With coverage
pytest src/tests/ --cov=src

# Specific module
pytest src/tests/test_adif.py
```

### Code Quality

```bash
black src/           # Format
flake8 src/          # Lint
mypy src/            # Type check
```

### Run Application

```bash
python src/main.py
```

## Common Tasks

### Adding a New Award Program

1. Create file `src/awards/{award_name}.py`
2. Inherit from `AwardProgram` base class
3. Implement: `validate()`, `calculate_progress()`, `get_requirements()`, `get_endorsements()`
4. Add to `config/awards.yaml`
5. Register in award factory (TODO)

### Adding a New Extended Field

1. Add column to Contact model in `src/database/models.py`
2. Add to appropriate category in `src/ui/field_manager.py`
3. Add validation in `src/utils/validators.py` if needed
4. Database migration will auto-create column on first run

### Adding a GUI Tab

1. Create class inheriting QWidget in `src/ui/tabs/{tab_name}.py`
2. Implement layout and signal/slot connections
3. Add to main_window.py tab widget
4. Connect to business logic services

## Database

### Initialization

- Auto-creates on first run in `~/.w4gns_logger/contacts.db`
- Path configurable in settings
- Uses SQLite3 via SQLAlchemy

### Key Tables

- `contacts` - QSO records with 80+ ADIF fields
- `qsl_records` - QSL confirmation history
- `awards_progress` - Award progress tracking
- `ui_field_preferences` - User field display settings
- `cluster_spots` - DX cluster spot cache (optional)
- `configuration` - App configuration storage

## Running Tests

```bash
# Verify ADIF parser
python -c "from src.adif.parser import ADIFParser; p = ADIFParser(); print(f'Fields: {len(p.ALL_SUPPORTED_FIELDS)}')"

# Verify database models
python -c "from src.database.models import Contact, Award; print('✓ Models OK')"

# Verify configuration
python -c "from src.config.settings import get_config_manager; c = get_config_manager(); print(f'Config: {c.config_file}')"
```

## Next Steps for Development

1. **Implement GUI tabs** - Contact logging, list view, search
2. **Connect database** - CRUD operations from GUI
3. **Implement ADIF export** - Serializer for ADI/ADX
4. **Build award engine** - Calculate progress for all awards
5. **Add DX Cluster** - Telnet client for real-time spots
6. **QRZ Integration** - Upload contacts to QRZ
7. **Testing** - Comprehensive test coverage
8. **Optimization** - Performance tuning for large datasets

## Important Notes

- **Python 3.14.0** managed by UV (not system Python)
- **SQLite database** auto-creates on first run
- **ADIF compliance** - Full 3.1.5 standard support
- **Field flexibility** - Users control which fields to display
- **Extensible awards** - Plugin architecture for new awards
- **Cross-platform** - PyQt6 works on Windows/macOS/Linux

## Contact & Documentation

- **Design Document**: `Ham_Radio_Logging_Program_Design_Document.txt` (comprehensive spec)
- **README**: `README.md` (user guide)
- **UV Guide**: `UV_GUIDE.md` (package manager reference)
- **Code**: Well-commented, type-hinted Python 3.14

---

**Last Updated**: October 20, 2025
**Version**: 1.0.0 (Phase 1-2 complete)
**Python**: 3.14.0 (UV-managed)
