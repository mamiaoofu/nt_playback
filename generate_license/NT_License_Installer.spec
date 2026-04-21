# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['C:\\Users\\ACER\\Documents\\GitHub\\nt_playback\\generate_license\\license_installer.py'],
    pathex=[],
    binaries=[],
    datas=[('C:\\Users\\ACER\\Documents\\GitHub\\nt_playback\\generate_license\\output\\license.json', 'license_files'), ('C:\\Users\\ACER\\Documents\\GitHub\\nt_playback\\generate_license\\output\\public_key.pem', 'license_files'), ('C:\\Users\\ACER\\Documents\\GitHub\\nt_playback\\generate_license\\output\\fingerprint.txt', 'license_files')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='NT_License_Installer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='NONE',
)
