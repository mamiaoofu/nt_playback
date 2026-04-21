"""
Build both customer-facing executables from fingerprint_collector.py.

  seektrack.exe              → bundled INSIDE seektrack_fngerprint_Installer.exe
                               (run via Scheduled Task as the attestation agent)

  fingerprint_collector.exe  → given to customer BEFORE license is generated
                               (GUI: collects fingerprint, saves to Desktop)

Usage
-----
    python build_agent.py

Output: generate_license/dist/seektrack.exe
        generate_license/dist/fingerprint_collector.exe

After this, run build_installer.py to produce the final installer .exe.
"""

import subprocess
import sys
from pathlib import Path

BASE_DIR  = Path(__file__).resolve().parent
LOGO_PATH = BASE_DIR / 'images' / 'logo-nichtel.png'
SOURCE    = BASE_DIR / 'fingerprint_collector.py'


def _add_data():
    if LOGO_PATH.exists():
        sep = ';' if sys.platform == 'win32' else ':'
        return ['--add-data', f'{LOGO_PATH}{sep}.']
    print(f'[warn] Logo not found at {LOGO_PATH} — building without it.')
    return []


def build(name: str):
    print(f'\n─── Building {name}.exe ───')
    subprocess.run(
        [
            sys.executable, '-m', 'PyInstaller',
            '--onefile',
            '--noconsole',
            '--name', name,
            *_add_data(),
            str(SOURCE),
        ],
        cwd=str(BASE_DIR),
        check=True,
    )
    out = BASE_DIR / 'dist' / f'{name}.exe'
    print(f'Built: {out}  ({out.stat().st_size / 1024:.0f} KB)')


def main():
    # seektrack.exe — used as attestation agent inside the installer
    build('seektrack')
    # fingerprint_collector.exe — sent to customer for fingerprint collection
    build('fingerprint_collector')

    print('\n✅  Both executables built successfully.')
    print('   dist/seektrack.exe             → used by build_installer.py')
    print('   dist/fingerprint_collector.exe → send to customer for fingerprint collection')


if __name__ == '__main__':
    main()
