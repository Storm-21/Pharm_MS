"""
Pharmacy Management System (PharmMS)
Quick Start Guide
"""

# ============================================
# BACKEND SETUP
# ============================================

# 1. Navigate to backend
cd backend

# 2. Create virtual environment
python -m venv venv

# 3. Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Initialize database with sample data
python init_db.py

# 6. Run Flask server (runs on http://localhost:5000)
python run.py

# ============================================
# FRONTEND SETUP (in a new terminal)
# ============================================

# 1. Navigate to frontend
cd frontend

# 2. Install npm dependencies
npm install

# 3. Start React development server (runs on http://localhost:3000)
npm start

# ============================================
# SYSTEM IS NOW READY!
# ============================================

# Frontend: http://localhost:3000
# Backend API: http://localhost:5000/api

# ============================================
# KEY FEATURES TO TRY
# ============================================

# 1. MEDICINE DATABASE
#    - Navigate to "Medicine Database"
#    - Search for medicines like "Paracetamol" or "Aspirin"
#    - View medicine details, composition, uses
#    - Add new medicines

# 2. DOSAGE CALCULATOR
#    - Go to "Dosage Calculator"
#    - Enter Patient ID: 1, Medicine ID: 1
#    - Add condition: "Fever"
#    - See calculated dosage, total amount needed, and drug cycle info
#    - Automatically checks for allergies and contraindications

# 3. MEDICINE RECOMMENDER
#    - Navigate to "Medicine Recommender"
#    - Enter Patient ID: 1
#    - Enter condition: "Fever" or "Bacterial Infection"
#    - Select severity level
#    - Get top 5 recommended medicines with scores
#    - View similar past cases for reference

# 4. INVENTORY MANAGEMENT
#    - Go to "Inventory" section
#    - View stock status and alerts
#    - Add new stock with batch details
#    - Update quantities
#    - Monitor expiry dates

# ============================================
# SAMPLE DATA AVAILABLE
# ============================================

# 8 Medicines pre-loaded:
# 1. Paracetamol 500mg
# 2. Amoxicillin 500mg
# 3. Ibuprofen 200mg
# 4. Metformin 500mg
# 5. Aspirin 75mg
# 6. Omeprazole 20mg
# 7. Lisinopril 10mg
# 8. Atorvastatin 10mg

# ============================================
# API TESTING
# ============================================

# Test with curl or Postman:

# Get all medicines:
# curl http://localhost:5000/api/medicines

# Calculate dosage:
# curl -X POST http://localhost:5000/api/recommender/dosage \
#   -H "Content-Type: application/json" \
#   -d '{"patient_id": 1, "medicine_id": 1, "condition": "Fever"}'

# Get recommendations:
# curl -X POST http://localhost:5000/api/recommender/recommend-medicines \
#   -H "Content-Type: application/json" \
#   -d '{"patient_id": 1, "condition": "Fever", "severity": "mild"}'

# ============================================
# TROUBLESHOOTING
# ============================================

# Q: Port 5000 already in use?
# A: Change port in backend/run.py or kill existing process

# Q: CORS errors in frontend?
# A: Make sure backend server is running (http://localhost:5000)

# Q: Database not found?
# A: Run "python init_db.py" in backend directory

# Q: npm install fails?
# A: Try "npm install --legacy-peer-deps"

# Q: Frontend won't start?
# A: Check if port 3000 is available, install Node.js if not installed

# ============================================
# NEXT STEPS
# ============================================

# 1. Add real patient data to test patient features
# 2. Add more medicines to the database
# 3. Create prescriptions linking patients to medicines
# 4. Test the recommender with multiple patients
# 5. Monitor inventory alerts and update stock
# 6. Customize dosage guides for specific medicines
# 7. Deploy backend to cloud (Heroku, AWS, etc.)
# 8. Deploy frontend to CDN (Vercel, Netlify, etc.)

# ============================================
# DOCUMENTATION
# ============================================

# For complete documentation, see README.md
# For API documentation, check the API endpoints section in README.md

print("✓ Pharmacy Management System is ready to use!")
print("✓ Backend: http://localhost:5000")
print("✓ Frontend: http://localhost:3000")
print("✓ Enjoy managing your pharmacy!")
