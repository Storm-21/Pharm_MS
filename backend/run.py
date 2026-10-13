"""
PharmMS development entry point.

For production or packaged desktop use, start the app via desktop_app.py or
the generated PharmMS.exe instead. This module is intentionally conservative:
debug mode and wildcard hosts are never enabled here without an explicit
environment variable, because accidentally publishing the dev server on 0.0.0.0
would expose every patient record on the local network.
"""
import os

from app import create_app

app = create_app()

# Prevent accidental exposure when this module is run directly.
# The desktop app forces 127.0.0.1 and debug=False; this file must not be more
# permissive by default.
_HOST = os.environ.get('PHARMS_HOST', '127.0.0.1')
_PORT = int(os.environ.get('PHARMS_PORT', '5000'))
_DEBUG = os.environ.get('PHARMS_DEBUG', 'false').lower() in ('1', 'true', 'yes')

if __name__ == '__main__':
    app.run(debug=_DEBUG, host=_HOST, port=_PORT)
