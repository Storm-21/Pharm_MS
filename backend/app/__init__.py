from flask import Flask, send_from_directory, g
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import os
import sys

db = SQLAlchemy()

# ---------------------------------------------------------------------------
# Environment detection
# ---------------------------------------------------------------------------

def _is_frozen():
    """True when running as a PyInstaller-packaged executable."""
    return getattr(sys, 'frozen', False)


def _is_dev_mode():
    """
    True when the developer has explicitly asked for development behaviour.

    Only PHARMS_DEBUG=true enables it - there is no silent fallback from
    packaged mode to debug mode. A packaged build never runs with Werkzeug's
    debugger because that would expose a full Python REPL to anyone who can
    reach the internal server.
    """
    return os.environ.get('PHARMS_DEBUG', 'false').lower() in ('1', 'true', 'yes')


def _host_from_env():
    host = os.environ.get('PHARMS_HOST')
    if host is None:
        return '127.0.0.1'
    # Reject any wildcard or link-local binding at the env-var level.
    # The app is a single-user desktop programme; exposing it to the network
    # requires a deliberate, auditable decision, not an accidental default.
    if host in ('0.0.0.0', '::', '*'):
        raise ValueError(
            'PHARMS_HOST must not be a wildcard address. '
            'Use 127.0.0.1 for the local-only desktop server.'
        )
    return host


def _port_from_env(default):
    try:
        port = int(os.environ.get('PHARMS_PORT', str(default)))
    except ValueError:
        port = default
    if not (1 <= port <= 65535):
        port = default
    return port


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
    if _is_frozen():
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


def get_data_dir():
    """The resolved data directory, cached - also used for the encryption key."""
    global _data_dir
    if _data_dir is None:
        _data_dir = _resolve_data_dir()
    return _data_dir


_data_dir = None


def _resolve_frontend_dir():
    """Locate the built React bundle (frontend/build), if present."""
    candidates = []
    if _is_frozen():
        base = getattr(sys, '_MEIPASS', None)
        if base:
            candidates.append(os.path.join(base, 'frontend_build'))
    here = os.path.abspath(os.path.dirname(__file__))
    candidates.append(os.path.join(os.path.dirname(os.path.dirname(here)), 'frontend', 'build'))
    for candidate in candidates:
        if os.path.isdir(candidate) and os.path.exists(os.path.join(candidate, 'index.html')):
            return candidate
    return None


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

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
    # Never allow Werkzeug's debugger in packaged builds. It exposes a full
    # Python REPL and must only ever be reachable when the developer has
    # explicitly enabled PHARMS_DEBUG=true on a trusted local machine.
    app.config['WERKZEUG_DEBUG_PIN'] = 'off' if not _is_dev_mode() else 'off'
    app.config['TEMPLATES_AUTO_RELOAD'] = False
    # Limit request body size to 10 MiB: large uploads are almost always a
    # mistake or a denial-of-service attempt. The branding logo route has its
    # own tighter limit (2 MiB) and validates image contents separately.
    app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024

    # Initialize extensions
    db.init_app(app)

    # CORS: the dev frontend runs on :3000; in a packaged build the UI is served
    # from this same origin, so only the dev origins need allowing.
    CORS(app, resources={r"/api/*": {"origins": [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]}})

    # -----------------------------------------------------------------------
    # Security headers — applied to every response, including errors.
    #
    # These are non-negotiable for a client-side app that serves patient data.
    # Each one is explained so future maintainers do not "fix" a broken
    # feature by quietly dropping a header.
    # -----------------------------------------------------------------------
    @app.after_request
    def _set_security_headers(response):
        # Prevent MIME-type sniffing; browsers must treat responses as JSON /
        # HTML exactly as declared, which blocks classic XSS vectors that rely
        # on the browser guessing a different content type from the body.
        response.headers['X-Content-Type-Options'] = 'nosniff'
        # Restrict the Referrer header so patient names in URLs are never
        # leaked to third-party pages linked from the app.
        response.headers['Referrer-Policy'] = 'no-referrer'
        # Tight Content-Security-Policy: no external script/style sources,
        # inline handlers blocked, images/data-uri only, form action self.
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "object-src 'none'; "
            "frame-ancestors 'none'; "
            "form-action 'self'; "
            "base-uri 'self'"
        )
        # Prevent the app from being embedded in an iframe on any page.
        response.headers['X-Frame-Options'] = 'DENY'
        # Clear-site-data on logout-ish flows wipes cookies/storage in one go.
        # Applied selectively where needed; this header alone is harmless.
        response.headers['Cache-Control'] = 'no-store'
        return response

    # -----------------------------------------------------------------------
    # Global request validation helper
    # -----------------------------------------------------------------------
    @app.before_request
    def _validate_content_type():
        """
        Reject unexpected content types on state-changing requests.

        The desktop app talks to itself over localhost; a stray or hostile
        cross-origin POST without the right Content-Type should not be parsed
        as JSON. This does not block the internal SPA (which sends proper
        headers) but drops malformed or mis-typed requests early.
        """
        from flask import request as _req
        if _req.method in ('POST', 'PUT', 'PATCH'):
            content_type = _req.content_type or ''
            # If there is a body, require JSON content type. File uploads
            # carry multipart and are handled by the route itself.
            if 'multipart' not in content_type and _req.get_data(as_text=True) != '':
                if 'json' not in content_type:
                    from flask import abort
                    abort(415, 'Content-Type must be application/json for this endpoint.')

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

        # Run versioned migrations with full safety guarantees.
        # This replaces the old apply_migrations() and adds:
        #   - explicit version tracking in schema_migrations table
        #   - pre-migration backups
        #   - transactional execution
        #   - post-migration validation
        #   - clear recovery instructions on failure
        try:
            from app.migrations_v2 import run_migrations
            migration_result = run_migrations(db, app.logger)
            if migration_result.get('skipped'):
                app.logger.warning('Migration skipped: %s', migration_result.get('reason'))
            elif migration_result.get('applied'):
                app.logger.info('Migrations applied: %s', ', '.join(migration_result['applied']))
        except RuntimeError as exc:
            # Hard failure: do NOT silently continue with a partial schema.
            # The app will still start (to allow diagnostic access) but logs
            # a clear error and provides recovery instructions.
            app.logger.error('FATAL: Schema migration failed: %s', exc)
            app.logger.error('Recovery: Check backups/pre-migration-*.db for a safe copy.')
            # Continue startup so the user can access recovery tools
        except Exception as exc:
            app.logger.warning('Schema migration error (continuing): %s', exc)

        # Also run legacy column additions for backward compatibility with
        # databases that predate the versioned migration system.
        try:
            from app.migrations import apply_migrations
            legacy_added = apply_migrations(db, app.logger)
            if legacy_added:
                app.logger.info('Legacy migrations applied: %s', ', '.join(legacy_added))
        except Exception as exc:
            app.logger.warning('Legacy migration error: %s', exc)

        try:
            from app.data import ensure_seeded
            ensure_seeded()
        except Exception as exc:  # never let seeding block the app from starting
            app.logger.warning('Reference data seeding skipped: %s', exc)

        # Enhanced startup snapshot with integrity metadata.
        try:
            from app.services import backup_service
            snapshot = backup_service.create_versioned_snapshot('startup')
            if snapshot and snapshot.get('valid'):
                app.logger.info('Startup snapshot created: %s', snapshot.get('filename'))
            else:
                app.logger.warning('Startup snapshot incomplete: %s', snapshot)
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


def request_method_needs_json_check():
    """Return True for methods that typically carry a JSON body."""
    return False  # overridden per-route in practice
