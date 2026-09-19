"""
PharmMS desktop application.

Runs the Flask backend in-process, serves the bundled React UI, and presents it
in a native window via the Windows WebView2 runtime (through pywebview). No
browser tab, no console window, no internet connection.

Architecture
------------
    main thread        : native window + WebView2
    background thread  : Werkzeug HTTP server on 127.0.0.1

The window loads http://127.0.0.1:<port> only after the socket is accepting, so
the WebView never shows a connection error.

Fallback chain, because a desktop app that refuses to start is worse than an
imperfect one:
    1. pywebview window (WebView2, then the legacy MSHTML renderer)
    2. the system default browser, if no GUI backend is available at all

Closing the window shuts the server down; the process does not linger.
"""

import logging
import os
import socket
import sys
import threading
import time
import webbrowser
if getattr(sys, 'frozen', False):
    sys.path.insert(0, getattr(sys, '_MEIPASS', os.path.dirname(sys.executable)))

from app import create_app  # noqa: E402

HOST = '127.0.0.1'
PREFERRED_PORT = 5000
WINDOW_TITLE = 'Pharmacy Management System'
WINDOW_SIZE = (1360, 900)
WINDOW_MIN_SIZE = (1024, 700)


def _port_is_free(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, port)) != 0


def _find_free_port(host, preferred):
    """
    Use the preferred port if available, otherwise any free port.

    Falling back rather than failing matters here: a user should not be blocked
    from opening their pharmacy records because something else holds 5000.
    """
    if _port_is_free(host, preferred):
        return preferred
    for candidate in range(preferred + 1, preferred + 40):
        if _port_is_free(host, candidate):
            return candidate
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return sock.getsockname()[1]


def _wait_for_server(host, port, timeout=45):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not _port_is_free(host, port):
            return True
        time.sleep(0.2)
    return False


def _start_server(app, port):
    def run():
        # Werkzeug's request logging is noise in a desktop app, and the banner
        # is invisible anyway with no console attached.
        logging.getLogger('werkzeug').setLevel(logging.ERROR)
        app.run(host=HOST, port=port, debug=False, use_reloader=False, threaded=True)

    thread = threading.Thread(target=run, daemon=True, name='pharms-server')
    thread.start()
    return thread


def _startup_report(app):
    """Print attribution and the integrity result (visible only if a console exists)."""
    from app.branding import branding_payload
    from app.data import DATA_VERSION

    payload = branding_payload()
    line = '=' * 62
    print(line)
    print(f"  {payload['app_name']}  v{payload['app_version']}")
    print(f"  {payload['attribution']}")
    print(line)
    try:
        with app.app_context():
            from app.models import Medicine
            from app.security import verify_all
            report = verify_all(Medicine.query.all())
            state = 'VERIFIED' if report['ok'] else 'FAILED'
            print(f"  Creator identity : "
                  f"{'verified' if payload['integrity_ok'] else 'NOT VERIFIED'}")
            print(f"  Reference data   : {state} "
                  f"({report['counts'].get('INTACT', 0)}/{report['total']} intact)")
            if not report['ok']:
                for item in report['compromised'][:5]:
                    print(f"    [{item['status']}] {item['name']}")
            print(f"  Data version     : {DATA_VERSION}")
    except Exception as exc:
        print(f"  Integrity check  : could not run ({exc})")
    print(line)


def _data_folder(app):
    try:
        with app.app_context():
            from app.services import storage_service
            return storage_service.database_info()['data_directory']
    except Exception:
        return 'unknown'


def run_window(port):
    """
    Present the UI in a native window.

    Tries WebView2 first (Chromium-based, already present on Windows 10/11 via
    the Edge runtime), then the legacy MSHTML renderer. Returns True if a window
    was actually shown and closed by the user.
    """
    try:
        import webview
    except ImportError as exc:
        print(f"pywebview not available ({exc}).")
        return False

    url = f'http://{HOST}:{port}'

    for gui in ('edgechromium', 'mshtml'):
        try:
            webview.create_window(
                WINDOW_TITLE,
                url,
                width=WINDOW_SIZE[0],
                height=WINDOW_SIZE[1],
                min_size=WINDOW_MIN_SIZE,
                text_select=True,
            )
            webview.start(gui=gui, debug=False)
            return True
        except Exception as exc:
            print(f"Window backend '{gui}' failed: {exc}")

    return False


def run_browser(port):
    """Last-resort fallback: open the system browser and stay alive."""
    url = f'http://{HOST}:{port}'
    print(f"  No native window available. Opening {url} in your default browser.")
    try:
        webbrowser.open(url)
    except Exception:
        print(f"  Could not launch a browser. Open {url} manually.")
    print("  Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print('\nShutdown requested.')
    return True


def main():
    app = create_app()
    _startup_report(app)

    port = _find_free_port(HOST, PREFERRED_PORT)
    _start_server(app, port)

    if not _wait_for_server(HOST, port):
        print("The internal server did not start. Exiting.")
        if getattr(sys, 'frozen', False):
            input('Press Enter to close...')
        return 1

    print(f"  Data folder      : {_data_folder(app)}")
    print(f"  Serving at       : http://{HOST}:{port}")
    print("  Close the window to quit.")
    print('=' * 62)

    if run_window(port):
        return 0

    run_browser(port)
    return 0


if __name__ == '__main__':
    sys.exit(main())
