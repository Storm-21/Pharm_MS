"""
Optional live reference lookup.

WHAT THIS IS FOR
----------------
The authored reference set is a curated dispensing set - around 80 medicines
with full monographs. When a pharmacist looks up something outside it, the
useful answer is "here is the label data, fetched from the regulator's public
database" rather than "not found".

DATA SOURCE
-----------
openFDA drug labelling endpoint (api.fda.gov/drug/label). It is a public,
government-operated API covering FDA-approved product labelling. No key is
required, the responses are JSON, and the fields map directly onto what a
pharmacy needs: boxed warnings, contraindications, interactions, dosage.

WHY IT IS OPT-IN AND OFF BY DEFAULT
-----------------------------------
This application advertises itself as fully offline, and that claim is load
bearing: a pharmacy counter may have no usable connection, and patient data
must never leave the machine. So:

  * the feature is disabled unless explicitly switched on in Data settings
  * only the drug *name* is ever sent - never a patient identifier, never a
    record from the local database
  * every call is cached on disk, so a drug fetched once works offline
  * when the network is unavailable the cache is used, and when there is no
    cached copy the caller is told plainly that live data is unavailable
    rather than being given an empty answer that looks like "no warnings"

THE SAFETY RULE
---------------
Data fetched from here is *reference material*, never a recommendation. It is
stored as a monograph and displayed for a human to read. It is deliberately
NOT fed into the recommender's ranking, because a label written for a
different regulatory jurisdiction is not a substitute for the curated,
safety-screened set that the recommendation engine relies on.
"""

import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request

# openFDA asks callers to identify themselves and to stay within reasonable
# request rates. These are honoured rather than worked around.
USER_AGENT = 'PharmMS/3.0 (pharmacy management; offline-first; contact: local user)'
BASE_URL = 'https://api.fda.gov/drug/label.json'

# Seconds to wait between live requests. openFDA allows 240 requests per minute
# without a key for most endpoints; 1.5 s keeps well under that and is far
# faster than a human types.
MIN_INTERVAL_SECONDS = 1.5

# Cache lifetime. Label data changes rarely, and a stale monograph is better
# than no monograph at a counter with no connection.
CACHE_MAX_AGE_DAYS = 90


class LiveReference:
    """Fetch and cache drug label data from the openFDA public API."""

    _last_request_at = 0.0

    # ------------------------------------------------------------------ #
    # Cache
    # ------------------------------------------------------------------ #

    @staticmethod
    def _cache_dir():
        """Where fetched monographs are kept.

        Lives beside the database in %LOCALAPPDATA%, not in the program
        folder, so upgrading or reinstalling never discards the cache.
        """
        base = os.environ.get('PHARMS_DATA_DIR')
        if not base:
            base = os.path.join(
                os.environ.get('LOCALAPPDATA') or os.path.expanduser('~'),
                'PharmMS')
        path = os.path.join(base, 'reference_cache')
        try:
            os.makedirs(path, exist_ok=True)
        except Exception:
            return None
        return path

    @staticmethod
    def _cache_path(drug_name):
        safe = re.sub(r'[^a-z0-9]+', '_', (drug_name or '').lower()).strip('_')
        directory = LiveReference._cache_dir()
        if not directory or not safe:
            return None
        return os.path.join(directory, '%s.json' % safe[:80])

    @staticmethod
    def read_cache(drug_name):
        """Cached monograph, or None. Includes its age in days."""
        path = LiveReference._cache_path(drug_name)
        if not path or not os.path.exists(path):
            return None
        try:
            with open(path, 'r', encoding='utf-8') as handle:
                payload = json.load(handle)
        except Exception:
            return None
        fetched = payload.get('_fetched_at') or 0
        payload['_cache_age_days'] = round(
            (time.time() - fetched) / 86400.0, 1) if fetched else None
        payload['_from_cache'] = True
        return payload

    @staticmethod
    def write_cache(drug_name, payload):
        path = LiveReference._cache_path(drug_name)
        if not path:
            return False
        try:
            payload = dict(payload)
            payload['_fetched_at'] = time.time()
            with open(path, 'w', encoding='utf-8') as handle:
                json.dump(payload, handle, ensure_ascii=False)
            return True
        except Exception:
            return False

    @staticmethod
    def cache_stats():
        """How many monographs are cached, for the settings screen."""
        directory = LiveReference._cache_dir()
        if not directory:
            return {'count': 0, 'path': None}
        try:
            files = [f for f in os.listdir(directory) if f.endswith('.json')]
        except Exception:
            files = []
        return {'count': len(files), 'path': directory}

    @staticmethod
    def clear_cache():
        directory = LiveReference._cache_dir()
        if not directory:
            return 0
        removed = 0
        try:
            for name in os.listdir(directory):
                if name.endswith('.json'):
                    os.remove(os.path.join(directory, name))
                    removed += 1
        except Exception:
            pass
        return removed

    # ------------------------------------------------------------------ #
    # Live fetch
    # ------------------------------------------------------------------ #

    @staticmethod
    def _throttle():
        """Keep requests under the published rate so the API stays usable."""
        elapsed = time.time() - LiveReference._last_request_at
        if elapsed < MIN_INTERVAL_SECONDS:
            time.sleep(MIN_INTERVAL_SECONDS - elapsed)
        LiveReference._last_request_at = time.time()

    @staticmethod
    def _clean(text):
        """Collapse label whitespace into readable sentences."""
        if not text:
            return None
        if isinstance(text, list):
            text = ' '.join(str(part) for part in text)
        text = re.sub(r'\s+', ' ', str(text)).strip()
        return text or None

    @staticmethod
    def _matches_drug(record, generic_name):
        """
        Confirm the returned label is actually for the drug we asked about.

        openFDA returns combination products and loosely-matched brands - a
        query for 'metformin' came back with a metformin/sitagliptin
        combination. Presenting that as the metformin monograph would be wrong,
        so the active ingredients are compared before the record is accepted.
        """
        wanted = re.sub(r'[^a-z0-9]+', '', (generic_name or '').lower())
        if not wanted:
            return False
        openfda = record.get('openfda') or {}

        # Collect the active ingredients. `substance_name` lists them
        # individually when the API provides it; when it does not, the
        # `generic_name` list is the fallback because a combination product is
        # reported there as several entries ('METFORMIN HYDROCHLORIDE' and
        # 'SITAGLIPTIN PHOSPHATE'), whereas a single-ingredient product has
        # one entry.
        substances = openfda.get('substance_name')
        if not substances:
            substances = openfda.get('generic_name')
        if isinstance(substances, str):
            substances = [substances]
        substances = [re.sub(r'[^a-z0-9]+', '', str(s).lower())
                      for s in (substances or [])]
        substances = [s for s in substances if s]

        # Reject any combination product. A label is only a match when the
        # requested drug is the product's sole active ingredient: returning a
        # metformin/sitagliptin label for a query about metformin would
        # attribute a second drug's warnings and interactions to plain
        # metformin, which is exactly the misattribution this module exists to
        # prevent. Erring toward rejection is correct here - a missing
        # monograph is harmless, a wrong one is not.
        if len(substances) > 1:
            return False
        candidates = []
        for field in ('generic_name', 'substance_name', 'brand_name'):
            value = openfda.get(field)
            if isinstance(value, list):
                candidates.extend(str(v) for v in value)
            elif value:
                candidates.append(str(value))

        for name in candidates:
            cleaned = re.sub(r'[^a-z0-9]+', '', name.lower())
            if not cleaned:
                continue
            # Accept when one is a prefix of the other, which covers
            # 'metformin' against 'metformin hydrochloride'. A prefix test is
            # used rather than a substring test so that 'metformin' does not
            # match an unrelated name that merely contains the letters.
            if cleaned.startswith(wanted) or wanted.startswith(cleaned):
                return True
        return False

    @staticmethod
    def fetch_monograph(drug_name, force=False):
        """
        Look up a drug. Returns (payload, error).

        Order of operations:
          1. A fresh cache entry is returned immediately - no network needed.
          2. Otherwise the live API is queried and the result cached.
          3. If the network fails, a stale cache entry is used if one exists.
          4. With neither, an explicit error is returned. The caller must not
             treat "no data" as "no warnings".
        """
        if not drug_name or not str(drug_name).strip():
            return None, 'A drug name is required.'

        drug_name = str(drug_name).strip()

        # --- 1. Fresh cache ------------------------------------------------
        if not force:
            cached = LiveReference.read_cache(drug_name)
            age = cached.get('_cache_age_days') if cached else None
            if cached and age is not None and age <= CACHE_MAX_AGE_DAYS:
                return cached, None

        # --- 2. Live query --------------------------------------------------
        params = urllib.parse.urlencode({
            'search': 'openfda.generic_name:"%s"' % drug_name,
            'limit': 5,
        })
        url = '%s?%s' % (BASE_URL, params)
        request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})

        try:
            LiveReference._throttle()
            with urllib.request.urlopen(request, timeout=20) as response:
                body = response.read().decode('utf-8')
            data = json.loads(body)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                # openFDA returns 404 for "no matching record", which is a
                # legitimate answer, not a failure.
                payload = {'drug_name': drug_name, 'found': False,
                           'source': 'openFDA drug labelling', 'url': url}
                LiveReference.write_cache(drug_name, payload)
                return payload, None
            cached = LiveReference.read_cache(drug_name)
            if cached:
                cached['_stale_fallback'] = True
                return cached, None
            return None, ('The reference service returned HTTP %s. '
                          'Live lookup unavailable.' % exc.code)
        except Exception as exc:
            # --- 3. Stale cache is better than nothing ----------------------
            cached = LiveReference.read_cache(drug_name)
            if cached:
                cached['_stale_fallback'] = True
                return cached, None
            return None, ('Live lookup unavailable (%s). The application '
                          'continues to work offline; only this optional '
                          'lookup is affected.' % type(exc).__name__)

        # --- Parse ----------------------------------------------------------
        results = data.get('results') or []
        record = None
        for candidate in results:
            if LiveReference._matches_drug(candidate, drug_name):
                record = candidate
                break

        if record is None:
            payload = {'drug_name': drug_name, 'found': False,
                       'source': 'openFDA drug labelling', 'url': url,
                       'note': ('No label whose active ingredient matches "%s" '
                                'was found.' % drug_name)}
            LiveReference.write_cache(drug_name, payload)
            return payload, None

        openfda = record.get('openfda') or {}

        def first(field):
            value = openfda.get(field)
            if isinstance(value, list):
                return value[0] if value else None
            return value

        payload = {
            'drug_name': drug_name,
            'found': True,
            'source': 'openFDA drug labelling (FDA-approved product labels)',
            'source_url': 'https://open.fda.gov/apis/drug/label/',
            'query_url': url,
            'generic_name': first('generic_name'),
            'brand_name': first('brand_name'),
            'manufacturer': first('manufacturer_name'),
            'route': first('route'),
            'product_type': first('product_type'),
            # The clinically important fields, kept under names that match the
            # local Medicine model so the two can be shown side by side.
            'boxed_warning': LiveReference._clean(record.get('boxed_warning')),
            'warnings': LiveReference._clean(
                record.get('warnings_and_cautions')
                or record.get('warnings')),
            'contraindications': LiveReference._clean(record.get('contraindications')),
            'drug_interactions': LiveReference._clean(record.get('drug_interactions')),
            'adverse_reactions': LiveReference._clean(record.get('adverse_reactions')),
            'dosage_and_administration': LiveReference._clean(
                record.get('dosage_and_administration')),
            'indications_and_usage': LiveReference._clean(
                record.get('indications_and_usage')),
            'pregnancy': LiveReference._clean(
                record.get('pregnancy') or record.get('use_in_specific_populations')),
            'pediatric_use': LiveReference._clean(record.get('pediatric_use')),
            'geriatric_use': LiveReference._clean(record.get('geriatric_use')),
            'effective_date': record.get('effective_time'),
            'disclaimer': (
                'Reference material from FDA product labelling. Not a '
                'recommendation. Verify against the current Indian '
                'Pharmacopoeia and the manufacturer\'s own labelling before '
                'acting on it.'
            ),
        }
        LiveReference.write_cache(drug_name, payload)
        return payload, None

    # ------------------------------------------------------------------ #
    # Applying fetched data
    # ------------------------------------------------------------------ #

    @staticmethod
    def enrich_medicine(medicine, force=False):
        """
        Fill in missing monograph fields on a local medicine from live data.

        Only ever *adds* to a record that has a gap. An authored value is never
        overwritten with a fetched one: the local set is curated and
        safety-reviewed, the fetched text is not, so the curated value wins
        every conflict.
        """
        payload, error = LiveReference.fetch_monograph(
            medicine.generic_name or medicine.name, force=force)
        if error or not payload or not payload.get('found'):
            return None, error or 'No matching label found.'

        from app import db
        from datetime import datetime
        filled = []

        # Map a fetched field onto a local column, only when the local column
        # is empty.
        mapping = [
            ('contraindications', 'contraindications'),
            ('warnings', 'warnings'),
            ('drug_interactions', 'drug_interactions'),
            ('indications_and_usage', 'use_case'),
            ('adverse_reactions', 'side_effects'),
        ]
        for source_field, column in mapping:
            value = payload.get(source_field)
            if value and not getattr(medicine, column, None):
                setattr(medicine, column, value)
                filled.append(column)

        if filled:
            medicine.data_source = payload.get('source')
            medicine.data_fetched_at = datetime.utcnow()
            db.session.commit()
        return {'filled_fields': filled, 'payload': payload}, None
