from flask import Flask, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import os
import sys

db = SQLAlchemy()


def _resolve_data_dir():
    """
    Where the SQLite database lives - always on this machine, never remote.

    Resolution order:
      1. PHARMS_DATA_DIR, if set (explicit override).
      2. LOCALAPPDATA\PharmMS when frozen - a stable per-user location that
         survives the executable being moved or replaced. Writing beside a copy
         sitting on the Desktop would scatter pharmacy.db into whatever folder
         the user happened to launch from.
      3. The package directory in development.

    If the preferred location cannot be created (locked-down machine, read-only
    profile) fall back to the executable's own folder rather than refusing to
    start.
    """
    override = os.environ.get('PHARMS_DATA_DIR')
    if override:
        os.makedirs(override, exist_ok=True)
        return override
    if getattr(sys, 'frozen', False):
        candidates = []
        local_appdata = os.environ.get('LOCALAPPDATA')
        if local_appdata:
            candidates.append(os.path.join(local_appdata, 'PharmMS'))
        candidates.append(os.path.dirname(os.path.abspath(sys.executable)))
        for candidate in candidates:
            try:
                os.makedirs(candidate, exist_ok=True)
                return candidate
            except OSError:
                continue
        return os.path.dirname(os.path.abspath(sys.executable))

    return os.path.abspath(os.path.dirname(__file__))


def _resolve_frontend_dir():
    """Locate the built React bundle (frontend/build), if present."""
    candidates = []
    if getattr(__import__('sys'), 'frozen', False):
        base = getattr(__import__('sys'), '_MEIPASS', None)
        if base:
            candidates.append(os.path.join(base, 'frontend_build'))
    here = os.path.abspath(os.path.dirname(__file__))
    candidates.append(os.path.join(os.path.dirname(os.path.dirname(here)), 'frontend', 'build'))
    for candidate in candidates:
        if os.path.isdir(candidate) and os.path.exists(os.path.join(candidate, 'index.html')):
            return candidate
    return None

def create_app():
    # static_folder=None disables Flask's built-in /static/<filename> route,
    # which would otherwise shadow the built React bundle's /static/* assets
    # served by serve_frontend below (and cause 404s for main.js / main.css).
    app = Flask(__name__, static_folder=None)

    # Database configuration
    data_dir = _resolve_data_dir()
    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(data_dir, 'pharmacy.db')}"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JSON_SORT_KEYS'] = False
    # Initialize extensions
    db.init_app(app)

    # CORS: the dev frontend runs on :3000; in a packaged build the UI is served
    # from this same origin, so only the dev origins need allowing.
    CORS(app, resources={r"/api/*": {"origins": [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]}})

    # Register blueprints
    from app.routes import (
        medicine_bp, patient_bp, prescription_bp, inventory_bp,
        recommender_bp, security_bp, storage_bp, branding_bp, report_bp,
    )
    app.register_blueprint(medicine_bp)
    app.register_blueprint(patient_bp)
    app.register_blueprint(prescription_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(recommender_bp)
    app.register_blueprint(security_bp)
    app.register_blueprint(storage_bp)
    app.register_blueprint(branding_bp)
    app.register_blueprint(report_bp)

    # Create tables, then bring in any authored reference data that is missing.
    # Running on every start makes the packaged .exe self-bootstrapping on a
    # fresh machine, while leaving an existing database untouched.
    with app.app_context():
        # Import the settings model so create_all() creates app_settings.
        from app import licensing  # noqa: F401
        db.create_all()
        # importing registers the AppSetting model before create_all in later versions
        try:
            from app.data import ensure_seeded
            ensure_seeded()
        except Exception as exc:  # never let seeding block the app from starting
            app.logger.warning('Reference data seeding skipped: %s', exc)

        # Keep a rolling local snapshot of the database so an accidental delete
        # or a bad edit can be rolled back. Best-effort: never block startup.
        try:
            from app.services import storage_service
            storage_service.create_snapshot('startup')
        except Exception as exc:
            app.logger.warning('Startup snapshot skipped: %s', exc)

    # Serve the built React UI when it exists (packaged / production mode).
    # Registered after the blueprints so /api/* always wins, and the catch-all
    # falls back to index.html so client-side routes survive a hard refresh.
    frontend_dir = _resolve_frontend_dir()
    if frontend_dir:
        @app.route('/', defaults={'path': ''})
        @app.route('/<path:path>')
        def serve_frontend(path):
            if path:
                candidate = os.path.join(frontend_dir, path)
                if os.path.isfile(candidate):
                    return send_from_directory(frontend_dir, path)
            return send_from_directory(frontend_dir, 'index.html')

        app.config['FRONTEND_SERVED'] = True
    else:
        app.config['FRONTEND_SERVED'] = False
    return app
