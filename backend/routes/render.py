# routes/render.py
# LibreOffice-based Excel-to-HTML render + diagnostics.

import io
import os
import shutil
import subprocess
import tempfile
import urllib.request
from flask import request, send_file, jsonify


def render_routes(app):
    _RENDER_DIRS = {}

    def _libreoffice_bin():
        # Windows: soffice.exe (usually not on PATH after winget install)
        # Linux/macOS: libreoffice or soffice
        import platform

        candidates = []
        if platform.system() == 'Windows':
            candidates += [
                shutil.which('soffice'),
                r'C:\Program Files\LibreOffice\program\soffice.exe',
                r'C:\Program Files (x86)\LibreOffice\program\soffice.exe',
            ]
        else:
            candidates += [shutil.which('libreoffice'), shutil.which('soffice')]

        for c in candidates:
            if c and os.path.exists(c):
                return c
        return None

    def _libreoffice_path():
        return _libreoffice_bin()

    def _libreoffice_works():
        # Note: this --version check sometimes falsely fails on Windows 
        # due to profile locks, but the actual render works fine.
        bin_path = _libreoffice_bin()
        if not bin_path:
            return False
        try:
            subprocess.run(
                [bin_path, '--version'],
                check=True, timeout=15, capture_output=True
            )
            return True
        except Exception:
            return False

    # ── Diagnostic endpoint ────────────────────────────────────
    @app.route('/api/render/diagnose', methods=['GET'])
    def render_diagnose():
        lo_path = _libreoffice_path()
        lo_ok = _libreoffice_works()
        return jsonify({
            'libreoffice_path': lo_path,
            'libreoffice_installed': bool(lo_path),
            'libreoffice_works': lo_ok,
            'hint': None if lo_ok else 'Version check failed. The actual render may still work.',
            'port_env': os.environ.get('PORT', '5000 (default)')
        })

    # ── Fetch original workbook via the existing /file endpoint ─
    def _fetch_original(dataset_id, headers):
        port = int(os.environ.get('PORT', 5000))
        # Try 127.0.0.1 first (fast, no DNS)
        urls = [
            f'http://127.0.0.1:{port}/api/dataset/{dataset_id}/file',
            f'http://localhost:{port}/api/dataset/{dataset_id}/file',
        ]
        last_err = None
        for url in urls:
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=30) as resp:
                    return resp.read(), resp.headers.get('Content-Type', ''), resp.headers.get('Content-Disposition', '')
            except Exception as e:
                last_err = f'{url} → {e}'
                continue
        raise RuntimeError(f'Cannot reach original workbook. Tried: {last_err}')

    # ── Main render endpoint ────────────────────────────────────
    @app.route('/api/dataset/<dataset_id>/render', methods=['GET'])
    def render_dataset_html(dataset_id):
        # REMOVED the blocking _libreoffice_works() check here.
        # We let the actual conversion try and catch real errors below.

        # Forward auth header so /file accepts the request
        headers = {}
        if request.headers.get('Authorization'):
            headers['Authorization'] = request.headers['Authorization']

        try:
            file_bytes, content_type, cd = _fetch_original(dataset_id, headers)
        except Exception as e:
            return jsonify({
                'success': False,
                'stage': 'fetch-original',
                'message': str(e),
                'hint': 'Check that /api/dataset/<id>/file exists and returns the file for this id.'
            }), 500

        if not file_bytes:
            return jsonify({
                'success': False,
                'stage': 'fetch-original',
                'message': 'The /file endpoint returned an empty body.'
            }), 400

        ext = '.xlsx'
        low = (content_type + ' ' + cd).lower()
        for candidate in ('.xlsm', '.xlsb', '.xltx', '.xltm', '.xls', '.ods'):
            if candidate in low:
                ext = candidate
                break

        work_dir = tempfile.mkdtemp(prefix='render_')
        # Use a PERSISTENT profile folder so LibreOffice stays warm and loads fast
        profile_dir = os.path.join(tempfile.gettempdir(), 'dura_lo_profile')
        src_path = os.path.join(work_dir, 'workbook' + ext)
        with open(src_path, 'wb') as f:
            f.write(file_bytes)

        bin_path = _libreoffice_bin()
        if not bin_path:
            shutil.rmtree(work_dir, ignore_errors=True)
            return jsonify({
                'success': False,
                'stage': 'libreoffice-check',
                'message': 'LibreOffice executable not found on this machine.'
            }), 500

        try:
            # Added --nologo, --nodefault, --nolockcheck, and macro bypass flags.
            # Increased timeout to 300s.
            subprocess.run(
                [bin_path, '--headless', '--norestore', '--nologo', '--nodefault', '--nolockcheck', '--nofirststartwizard',
                 f'-env:UserInstallation=file:///{profile_dir.replace(os.sep, "/")}',
                 '--convert-to', 'html:HTML (StarCalc):{"FilterOptions":{"MacroExecutionMode":"0"}}',
                 '--outdir', work_dir, src_path],
                check=True, timeout=300, capture_output=True, text=True
            )

            html_files = [f for f in os.listdir(work_dir) if f.lower().endswith('.html')]
            if not html_files:
                shutil.rmtree(work_dir, ignore_errors=True)
                return jsonify({
                    'success': False,
                    'stage': 'libreoffice-output',
                    'message': 'LibreOffice ran but produced no .html file.'
                }), 500

            html_path = os.path.join(work_dir, html_files[0])
            with open(html_path, 'rb') as f:
                payload = f.read()

            payload = payload.replace(
                b'src="', b'src="/api/dataset/' + str(dataset_id).encode() + b'/render-asset/'
            ).replace(
                b'href="', b'href="/api/dataset/' + str(dataset_id).encode() + b'/render-asset/'
            )

            old_dir = _RENDER_DIRS.get(str(dataset_id))
            if old_dir and old_dir != work_dir:
                shutil.rmtree(old_dir, ignore_errors=True)
            _RENDER_DIRS[str(dataset_id)] = work_dir

            response = send_file(io.BytesIO(payload), mimetype='text/html; charset=utf-8')
            response.headers['Cache-Control'] = 'no-store'
            # These two headers stop the browser from blocking the iframe
            response.headers['X-Frame-Options'] = 'ALLOWALL'
            response.headers['Content-Security-Policy'] = "frame-ancestors *"
            return response

        except subprocess.TimeoutExpired:
            shutil.rmtree(work_dir, ignore_errors=True)
            return jsonify({
                'success': False,
                'stage': 'libreoffice-run',
                'message': 'LibreOffice timed out after 120s (workbook too large?).'
            }), 504
        except subprocess.CalledProcessError as e:
            shutil.rmtree(work_dir, ignore_errors=True)
            return jsonify({
                'success': False,
                'stage': 'libreoffice-run',
                'message': f'LibreOffice exited with code {e.returncode}.',
                'stderr': (e.stderr or '')[:2000]
            }), 500
        except Exception as e:
            shutil.rmtree(work_dir, ignore_errors=True)
            return jsonify({
                'success': False,
                'stage': 'libreoffice-run',
                'message': str(e)
            }), 500

    @app.route('/api/dataset/<dataset_id>/render-asset/<path:asset_path>', methods=['GET'])
    def render_dataset_asset(dataset_id, asset_path):
        directory = _RENDER_DIRS.get(str(dataset_id))
        if not directory or not os.path.isdir(directory):
            return jsonify({'success': False, 'message': 'No active render.'}), 404
        target = os.path.normpath(os.path.join(directory, asset_path))
        if not target.startswith(os.path.normpath(directory)):
            return jsonify({'success': False, 'message': 'Invalid asset path.'}), 400
        if not os.path.isfile(target):
            return jsonify({'success': False, 'message': 'Asset not found.'}), 404
        return send_file(target)