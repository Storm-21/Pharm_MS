"""
Database initialisation / rebuild utility for PharmacyMS.

Usage
-----
    python init_db.py                 # create schema + load authored data
    python init_db.py --reset         # DESTRUCTIVE: drop everything and reload
    python init_db.py --reseal-all    # re-seal all records (authorised change)
    python init_db.py --verify        # report integrity of every record

--reseal-all exists so that the creator can make a deliberate change to the
reference data and then re-issue the seals. That is the documented path for an
authorised modification. Editing the SQLite file by hand will instead show up
as TAMPERED.
"""

import argparse
import sys

from app import create_app, db
from app.models import Medicine
from app.data import ensure_seeded, DATA_VERSION, DATA_AUTHOR
from app.branding import branding_payload
from app.security import apply_seal, verify_all


def main():
    parser = argparse.ArgumentParser(description="PharmacyMS database initialisation")
    parser.add_argument('--reset', action='store_true',
                        help='DESTRUCTIVE: drop all tables and reload from source data')
    parser.add_argument('--reseal-all', action='store_true',
                        help='Recompute integrity seals for every medicine (authorised edit)')
    parser.add_argument('--verify', action='store_true',
                        help='Verify integrity of every medicine and exit')
    args = parser.parse_args()

    app = create_app()

    with app.app_context():
        if args.reset:
            print("!! --reset drops ALL data, including patients and prescriptions.")
            db.drop_all()
            db.create_all()
            print("Schema recreated.")

        if args.verify:
            report = verify_all(Medicine.query.all())
            print(f"Reference data version : {DATA_VERSION}")
            print(f"Data author            : {DATA_AUTHOR}")
            print(f"Records checked        : {report['total']}")
            print(f"Status counts          : {report['counts']}")
            if report['compromised']:
                print("")
                print("COMPROMISED RECORDS:")
                for item in report['compromised']:
                    print(f"  [{item['status']}] {item['name']} - {item['detail']}")
                return 1
            print("")
            print("All records intact.")
            return 0

        if args.reseal_all:
            count = 0
            for medicine in Medicine.query.all():
                apply_seal(medicine)
                count += 1
            db.session.commit()
            print(f"Re-sealed {count} medicine records.")
            return 0

        ensure_seeded(verbose=True)
        payload = branding_payload()
        print("")
        print(f"  {payload['app_name']} v{payload['app_version']}")
        print(f"  {payload['attribution']}")
        print(f"  identity integrity    : {'OK' if payload['integrity_ok'] else 'FAILED'}")
        print(f"  reference data version: {DATA_VERSION}")
        print("")
        print("Database ready.")
        return 0


if __name__ == '__main__':
    sys.exit(main())
