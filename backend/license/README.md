# License Files

This directory should contain the following files for the license system to work:

| File | Source | Description |
|------|--------|-------------|
| `license.json` | From Admin (generated via License Generator) | Signed license file |
| `public_key.pem` | From Admin (generated via License Generator) | RSA public key for signature verification |
| `fingerprint.txt` | From `fingerprint.exe` run on this host | SHA-256 hardware fingerprint |

## Deployment Steps

1. Run `fingerprint.exe` on the Windows Server host → creates `seektrack_fngerprint` folder on Desktop
2. Send the `seektrack_fngerprint` folder to the Admin
3. Admin generates license using the License Generator tool → sends back `license.json` + `public_key.pem`
4. Place all 3 files in this directory (`backend/license/`)
5. Run `docker-compose up -d`

> **Note:** This directory is mounted as read-only into the Docker container.
