# W4GNS Ham Radio Logger

A comprehensive ham radio contact logging application with support for ADIF import/export, award tracking, DX cluster integration, and QRZ.com synchronization.

**Version**: 1.0.0
**Python**: 3.14.0 (managed by UV)
**Package Manager**: UV (100x faster than pip)

## Features

- **Contact Logging**: Record complete QSO details with comprehensive field support
- **ADIF Support**: Full ADIF 3.x compliant import/export (ADI and ADX formats)
- **Award Tracking**: Track progress for DXCC, WAS, WAC, SKCC, IOTA, and SOTA awards
- **DX Cluster Integration**: Real-time spot monitoring from multiple cluster nodes
- **QRZ.com Integration**: Upload contacts to QRZ logbook
- **Cross-Platform GUI**: Modern PyQt6 interface for Windows, macOS, and Linux
- **Database**: SQLite backend with comprehensive contact management
- **Reproducible Builds**: UV lock file ensures identical installs everywhere

## Requirements

- **Python**: 3.14+ (automatically downloaded and managed by UV)
- **UV**: Modern Python package manager (already installed)
- **PyQt6**: GUI framework
- **SQLAlchemy**: Database ORM
- All other dependencies in `requirements.txt`

## Quick Start

### Automatic Setup (Recommended)

```bash
cd "W4GNS Logger"
./run.sh              # Linux/macOS
# OR
run.bat               # Windows
```

This will automatically:
- Download Python 3.14 (if not already available)
- Create a virtual environment
- Install all dependencies
- Launch the application

### Manual Setup

```bash
cd "W4GNS Logger"

# Create virtual environment with Python 3.14
uv venv --python 3.14 venv

# Activate it
source venv/bin/activate  # Linux/macOS
# OR
venv\Scripts\activate.bat # Windows

# Install dependencies
uv pip install --python ./venv/bin/python -r requirements.txt

# Run the application
python src/main.py
```

### Using Reproducible Lock File

For guaranteed identical installs across team/CI:

```bash
cd "W4GNS Logger"
uv venv --python 3.14 venv
source venv/bin/activate

# Install from lock file (fast & reproducible)
uv pip install --python ./venv/bin/python --require-hashes -r uv.lock

python src/main.py
```

## Project Structure

```
W4GNS Logger/
├── src/                          # Main source code
│   ├── main.py                   # Application entry point
│   ├── config/                   # Configuration management
│   │   └── settings.py
│   ├── database/                 # Database layer
│   │   ├── models.py             # SQLAlchemy ORM models
│   │   └── repository.py         # Data access layer
│   ├── adif/                     # ADIF handling
│   │   ├── parser.py             # ADIF parser
│   │   └── serializer.py         # ADIF export
│   ├── awards/                   # Award programs
│   │   ├── base.py               # Abstract award class
│   │   ├── dxcc.py               # DXCC implementation
│   │   └── registry.py           # Award registry
│   ├── ui/                       # PyQt6 GUI
│   │   ├── main_window.py        # Main application window
│   │   ├── tabs/                 # Tab implementations
│   │   └── dialogs/              # Custom dialogs
│   ├── business_logic/           # Business logic services
│   ├── utils/                    # Utility modules
│   │   └── validators.py         # Data validators
│   └── tests/                    # Unit tests
│
├── config/                       # Configuration files
│   ├── awards.yaml               # Award definitions
│   ├── clusters.yaml             # DX cluster nodes
│   └── qrz.yaml                  # QRZ settings
│
├── requirements.txt              # Python dependencies
├── venv/                         # Virtual environment
└── README.md                     # This file
```

## Configuration

Configuration files are located in the `config/` directory:

### awards.yaml
Define and enable/disable award programs (DXCC, WAS, SKCC, etc.)

### clusters.yaml
Configure DX cluster node connections

### qrz.yaml
QRZ.com API settings

### User Settings
User-specific settings are stored in:
- **Linux/macOS**: `~/.w4gns_logger/config.yaml`
- **Windows**: `%USERPROFILE%\.w4gns_logger\config.yaml`

## Development

### Running Tests

```bash
pytest src/tests/
```

### Code Quality

```bash
black src/                   # Format code
flake8 src/                  # Lint
mypy src/                    # Type checking
```

## Database

The application uses SQLite for data storage. Database location is configurable in settings:
- Default: `~/.w4gns_logger/contacts.db`

### Database Schema

- **contacts**: QSO records
- **qsl_records**: QSL confirmation history
- **awards_progress**: Award progress tracking
- **cluster_spots**: Optional cluster spot logging
- **configuration**: Application settings

## Usage

### Logging a Contact

1. Go to the **Logging** tab
2. Enter contact details:
   - Callsign
   - Date/Time
   - Band & Frequency
   - Mode
   - Signal reports
3. Click **Save**

### Importing ADIF

1. Go to **File** → **Import ADIF**
2. Select ADIF file (ADI or ADX format)
3. Review import preview
4. Click **Import**

### Tracking Awards

1. Go to **Awards** tab
2. Select award program
3. View current progress
4. Click on award for details

### DX Cluster

1. Configure cluster nodes in **config/clusters.yaml**
2. Go to **DX Cluster** tab
3. Click **Connect**
4. Monitor real-time spots

## Dependencies

### Core
- PyQt6 - GUI framework
- SQLAlchemy - Database ORM
- adif_io - ADIF file handling

### Network
- requests - HTTP client
- asyncio - Async I/O for cluster connections

### Configuration
- PyYAML - YAML configuration

### Security
- cryptography - Credential encryption

### Development
- pytest - Testing framework
- black - Code formatter
- mypy - Type checker
- flake8 - Linter

See `requirements.txt` for complete list and versions.

## Important Guides

### For Understanding UV Setup
→ Read **ANSWER_TO_YOUR_QUESTION.md** for detailed explanation of why UV can download Python while pip cannot.

### For UV Commands Reference
→ Read **UV_GUIDE.md** for complete command reference, workflows, and examples.

### For Design Specifications
→ Read **Ham_Radio_Logging_Program_Design_Document.txt** for comprehensive technical requirements.

## License

This project is designed for ham radio operators. Please respect applicable regulations and licensing requirements.

## Support

For issues, feature requests, or questions:
- Check the Design Document for detailed specifications
- Review ANSWER_TO_YOUR_QUESTION.md for UV/Python setup issues
- Check UV_GUIDE.md for dependency and installation help
- Review existing code structure
- Submit issues through your development workflow

## Contributing

When adding new features:
1. Follow existing code structure
2. Add tests for new functionality
3. Update relevant configuration files
4. Maintain ADIF standard compliance
5. Keep uv.lock updated: `uv pip compile requirements.txt --python 3.14 -o uv.lock`

---

**Version**: 1.0.0
**Python**: 3.14.0 (managed by UV)
**Package Manager**: UV (100x faster than pip)
**Last Updated**: October 20, 2025
