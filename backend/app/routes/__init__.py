# Routes module
from .medicine_routes import medicine_bp
from .patient_routes import patient_bp
from .prescription_routes import prescription_bp
from .inventory_routes import inventory_bp
from .recommender_routes import recommender_bp
from .security_routes import security_bp
from .storage_routes import storage_bp
from .branding_routes import branding_bp
from .report_routes import report_bp
__all__ = [
    'medicine_bp',
    'patient_bp',
    'prescription_bp',
    'inventory_bp',
    'recommender_bp',
    'security_bp',
    'storage_bp',
    'branding_bp',
    'report_bp'
]
