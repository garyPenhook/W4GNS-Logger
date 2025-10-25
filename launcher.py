#!/usr/bin/env python3
"""
W4GNS Ham Radio Logger Launcher

Provides cross-platform GUI launching with automatic environment detection.
Can be run from file manager (double-click) or from terminal.

Usage:
    python launcher.py                # Auto-detect and launch
    python launcher.py --console      # Show terminal window
    python launcher.py --debug        # Enable debug logging
"""

import sys
import os
import subprocess
import platform
import argparse
from pathlib import Path


def get_project_root() -> Path:
    """Get the project root directory"""
    return Path(__file__).parent.absolute()


def setup_environment(project_root: Path, debug: bool = False) -> None:
    """Setup environment variables for Qt"""
    if debug:
        os.environ['QT_DEBUG_PLUGINS'] = '1'
        os.environ['QT_DEBUG_EVENTS'] = '1'

    # Try to detect best platform
    if platform.system() == 'Linux':
        # Linux: try platforms in order
        if not os.environ.get('QT_QPA_PLATFORM'):
            # First, try to set DISPLAY if not set but X is running
            if not os.environ.get('DISPLAY') and not os.environ.get('WAYLAND_DISPLAY'):
                # Check if X is running on :0
                try:
                    result = subprocess.run(
                        ["ps", "aux"],
                        capture_output=True,
                        text=True,
                        timeout=2
                    )
                    # Look for Xorg process with :0 display
                    if ":0" in result.stdout and ("Xorg" in result.stdout or "X " in result.stdout):
                        os.environ['DISPLAY'] = ':0'
                        print("✓ Detected X server on :0, setting DISPLAY")
                except Exception as e:
                    pass

            # Get venv Python for platform testing
            venv_path = project_root / "venv"
            if platform.system() == 'Windows':
                venv_python = venv_path / "Scripts" / "python.exe"
            else:
                venv_python = venv_path / "bin" / "python"

            # Now try platforms in order
            for platform_name in ['xcb', 'wayland', 'offscreen']:
                try:
                    # Test platform directly using venv Python's QApplication
                    test_env = os.environ.copy()
                    test_env['QT_QPA_PLATFORM'] = platform_name

                    result = subprocess.run(
                        [str(venv_python), "-c", "from PyQt6.QtWidgets import QApplication; QApplication([]).quit()"],
                        capture_output=True,
                        timeout=2,
                        env=test_env
                    )

                    if result.returncode == 0:
                        os.environ['QT_QPA_PLATFORM'] = platform_name
                        print(f"✓ Using platform: {platform_name}")
                        return
                except Exception as e:
                    pass

            # If no platform worked, default to offscreen
            print("No platform detected, using offscreen (headless) mode")
            os.environ['QT_QPA_PLATFORM'] = 'offscreen'
    # Windows and macOS don't need platform specification


def create_virtual_environment(project_root: Path) -> bool:
    """Create virtual environment if it doesn't exist"""
    venv_path = project_root / "venv"

    if venv_path.exists():
        return True

    print("Virtual environment not found. Creating with UV and Python 3.14...")
    try:
        # Use UV to create venv with Python 3.14
        result = subprocess.run(
            ["uv", "venv", "--python", "3.14", "venv"],
            cwd=project_root
        )
        if result.returncode == 0:
            print("Virtual environment created successfully with UV")
            return True
        else:
            print(f"UV venv creation failed with return code {result.returncode}")
            return False
    except FileNotFoundError:
        print("UV not found in PATH. Please install UV first:")
        print("  https://docs.astral.sh/uv/getting-started/installation/")
        return False
    except Exception as e:
        print(f"Failed to create virtual environment: {e}")
        return False


def install_dependencies(project_root: Path) -> bool:
    """Install dependencies using UV"""
    venv_path = project_root / "venv"
    requirements_file = project_root / "requirements.txt"

    if not requirements_file.exists():
        print("requirements.txt not found!")
        return False

    # Get the python executable in the venv
    if platform.system() == 'Windows':
        python_exe = venv_path / "Scripts" / "python.exe"
    else:
        python_exe = venv_path / "bin" / "python"

    # Check if PyQt6 is already installed (quick check)
    print("Checking if dependencies are already installed...")
    try:
        result = subprocess.run(
            [str(python_exe), "-c", "import PyQt6; print('OK')"],
            capture_output=True,
            timeout=5
        )
        if result.returncode == 0:
            print("✓ Dependencies already installed")
            return True
    except Exception:
        pass

    print("Installing dependencies with UV...")
    try:
        # Use UV with explicit python path
        cmd = [
            "uv", "pip", "install",
            "--python", str(python_exe),
            "-r", str(requirements_file)
        ]

        result = subprocess.run(cmd, cwd=project_root)

        if result.returncode == 0:
            print("Dependencies installed successfully")
            return True
        else:
            print(f"Installation failed with return code {result.returncode}")
            return False

    except Exception as e:
        print(f"Failed to install dependencies: {e}")
        return False


def run_application(project_root: Path, debug: bool = False) -> int:
    """Run the main application"""
    venv_path = project_root / "venv"
    main_script = project_root / "src" / "main.py"

    if not main_script.exists():
        print(f"main.py not found at {main_script}")
        return 1

    # Get Python executable path
    if platform.system() == 'Windows':
        python_exe = venv_path / "Scripts" / "python.exe"
    else:
        python_exe = venv_path / "bin" / "python"

    if not python_exe.exists():
        print(f"Python executable not found at {python_exe}")
        return 1

    print(f"Starting application from {main_script}...")

    try:
        # Run with inherited environment
        result = subprocess.run(
            [str(python_exe), str(main_script)],
            cwd=project_root,
            env=os.environ.copy()
        )
        return result.returncode
    except KeyboardInterrupt:
        print("\nApplication closed by user")
        return 0
    except Exception as e:
        print(f"Failed to run application: {e}")
        return 1


def main():
    """Main launcher function"""
    parser = argparse.ArgumentParser(
        description="W4GNS Ham Radio Logger Launcher"
    )
    parser.add_argument(
        "--console",
        action="store_true",
        help="Show console window (default for terminal launch)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable Qt debug logging"
    )
    parser.add_argument(
        "--setup-only",
        action="store_true",
        help="Only setup environment, don't run application"
    )

    args = parser.parse_args()

    project_root = get_project_root()
    print(f"W4GNS Ham Radio Logger")
    print(f"Project root: {project_root}")
    print(f"Platform: {platform.system()} {platform.release()}")
    print()

    # Setup environment
    setup_environment(project_root, debug=args.debug)

    # Create virtual environment if needed
    if not create_virtual_environment(project_root):
        print("ERROR: Could not create virtual environment")
        return 1

    # Install dependencies if needed
    if not install_dependencies(project_root):
        print("ERROR: Could not install dependencies")
        return 1

    if args.setup_only:
        print("Setup complete!")
        return 0

    # Run application
    return run_application(project_root, debug=args.debug)


if __name__ == "__main__":
    sys.exit(main())
