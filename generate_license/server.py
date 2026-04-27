"""
NT License Generator — Flask Server
====================================
Admin tool for generating RSA-signed license files.
Run: python server.py
"""

import base64
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from flask import Flask, jsonify, request, send_file, send_from_directory

app = Flask(__name__, static_folder='.', static_url_path='')

BASE_DIR = Path(__file__).resolve().parent
KEYS_DIR = BASE_DIR / 'keys'
OUTPUT_DIR = BASE_DIR / 'output'

KEYS_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

PRIVATE_KEY_PATH = KEYS_DIR / 'private_key.pem'
PUBLIC_KEY_PATH = KEYS_DIR / 'public_key.pem'


def _load_private_key():
    if not PRIVATE_KEY_PATH.exists():
        return None
    return serialization.load_pem_private_key(
        PRIVATE_KEY_PATH.read_bytes(), password=None
    )


def _load_public_key():
    if not PUBLIC_KEY_PATH.exists():
        return None
    return serialization.load_pem_public_key(PUBLIC_KEY_PATH.read_bytes())


def _canonical_json(obj):
    """Produce deterministic JSON bytes for signing."""
    return json.dumps(obj, sort_keys=True, separators=(',', ':')).encode('utf-8')


# ─── Routes ────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')


@app.route('/api/keys-status')
def keys_status():
    return jsonify({
        'has_private_key': PRIVATE_KEY_PATH.exists(),
        'has_public_key': PUBLIC_KEY_PATH.exists(),
    })


@app.route('/api/generate-keys', methods=['POST'])
def generate_keys():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    # Save private key
    PRIVATE_KEY_PATH.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )

    # Save public key
    public_key = private_key.public_key()
    PUBLIC_KEY_PATH.write_bytes(
        public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )

    return jsonify({'message': 'Generated successfully.'})


@app.route('/api/import-keys', methods=['POST'])
def import_keys():
    """Import an existing private key PEM. Validates it and derives the public key."""
    if 'private_key' not in request.files:
        return jsonify({'error': 'No file uploaded. Send field name: private_key'}), 400

    file = request.files['private_key']
    pem_bytes = file.read()

    # Validate: must be a valid unencrypted RSA private key
    try:
        private_key = serialization.load_pem_private_key(pem_bytes, password=None)
    except Exception as e:
        return jsonify({'error': f'Invalid private key PEM: {e}'}), 400

    # Ensure it is RSA
    if not isinstance(private_key, rsa.RSAPrivateKey):
        return jsonify({'error': 'Only RSA private keys are supported.'}), 400

    # Save private key
    PRIVATE_KEY_PATH.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )

    # Derive and save public key
    public_key = private_key.public_key()
    PUBLIC_KEY_PATH.write_bytes(
        public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )

    key_size = private_key.key_size
    return jsonify({'message': f'Private key imported successfully (RSA-{key_size}). Public key derived and saved.'})


@app.route('/api/download-private-key')
def download_private_key():
    if not PRIVATE_KEY_PATH.exists():
        return jsonify({'error': 'No private key found.'}), 404
    return send_file(
        str(PRIVATE_KEY_PATH),
        as_attachment=True,
        download_name='private_key.pem',
        mimetype='application/x-pem-file',
    )


@app.route('/api/generate-license', methods=['POST'])
def generate_license():
    private_key = _load_private_key()
    if not private_key:
        return jsonify({'error': 'No private key found. Generate keys first.'}), 400

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No JSON body provided.'}), 400

    # Build license_data
    license_data = {
        'fingerprint': data.get('fingerprint', ''),
        'license_id': data.get('license_id', ''),
        'customer_name': data.get('customer_name', ''),
        'issued_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'expiry': data.get('expiry', ''),
        'features': {
            'max_main_db': data.get('max_main_db'),
            'max_concurrent_users': data.get('max_concurrent_users'),
            'allowed_menus': data.get('allowed_menus', []),
            'config_flags': data.get('config_flags', {}),
        },
    }

    # Sign
    canonical = _canonical_json(license_data)
    signature = private_key.sign(
        canonical,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH,
        ),
        hashes.SHA256(),
    )

    license_obj = {
        'license_data': license_data,
        'signature': base64.b64encode(signature).decode('ascii'),
    }

    # Save to output
    output_path = OUTPUT_DIR / 'license.json'
    output_path.write_text(json.dumps(license_obj, indent=2, ensure_ascii=False), encoding='utf-8')

    # Save fingerprint.txt to output (so installer can bundle it)
    fingerprint_path = OUTPUT_DIR / 'fingerprint.txt'
    fingerprint_path.write_text(data.get('fingerprint', ''), encoding='utf-8')

    # Copy public_key.pem to output
    import shutil
    if PUBLIC_KEY_PATH.exists():
        shutil.copy2(PUBLIC_KEY_PATH, OUTPUT_DIR / 'public_key.pem')

    return jsonify({
        'message': 'License generated successfully.',
        'license': license_obj,
        'output_path': str(OUTPUT_DIR),
    })


@app.route('/api/public-key')
def download_public_key():
    if not PUBLIC_KEY_PATH.exists():
        return jsonify({'error': 'No public key found.'}), 404
    return send_file(str(PUBLIC_KEY_PATH), as_attachment=True, download_name='public_key.pem')


@app.route('/api/verify-license', methods=['POST'])
def verify_license():
    """Test endpoint: verify a license.json with the current public key."""
    public_key = _load_public_key()
    if not public_key:
        return jsonify({'error': 'No public key found.'}), 400

    data = request.get_json()
    if not data or 'license_data' not in data or 'signature' not in data:
        return jsonify({'error': 'Invalid license format.'}), 400

    try:
        canonical = _canonical_json(data['license_data'])
        signature = base64.b64decode(data['signature'])

        public_key.verify(
            signature,
            canonical,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH,
            ),
            hashes.SHA256(),
        )
        return jsonify({'valid': True, 'message': 'Signature is valid.'})
    except Exception as e:
        return jsonify({'valid': False, 'message': f'Signature verification failed: {e}'})


LOGO_PATH = BASE_DIR / 'images' / 'logo-nichtel.png'
INSTALLER_NAME = 'seektrack_fngerprint_Installer'
REQUIRED_LICENSE_FILES = ['license.json', 'public_key.pem', 'fingerprint.txt']


@app.route('/api/build-installer', methods=['POST'])
def build_installer():
    """Build the installer .exe via PyInstaller and return it for download."""
    # Check that all license files exist in output/
    missing = [f for f in REQUIRED_LICENSE_FILES if not (OUTPUT_DIR / f).is_file()]
    if missing:
        return jsonify({'error': f'Missing files in output/: {", ".join(missing)}. Generate a license first.'}), 400

    sep = ';' if sys.platform == 'win32' else ':'
    add_data_args = []
    for f in REQUIRED_LICENSE_FILES:
        src = str(OUTPUT_DIR / f)
        add_data_args.extend(['--add-data', f'{src}{sep}license_files'])

    # Bundle logo if available
    if LOGO_PATH.is_file():
        add_data_args.extend(['--add-data', f'{LOGO_PATH}{sep}.'])

    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--onefile',
        '--windowed',
        '--name', INSTALLER_NAME,
        '--icon', 'NONE',
        '--distpath', str(BASE_DIR / 'dist'),
        '--workpath', str(BASE_DIR / 'build'),
        '--specpath', str(BASE_DIR),
        '-y',  # overwrite without asking
        *add_data_args,
        str(BASE_DIR / 'license_installer.py'),
    ]

    try:
        result = subprocess.run(
            cmd,
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            timeout=300,
        )
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Build timed out (5 min). Try running build_installer.py manually.'}), 500
    except FileNotFoundError:
        return jsonify({'error': 'Python executable not found.'}), 500

    if result.returncode != 0:
        # Return last 500 chars of stderr for debugging
        err_tail = (result.stderr or result.stdout or 'Unknown error')[-500:]
        return jsonify({'error': f'Build failed (exit {result.returncode}): {err_tail}'}), 500

    exe_path = BASE_DIR / 'dist' / f'{INSTALLER_NAME}.exe'
    if not exe_path.is_file():
        return jsonify({'error': 'Build completed but .exe not found in dist/.'}), 500

    return send_file(
        str(exe_path),
        as_attachment=True,
        download_name=f'{INSTALLER_NAME}.exe',
        mimetype='application/octet-stream',
    )


@app.route('/api/installer-status')
def installer_status():
    """Check if a pre-built installer .exe exists."""
    exe_path = BASE_DIR / 'dist' / f'{INSTALLER_NAME}.exe'
    if exe_path.is_file():
        size_mb = exe_path.stat().st_size / 1024 / 1024
        return jsonify({'exists': True, 'size_mb': round(size_mb, 1)})
    return jsonify({'exists': False})


@app.route('/api/download-installer')
def download_installer():
    """Download the pre-built installer .exe (if it exists)."""
    exe_path = BASE_DIR / 'dist' / f'{INSTALLER_NAME}.exe'
    if not exe_path.is_file():
        return jsonify({'error': 'No installer found. Build it first.'}), 404
    return send_file(
        str(exe_path),
        as_attachment=True,
        download_name=f'{INSTALLER_NAME}.exe',
        mimetype='application/octet-stream',
    )


if __name__ == '__main__':
    print(f'License Generator running at http://localhost:5000')
    print(f'Keys directory: {KEYS_DIR}')
    print(f'Output directory: {OUTPUT_DIR}')
    app.run(debug=True, port=5000)
