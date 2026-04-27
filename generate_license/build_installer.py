"""
Build seektrack_fngerprint_Installer.exe
==========================================
Bundles license files + seektrack.exe into a single installer for customers.

Prerequisites
-------------
1. Run `python build_agent.py` first to produce dist/seektrack.exe
2. Generate a license via the admin UI (python server.py) so that
   output/license.json, output/public_key.pem, output/fingerprint.txt exist

Usage
-----
    cd generate_license
    python build_installer.py

Output
------
    dist/seektrack_fngerprint_Installer.exe
"""

import subprocess
import sys
from pathlib import Path

BASE_DIR   = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / 'output'
DIST_DIR   = BASE_DIR / 'dist'
LOGO_PATH  = BASE_DIR / 'images' / 'logo-nichtel.png'

LICENSE_FILES = ['license.json', 'public_key.pem', 'fingerprint.txt']
AGENT_EXE     = DIST_DIR / 'seektrack.exe'


def check_files():
    ok = True

    missing_license = [f for f in LICENSE_FILES if not (OUTPUT_DIR / f).is_file()]
    if missing_license:
        print(f'❌  Missing license files in output/: {", ".join(missing_license)}')
        print('    Generate a license first via the admin UI (python server.py)')
        ok = False
    else:
        print('✅  License files found in output/')

    if not AGENT_EXE.is_file():
        print(f'❌  seektrack.exe not found at {AGENT_EXE}')
        print('    Build it first:  python build_agent.py')
        ok = False
    else:
        print(f'✅  seektrack.exe found ({AGENT_EXE.stat().st_size / 1024:.0f} KB)')

    if not ok:
        sys.exit(1)


def build():
    sep = ';' if sys.platform == 'win32' else ':'

    add_data_args = []

    # Bundle license files into license_files/ subdirectory inside the exe
    for f in LICENSE_FILES:
        src = OUTPUT_DIR / f
        add_data_args.extend(['--add-data', f'{src}{sep}license_files'])

    # Bundle seektrack.exe into the root of the bundle
    add_data_args.extend(['--add-data', f'{AGENT_EXE}{sep}.'])

    # Bundle logo
    if LOGO_PATH.is_file():
        add_data_args.extend(['--add-data', f'{LOGO_PATH}{sep}.'])
    else:
        print(f'⚠   Logo not found at {LOGO_PATH} — building without it.')

    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--onefile',
        '--windowed',
        '--name', 'seektrack_fngerprint_Installer',
        '--icon', 'NONE',
        *add_data_args,
        str(BASE_DIR / 'license_installer.py'),
    ]

    print(f'\nBuilding installer...\n')

    result = subprocess.run(cmd, cwd=str(BASE_DIR))

    if result.returncode == 0:
        exe = DIST_DIR / 'seektrack_fngerprint_Installer.exe'
        print(f'\n✅  Build successful!')
        print(f'    Output : {exe}')
        print(f'    Size   : {exe.stat().st_size / 1024 / 1024:.1f} MB')
        print()
        print('    Send this .exe to the customer.')
        print('    When they run it:')
        print('      1. License files → backend/license/')
        print('      2. seektrack.exe → C:\\SeekTrack\\')
        print('      3. Scheduled Task "SeekTrackAgent" registered (SYSTEM, ONSTART)')
        print('      4. Agent started immediately')
    else:
        print(f'\n❌  Build failed (exit code {result.returncode})')
        sys.exit(1)


if __name__ == '__main__':
    check_files()
    build()
