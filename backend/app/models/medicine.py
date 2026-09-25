from app import db
from datetime import datetime

class Medicine(db.Model):
    __tablename__ = 'medicines'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, unique=True)
    generic_name = db.Column(db.String(150), nullable=False)
    brand_name = db.Column(db.String(150), nullable=True)

    # --- Manufacturer details -------------------------------------------------
    manufacturer = db.Column(db.String(200), nullable=False)
    manufacturer_country = db.Column(db.String(100), nullable=True)
    manufacturer_site = db.Column(db.String(200), nullable=True)        # plant / site
    manufacturer_licence_no = db.Column(db.String(100), nullable=True)  # drug licence no.
    marketed_by = db.Column(db.String(200), nullable=True)
    country_origin = db.Column(db.String(100), nullable=True)

    # Composition / chemistry
    salt_composition = db.Column(db.String(500), nullable=False)  # e.g., "Paracetamol 500mg"
    molecular_formula = db.Column(db.String(200), nullable=True)       # e.g., C8H9NO2
    chemical_formula_weight = db.Column(db.String(60), nullable=True)  # g/mol
    strength = db.Column(db.String(100), nullable=False)  # e.g., "500mg"
    form = db.Column(db.String(50), nullable=False)  # e.g., "tablet", "syrup", "injection"
    route_of_administration = db.Column(db.String(120), nullable=True)

    # Classification
    therapeutic_class = db.Column(db.String(200), nullable=True)
    pharmacological_class = db.Column(db.String(200), nullable=True)

    # Medical information
    use_case = db.Column(db.Text, nullable=False)
    mechanism_of_action = db.Column(db.Text, nullable=True)
    side_effects = db.Column(db.Text, nullable=True)
    contraindications = db.Column(db.Text, nullable=True)
    warnings = db.Column(db.Text, nullable=True)
    drug_interactions = db.Column(db.Text, nullable=True)
    food_interactions = db.Column(db.Text, nullable=True)
    pregnancy_category = db.Column(db.String(120), nullable=True)

    # Pharmacokinetics
    onset_of_action = db.Column(db.String(120), nullable=True)
    half_life = db.Column(db.String(120), nullable=True)
    bioavailability = db.Column(db.String(120), nullable=True)
    protein_binding = db.Column(db.String(120), nullable=True)
    metabolism = db.Column(db.String(200), nullable=True)
    excretion = db.Column(db.String(200), nullable=True)

    # Dosing envelope
    max_daily_dose = db.Column(db.String(150), nullable=True)

    # Pharmacopoeia cross-references
    indian_pharmacopoeia_ref = db.Column(db.String(250), nullable=True)
    global_pharmacopoeia_ref = db.Column(db.String(250), nullable=True)
    pharmacopoeia_monograph = db.Column(db.Text, nullable=True)
    ip_status = db.Column(db.String(200), nullable=True)

    # Regulatory (India)
    schedule_classification = db.Column(db.String(150), nullable=True)
    hsn_code = db.Column(db.String(30), nullable=True)
    gst_rate = db.Column(db.String(20), nullable=True)
    barcode = db.Column(db.String(60), nullable=True)

    # Pricing
    cost_price = db.Column(db.Float, nullable=False)
    selling_price = db.Column(db.Float, nullable=False)

    # Additional info
    requires_prescription = db.Column(db.Boolean, default=True)
    storage_temp = db.Column(db.String(100), nullable=True)
    expiry_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # --- Image / pack shot ----------------------------------------------------
    # A local file name inside the data directory's medicines/ folder. Stored as
    # a NAME, not a path, for two reasons: the data directory moves between
    # machines (LOCALAPPDATA differs per user), and a stored absolute path would
    # be a path-traversal vector the moment it is used to serve a file.
    #
    # image_source records where it came from - 'upload', 'fetch', or 'url' -
    # so an image pulled from the web is distinguishable from one the pharmacy
    # supplied, and image_attribution keeps the credit line that a fetched image
    # may require.
    image_filename = db.Column(db.String(200), nullable=True)
    image_source = db.Column(db.String(40), nullable=True)
    image_attribution = db.Column(db.String(300), nullable=True)
    image_fetched_at = db.Column(db.DateTime, nullable=True)

    # Integrity seal - see app/security.py
    record_hash = db.Column(db.String(128), nullable=True)
    content_seal = db.Column(db.String(128), nullable=True)

    # Relationships
    inventory = db.relationship('Inventory', backref='medicine', lazy=True, cascade='all, delete-orphan')
    prescription_items = db.relationship('PrescriptionItem', backref='medicine', lazy=True)
    dosage_guides = db.relationship('DosageGuide', backref='medicine', lazy=True, cascade='all, delete-orphan')

    def to_dict(self, include_seal=False):
        data = {
            'id': self.id,
            'name': self.name,
            'generic_name': self.generic_name,
            'brand_name': self.brand_name,
            'manufacturer': self.manufacturer,
            'manufacturer_country': self.manufacturer_country,
            'manufacturer_site': self.manufacturer_site,
            'manufacturer_licence_no': self.manufacturer_licence_no,
            'marketed_by': self.marketed_by,
            'country_origin': self.country_origin,
            'salt_composition': self.salt_composition,
            'molecular_formula': self.molecular_formula,
            'chemical_formula_weight': self.chemical_formula_weight,
            'strength': self.strength,
            'form': self.form,
            'route_of_administration': self.route_of_administration,
            'therapeutic_class': self.therapeutic_class,
            'pharmacological_class': self.pharmacological_class,
            'use_case': self.use_case,
            'mechanism_of_action': self.mechanism_of_action,
            'side_effects': self.side_effects,
            'contraindications': self.contraindications,
            'warnings': self.warnings,
            'drug_interactions': self.drug_interactions,
            'food_interactions': self.food_interactions,
            'pregnancy_category': self.pregnancy_category,
            'onset_of_action': self.onset_of_action,
            'half_life': self.half_life,
            'bioavailability': self.bioavailability,
            'protein_binding': self.protein_binding,
            'metabolism': self.metabolism,
            'excretion': self.excretion,
            'max_daily_dose': self.max_daily_dose,
            'indian_pharmacopoeia_ref': self.indian_pharmacopoeia_ref,
            'global_pharmacopoeia_ref': self.global_pharmacopoeia_ref,
            'pharmacopoeia_monograph': self.pharmacopoeia_monograph,
            'ip_status': self.ip_status,
            'schedule_classification': self.schedule_classification,
            'hsn_code': self.hsn_code,
            'gst_rate': self.gst_rate,
            'barcode': self.barcode,
            'cost_price': self.cost_price,
            'selling_price': self.selling_price,
            'requires_prescription': self.requires_prescription,
            'storage_temp': self.storage_temp,
            'expiry_date': self.expiry_date.isoformat() if self.expiry_date else None,
            'has_image': bool(self.image_filename),
            'image_source': self.image_source,
            'image_attribution': self.image_attribution,
        }
        if include_seal:
            data['record_hash'] = self.record_hash
            data['content_seal'] = self.content_seal
        return data
    
    def __repr__(self):
        return f'<Medicine {self.name}>'
