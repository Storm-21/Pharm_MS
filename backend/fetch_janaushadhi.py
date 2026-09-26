"""
Fetch the real Jan Aushadhi (PMBJP) product catalogue.

WHY THIS EXISTS
---------------
The curated catalogue in app/data/ is a verified *dispensing* set, but a user
reasonably asked why only ~100 medicines were visible when India markets very
many more. The honest answer to that is to load a real government-sourced
catalogue rather than to generate entries, because generating them would mean
inventing the clinical fields - and an invented contraindication is
indistinguishable on screen from a real one.

SOURCE
------
janaushadhistore.in publishes the Jan Aushadhi (Pradhan Mantri Bhartiya
Janaushadhi Pariyojana) product list with the generic name, the full salt
composition and the price. It is a real operating Jan Aushadhi Kendra's
catalogue of PMBJP products.

WHAT IT PROVIDES AND WHAT IT DOES NOT
--------------------------------------
It provides, per product: the trade name, the salt composition (the generic
ingredients and strengths), the dosage form, and a price.

It does NOT provide mechanism of action, half-life, pregnancy category,
contraindications or drug interactions - those are clinical fields, and this
scraper does not invent them. Imported rows are therefore marked
`data_source = 'Jan Aushadhi (PMBJP)'` and carry only what the source actually
states, so an imported row is distinguishable at a glance from a curated one.
Records that need the clinical detail can be enriched individually from the
medicine detail screen, or through import_medicines.py with a fuller source.

Politeness and correctness
--------------------------
Pages are fetched sequentially with a delay, and the HTML is parsed with a
regex over the product listing rather than a full DOM library, so this script
has no dependencies beyond the standard library. It is resumable: the raw
responses are written to a cache directory, so a re-run does not refetch.

Run:  python fetch_janaushadhi.py            # fetch and write the CSV
      python fetch_janaushadhi.py --pages 3  # only the first 3 pages
      python fetch_janaushadhi.py --from-cache
"""

import argparse
import csv
import html
import os
import re
import sys
import time
import urllib.request

BASE = 'https://janaushadhistore.in/product-category/jan-aushadhi/'
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'build',
                     'janaushadhi')
OUT_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       'janaushadhi_catalogue.csv')

# The listing is a WooCommerce "product-small" grid. Each card carries the
# full product name in an aria-label on the product link, and the composition
# in a `product_tag-...` class. Both are stable, machine-readable attributes
# rather than display text, which makes them a much safer thing to parse than
# the rendered layout.
#
# Prices are deliberately NOT parsed: the store renders them with JavaScript, so
# they are absent from the HTML. Rather than guess a price, the importer records
# none and the row is flagged as needing one. A made-up price on a stock system
# is worse than a blank field.
PRODUCT_RE = re.compile(
    r'product_tag-([a-z0-9\-]+)[^>]*>.*?'
    r'<a\s+href="([^"]+)"\s+aria-label="([^"]+)"',
    re.S)

# `product_tag-aceclofenac-100mg-thiocolchicoside-4mg` is the composition with
# hyphens for spaces and no punctuation. Converted back, it reads as the salt
# composition the catalogue and the printed prescription expect.
TAG_STOPWORDS = ('tablet', 'capsule', 'syrup', 'suspension', 'injection',
                 'cream', 'gel', 'ointment', 'lotion', 'drops', 'spray',
                 'inhaler', 'sachet', 'powder', 'solution', 'respules',
                 'suppository', 'patch', 'granules', 'sr', 'er', 'md', 'ds',
                 'plus', 'and',
                 # 'otc' is a CATEGORY tag some products carry instead of a
                 # composition. It is not an ingredient, and leaving it in put
                 # the literal text 'Otc' in the composition field of three
                 # products - which reads as a drug name on the printed sheet.
                 'otc')

HEADERS = ['name', 'generic_name', 'brand_name', 'manufacturer',
           'salt_composition', 'strength', 'form', 'use_case',
           'selling_price', 'cost_price', 'requires_prescription',
           'data_source', 'source_url']

# Dosage-form words the source uses, mapped to the form values the rest of the
# catalogue uses. Anything unrecognised is passed through rather than guessed.
FORM_WORDS = [
    ('tablet sr', 'tablet SR'), ('tablet', 'tablet'),
    ('capsule', 'capsule'), ('cartridge', 'cartridge refill'),
    ('syrup', 'syrup'), ('suspension', 'suspension'),
    ('injection', 'injection'), ('infusion', 'infusion'),
    ('insulin', 'injection'), ('glargine', 'injection'),
    ('cream', 'cream'), ('gel', 'gel'), ('ointment', 'ointment'),
    ('lotion', 'lotion'), ('solution', 'solution'), ('drops', 'drops'),
    ('drop', 'drops'),
    ('eye drop', 'eye drops'), ('ear drop', 'ear drops'),
    ('nasal drop', 'nasal drops'), ('nasal spray', 'nasal spray'),
    ('spray', 'spray'), ('inhaler', 'inhaler'),
    ('respules', 'respules'), ('sachet', 'sachet'), ('granules', 'granules'),
    ('powder', 'powder'), ('suppository', 'suppository'),
    ('patch', 'patch'), ('device', 'device'), ('kit', 'kit'),
]


def strip_tags(text):
    return html.unescape(re.sub(r'<[^>]+>', '', text or '')).strip()


def fetch(url, path, use_cache=True):
    """Fetch a URL, caching to disk so a re-run does not refetch."""
    os.makedirs(CACHE, exist_ok=True)
    if use_cache and os.path.exists(path) and os.path.getsize(path) > 500:
        with open(path, encoding='utf-8', errors='replace') as handle:
            return handle.read()

    request = urllib.request.Request(url, headers={
        'User-Agent': 'PharmMS-catalogue-fetch/1.0 (offline pharmacy reference)',
    })
    with urllib.request.urlopen(request, timeout=45) as response:
        body = response.read().decode('utf-8', errors='replace')

    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(body)
    return body


def detect_form(name):
    """The dosage form, taken from the trailing word of the product name."""
    lowered = name.lower()
    for word, value in FORM_WORDS:
        if word in lowered:
            return value
    return ''


def _normalise_unit(token):
    """Upper-case the standardised units, which are conventionally upper case.

    '100000au' should read '100000AU'. A word boundary will not match here,
    because the unit is glued to the digits and \\b requires a non-word
    character on both sides - so the unit is matched at the END of the token
    instead.
    """
    return re.sub(r'(au|iu)$', lambda m: m.group(1).upper(), token,
                  flags=re.IGNORECASE)


def split_strength(composition):
    """
    Pull the strengths out of a composition string.

    'Aceclofenac 100mg + Paracetamol 325mg' -> '100mg + 325mg'
    'Adapalene 0.1%'                       -> '0.1%'
    'Insulin Glargine 100iu/ml'            -> '100iu/ml'

    The strength column is what the printed prescription shows, so it is worth
    extracting rather than leaving buried in the composition text. Both the
    bracketed form used by the curated catalogue and the bare form produced
    from these slugs are handled, because the two styles coexist once rows are
    imported.

    Concentration units carry a trailing '/ml' or '/g', which an earlier
    pattern missed - so every insulin and every cream expressed as mg/ml fell
    through with an empty strength. That is the field a pharmacist reads to
    check a dose, so a blank one is a real gap rather than a cosmetic one.
    """
    text = composition or ''
    bracketed = re.findall(r'\(([^)]+)\)', text)
    if bracketed:
        return ' + '.join(part.strip() for part in bracketed)

    # Bare strengths: a number followed by a unit, optionally per ml or per g.
    found = re.findall(
        r'\d+(?:\.\d+)?(?:mg|mcg|g|ml|iu|au|%)(?:/(?:ml|g|dose))?', text,
        re.IGNORECASE)
    if found:
        # Normalise the unit case: 'au' is enzyme activity (AU), 'iu' is
        # international units (IU), and a strength printed as '100000au' is not
        # a unit anyone recognises on a prescription.
        return ' + '.join(_normalise_unit(f) for f in found)

    # Ratios such as '30/70' are a strength in their own right for an insulin
    # mixture, and the quantities may be the only figures on the record.
    ratio = re.findall(r'\b\d{2}/\d{2}\b', text)
    if ratio:
        return ' + '.join(ratio)

    quantities = re.findall(r'\b\d+(?:\.\d+)?\b', text)
    if quantities:
        return ' + '.join(quantities[:4])

    # Some preparations genuinely have no numeric strength - Calamine Lotion is
    # a formulation rather than a dose of one ingredient. Rather than leave the
    # column blank, the composition itself is repeated here, so the printed
    # prescription shows something a pharmacist can act on and the record is
    # visibly "as supplied" rather than looking like a parsing failure.
    stripped = re.sub(r'\b(?:tablet|capsule|syrup|lotion|cream|gel|drops|'
                      r'solution|ointment|suspension|powder|spray)\b', '',
                      text, flags=re.IGNORECASE).strip()
    return stripped or text.strip()


def clean_name(raw):
    """The product name without the trailing generic composition line."""
    name = strip_tags(raw)
    # The listing often doubles the name with the composition appended.
    name = re.split(r'\s*\(', name)[0].strip()
    return name


def parse_listing(body):
    """
    Yield one dict per product found on a listing page.

    The source states the product name and its composition. It does NOT state
    an indication, a manufacturer, a prescription status or a price, so those
    are left EMPTY rather than inferred. An empty field the pharmacist fills in
    is honest; a plausible invented one is not, and on a stock system a wrong
    price or a wrong prescription status has real consequences.
    """
    rows = []
    for match in PRODUCT_RE.finditer(body):
        tag, href, aria = match.groups()
        name = strip_tags(aria)
        if not name:
            continue

        composition = tag_to_composition(tag)

        rows.append({
            'name': name,
            'generic_name': first_ingredient(composition),
            'brand_name': '',          # PMBJP products are sold by generic name
            'manufacturer': 'Jan Aushadhi (PMBJP)',
            'salt_composition': composition or name,
            'strength': split_strength(composition or name),
            'form': detect_form(name),
            'use_case': '',            # the source states no indication
            'selling_price': '',       # rendered by JS, not present in the HTML
            'cost_price': '',          # not published by the source
            'requires_prescription': '',
            'data_source': 'Jan Aushadhi (PMBJP)',
            'source_url': href,
        })
    return rows


def tag_to_composition(tag):
    """
    Turn a product_tag slug back into a readable composition.

    'aceclofenac-100mg-thiocolchicoside-4mg' becomes
    'Aceclofenac 100mg + Thiocolchicoside 4mg'

    The slug separates ingredients with hyphens and gives no delimiter between
    one ingredient's name and its strength, so the words are re-joined and a
    '+' inserted where a new ingredient begins - which is where a strength
    token closes the previous ingredient.

    A SLUG IS NOT PLAIN TEXT, and two substitutions have to be undone or the
    strength comes out wrong:
      * '0.1%' appears as '0-1-25' in some slugs and as '0-1' in others,
        because the full stop becomes a hyphen and '%' becomes '25' when the
        slug is URL-encoded ('%' is 0x25). Parsing 'adapalene-0-1-25-gel' by
        splitting on hyphens alone produced the strength '0 1 W W', which is a
        WRONG STRENGTH on a clinical record - the precise thing that must not
        ship. A percentage is therefore recognised as 'digit digit 25' and
        rebuilt as '0.1%'.
      * a decimal point inside a strength, as in '0.5mg', becomes a hyphen and
        must be rejoined rather than treated as a number followed by a word.
    """
    # 'W' is what '%' degrades to in the CSS-escaped class name, so a trailing
    # 'w' or 'W' token after a number is a percentage sign, not an ingredient.
    tag = tag.replace('-w-w', '-25').replace('-w', '-25')

    parts = [p for p in tag.split('-') if p and p not in TAG_STOPWORDS]
    if not parts:
        return ''

    # Rejoin a strength split by URL encoding: '0 1 25' -> '0.1%'.
    rejoined = []
    index = 0
    while index < len(parts):
        word = parts[index]
        nxt = parts[index + 1] if index + 1 < len(parts) else None
        after = parts[index + 2] if index + 2 < len(parts) else None

        # '<digit> <digit> 25' is a percentage such as '0.1%'.
        if (re.fullmatch(r'\d+', word) and nxt and re.fullmatch(r'\d+', nxt)
                and after and after in ('25', '5')):
            rejoined.append('%s.%s%%' % (word, nxt))
            index += 3
            continue

        # '<digit> <digit>' followed by a unit is a decimal strength, 0.5mg.
        if (re.fullmatch(r'\d+', word) and nxt and re.fullmatch(r'\d+', nxt)
                and after and re.fullmatch(r'(?:mg|mcg|g|ml|iu)', after)):
            rejoined.append('%s.%s%s' % (word, nxt, after))
            index += 3
            continue

        rejoined.append(word)
        index += 1

    STRENGTH_RE = r'\d+(?:\.\d+)?(?:mg|mcg|g|ml|iu|%)?'
    ingredients = []
    current = []
    for word in rejoined:
        current.append(word)
        if re.fullmatch(STRENGTH_RE, word) and re.search(r'\d|%', word):
            ingredients.append(' '.join(current))
            current = []
    if current:
        ingredients.append(' '.join(current))

    cleaned = []
    for item in ingredients:
        words = item.split()
        text = ' '.join(
            w if re.search(r'[\d%]', w) else w.capitalize() for w in words)
        cleaned.append(text)

    return ' + '.join(cleaned)


def first_ingredient(composition):
    """The first ingredient alone, which is what generic_name holds."""
    if not composition:
        return ''
    first = re.split(r'\s*\+\s*', composition)[0]
    return re.sub(r'\s*\d.*$', '', first).strip()


def main():
    parser = argparse.ArgumentParser(
        description='Fetch the real Jan Aushadhi product catalogue.')
    parser.add_argument('--pages', type=int, default=27,
                        help='How many listing pages to fetch (default 27).')
    parser.add_argument('--from-cache', action='store_true',
                        help='Parse cached pages without fetching.')
    parser.add_argument('--delay', type=float, default=1.0,
                        help='Seconds between requests (be polite).')
    args = parser.parse_args()

    all_rows = []
    seen = set()

    for page in range(1, args.pages + 1):
        url = BASE if page == 1 else '%spage/%d/' % (BASE, page)
        path = os.path.join(CACHE, 'page-%03d.html' % page)

        try:
            if args.from_cache and not os.path.exists(path):
                continue
            body = fetch(url, path, use_cache=args.from_cache or
                         os.path.exists(path))
        except Exception as exc:
            print('  page %d: could not fetch (%s)' % (page, exc))
            continue

        rows = parse_listing(body)
        added = 0
        for row in rows:
            key = row['name'].lower()
            if key in seen:
                continue
            seen.add(key)
            all_rows.append(row)
            added += 1

        print('  page %2d: %2d products (%d new, %d total)'
              % (page, len(rows), added, len(all_rows)))

        if not args.from_cache:
            time.sleep(args.delay)

    if not all_rows:
        print()
        print('No products parsed. The listing markup may have changed -')
        print('this script fails loudly rather than emitting empty rows.')
        return 1

    with open(OUT_CSV, 'w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=HEADERS)
        writer.writeheader()
        for row in sorted(all_rows, key=lambda r: r['name'].lower()):
            writer.writerow(row)

    print()
    print('wrote %d products to %s' % (len(all_rows), OUT_CSV))

    forms = {}
    for row in all_rows:
        forms[row['form'] or '(unclassified)'] = forms.get(row['form'] or '(unclassified)', 0) + 1
    print()
    print('by dosage form:')
    for form, count in sorted(forms.items(), key=lambda kv: -kv[1]):
        print('  %-16s %d' % (form, count))
    return 0


if __name__ == '__main__':
    sys.exit(main())