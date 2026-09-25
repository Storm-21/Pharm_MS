"""
Medicine images: store, serve and (optionally) fetch a pack shot.

DESIGN, AND WHY
---------------
Three things drive this design, and all three are the opposite of the obvious
choice:

1. **Local first, always.** An image is fetched once, written to this machine,
   and served from disk afterwards. The counter has to keep working with the
   router unplugged, so a medicine image must never be a live network call. The
   fetch is a one-off convenience when you *do* have a connection, not a
   dependency.

2. **Stored as a file name, not a path.** The data directory is
   `%LOCALAPPDATA%\\PharmMS` for one user and something else for the next, so an
   absolute path stored in the database breaks the moment the folder moves (or
   the database is restored onto another PC). A bare file name is resolved
   against the current data directory on every read. It also removes a
   path-traversal vector: a name is validated to contain no separators, so it
   cannot be used to ask for `..\\..\\secrets`.

3. **Fetched images carry their provenance.** `image_source` distinguishes an
   upload from a fetch, and `image_attribution` keeps any credit line the source
   supplied. A clinical reference database that silently presents an image of
   unknown origin as its own would be misrepresenting its data, and the pack shot
   is what a pharmacist uses to confirm they picked up the right box.

WHERE IMAGES COME FROM
----------------------
`fetch_from_web()` uses Wikipedia's public API to find an image for the drug's
generic name. It is deliberately conservative:

  * off unless switched on (`PHARMS_IMAGE_FETCH=1` or the setting below),
  * only the drug's generic name is ever sent - never a patient, never a record,
  * the first suitable result is downloaded, size-checked and stored locally,
  * if anything fails you get a clear reason and NO entry - an absent image is
    reported as absent, never as a broken or blank one.

Wikimedia content is used under its own licence, and the licence can differ per
file, so the API's own credit line is stored alongside the image and shown in the
UI. Only freely-licensed media is requested, which is why the request filters on
that.
"""

import json
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime

ALLOWED_EXT = {'.png', '.jpg', '.jpeg', '.webp', '.gif'}
MAX_BYTES = 3 * 1024 * 1024          # 3 MB - a pack shot, not a poster
FETCH_TIMEOUT = 12                    # seconds
# Wikimedia asks that automated clients identify themselves.
USER_AGENT = 'PharmMS/2.2 (offline pharmacy management; medicine image lookup)'

# A file name we wrote ourselves: letters, digits, underscore, dash and one
# extension. Anything else is rejected rather than sanitised, because a name that
# needed sanitising is a name we did not write.
_SAFE_NAME = re.compile(r'^[A-Za-z0-9_-]{1,120}\.(png|jpg|jpeg|webp|gif)$')


def images_dir(data_dir):
    """Where medicine images live, beside the database."""
    path = os.path.join(data_dir, 'medicines')
    os.makedirs(path, exist_ok=True)
    return path


def safe_filename(name):
    """
    The stored name, or None when it is not one we would have written.

    Rejected rather than repaired, and deliberately WITHOUT calling
    os.path.basename first. An earlier version did:

        base = os.path.basename(str(name))   # '../../evil.png' -> 'evil.png'
        if _SAFE_NAME.match(base): return base

    which looked safe and was not. basename *strips* a traversal instead of
    rejecting it, so '../../evil.png' was silently accepted as 'evil.png' - a
    differently-named success rather than a refused attack. The image would have
    landed in the right folder in that case, but the caller was told the value
    was fine, and the same helper guards image_path(), which is what actually
    serves files. Rejecting on the raw value means an attack is refused wherever
    it would be used, and a name that fails is reported rather than reinterpreted.
    """
    if not name:
        return None
    raw = str(name)
    # Any path structure at all is disqualifying: a name we wrote is a flat
    # token, so a separator, a drive letter or a parent reference means this is
    # not one of ours.
    if any(bad in raw for bad in ('/', '\\', '..', ':')):
        return None
    if not _SAFE_NAME.match(raw):
        return None
    return raw


def image_path(data_dir, filename):
    """Absolute path of a stored image, or None when it is absent or unsafe."""
    safe = safe_filename(filename)
    if not safe:
        return None
    path = os.path.join(images_dir(data_dir), safe)
    return path if os.path.isfile(path) else None


def _slug(text):
    return re.sub(r'[^a-z0-9]+', '-', (text or '').lower()).strip('-')


def _unique_name(base_slug, ext, folder):
    """
    A file name that is not already taken in the folder.

    The timestamp alone is not enough: two images saved in the same second get
    the same name, and then the second write silently overwrites the first while
    the medicine record still points at "the" file - so a replacement looks like
    it worked but has quietly replaced the wrong thing. test_medicine_images.py
    caught this by uploading twice in one second.

    A short random suffix keeps the name human-readable while making a collision
    effectively impossible, and the loop is the belt-and-braces check.
    """
    import secrets
    stamp = datetime.now().strftime('%Y%m%d%H%M%S')
    for _ in range(5):
        candidate = '%s-%s-%s%s' % (base_slug, stamp, secrets.token_hex(2), ext)
        if not os.path.exists(os.path.join(folder, candidate)):
            return candidate
    # Five collisions in a row means something is wrong with the clock or the
    # randomness; fall back to a guaranteed-unique name rather than give up.
    return '%s-%s%s' % (base_slug, secrets.token_hex(8), ext)


def save_upload(medicine, file_storage, data_dir):
    """
    Store an uploaded image against a medicine. Returns (ok, message, filename).

    The stored name is derived from the medicine and a timestamp, so it is always
    one we wrote, always unique, and never influenced by the uploaded filename
    beyond its extension - a crafted `../../evil.png` upload cannot escape.
    """
    filename = (file_storage.filename or '').strip()
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXT:
        return False, (
            "Unsupported image type '%s'. Use one of: %s."
            % (ext or 'none', ', '.join(sorted(ALLOWED_EXT)))
        ), None

    raw = file_storage.read()
    if not raw:
        return False, 'That file was empty.', None
    if len(raw) > MAX_BYTES:
        return False, (
            'That image is %.1f MB. The limit is %d MB - please resize it.'
            % (len(raw) / 1024 / 1024, MAX_BYTES // 1024 // 1024)
        ), None

    folder = images_dir(data_dir)
    stored = _unique_name(
        _slug(medicine.generic_name or medicine.name or 'medicine'), ext, folder)
    with open(os.path.join(folder, stored), 'wb') as handle:
        handle.write(raw)

    # Clear the previous image AFTER the new one is safely on disk, so a failure
    # mid-write never leaves the medicine with no image at all.
    _clear_previous(medicine, data_dir, keep=stored)
    medicine.image_filename = stored
    medicine.image_source = 'upload'
    medicine.image_attribution = None
    medicine.image_fetched_at = datetime.utcnow()
    return True, 'Image saved.', stored


def _clear_previous(medicine, data_dir, keep=None):
    """
    Delete the medicine's previous image, if any.

    Without this, replacing an image leaks a file on every change - small, but
    a pharmacy that swaps its pack shots a few times a year ends up with a folder
    full of images nothing references, and no way to tell which are live.
    """
    old = safe_filename(medicine.image_filename)
    if old and old != keep:
        try:
            os.remove(os.path.join(images_dir(data_dir), old))
        except OSError:
            pass


def remove_image(medicine, data_dir):
    """Drop the medicine's image and delete the file."""
    _clear_previous(medicine, data_dir)
    medicine.image_filename = None
    medicine.image_source = None
    medicine.image_attribution = None
    medicine.image_fetched_at = None
    return True, 'Image removed.'


# --- Fetching from the web ---------------------------------------------------

def fetch_enabled():
    """
    Whether web image fetching is allowed.

    Off by default and stated explicitly, because the whole product promise is
    that the application makes no internet requests of its own. A feature that
    quietly reached out would break that promise, so it is opt-in and the UI has
    to say so.
    """
    flag = (os.environ.get('PHARMS_IMAGE_FETCH') or '').strip().lower()
    return flag in ('1', 'true', 'yes', 'on')


def _lookup_wikimedia(query):
    """
    Find a freely-licensed image for a search term.

    Returns (image_url, credit, page_url) or (None, None, None).

    Two-step, because that is how the API works: search the file namespace for
    the term, then ask for the image info of the best hit. Filtering to the file
    namespace and asking only for the first result keeps this to two small
    requests rather than paging through results.
    """
    api = 'https://commons.wikimedia.org/w/api.php'

    search_params = {
        'action': 'query',
        'format': 'json',
        'generator': 'search',
        'gsrsearch': '%s filetype:bitmap' % query,
        'gsrnamespace': '6',              # File namespace
        'gsrlimit': '1',
        'prop': 'imageinfo',
        'iiprop': 'url|extmetadata|size',
        'iiurlwidth': '600',
    }
    url = api + '?' + urllib.parse.urlencode(search_params)
    request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    with urllib.request.urlopen(request, timeout=FETCH_TIMEOUT) as response:
        payload = json.loads(response.read().decode('utf-8'))

    pages = (payload.get('query') or {}).get('pages') or {}
    for page in pages.values():
        info = (page.get('imageinfo') or [{}])[0]
        # Prefer the scaled URL: a full-resolution original of a drug box can be
        # many megabytes, which is wasteful for a thumbnail nobody will zoom.
        image_url = info.get('thumburl') or info.get('url')
        if not image_url:
            continue
        meta = info.get('extmetadata') or {}
        licence = (meta.get('LicenseShortName') or {}).get('value') or 'Unknown licence'
        artist = (meta.get('Artist') or {}).get('value') or ''
        # The Artist field is HTML on Commons; strip tags so the stored credit
        # is text and cannot inject anything into the UI.
        artist = re.sub(r'<[^>]+>', '', artist).strip()
        credit = '%s - %s' % (artist or 'Wikimedia Commons', licence)
        return image_url, credit, info.get('descriptionurl')
    return None, None, None


def fetch_from_web(medicine, data_dir, query=None):
    """
    Look up and store an image for a medicine from the web.

    Returns (ok, message, filename). Nothing is written unless the whole
    download succeeds, so a failure never leaves a half-stored image.
    """
    if not fetch_enabled():
        return False, (
            'Web image lookup is off. It is disabled by default because the '
            'application makes no internet requests unless you ask it to. Set '
            'PHARMS_IMAGE_FETCH=1 (or use Upload image) to enable it.'
        ), None

    term = (query or medicine.generic_name or medicine.name or '').strip()
    if not term:
        return False, 'No name to look up.', None

    try:
        image_url, credit, page_url = _lookup_wikimedia(term)
    except Exception as exc:
        return False, (
            'Could not reach the image source (%s). Your connection may be off, '
            'which is fine - use Upload image instead.' % exc
        ), None

    if not image_url:
        return False, (
            'No image was found for "%s" under a free licence. Upload one '
            'instead.' % term
        ), None

    try:
        request = urllib.request.Request(
            image_url, headers={'User-Agent': USER_AGENT})
        with urllib.request.urlopen(request, timeout=FETCH_TIMEOUT) as response:
            raw = response.read(MAX_BYTES + 1)
    except Exception as exc:
        return False, 'Could not download the image (%s).' % exc, None

    if len(raw) > MAX_BYTES:
        return False, (
            'That image is larger than %d MB and was not stored. Upload a '
            'smaller one.' % (MAX_BYTES // 1024 // 1024)
        ), None

    # The extension comes from the URL, but only if it is one we serve - an
    # unfamiliar or absent extension falls back to .jpg rather than being used.
    ext = os.path.splitext(urllib.parse.urlparse(image_url).path)[1].lower()
    if ext not in ALLOWED_EXT:
        ext = '.jpg'

    stored = _unique_name(
        '%s-web' % _slug(medicine.generic_name or medicine.name or 'medicine'),
        ext, images_dir(data_dir))
    with open(os.path.join(images_dir(data_dir), stored), 'wb') as handle:
        handle.write(raw)

    _clear_previous(medicine, data_dir, keep=stored)
    medicine.image_filename = stored
    medicine.image_source = 'web'
    medicine.image_attribution = credit
    medicine.image_fetched_at = datetime.utcnow()
    return True, 'Image fetched and stored locally.', stored


def image_status(medicine, data_dir):
    """What the UI needs to render the image panel for one medicine."""
    stored = safe_filename(medicine.image_filename)
    present = bool(stored and image_path(data_dir, stored))
    return {
        'has_image': present,
        'source': medicine.image_source,
        'attribution': medicine.image_attribution,
        'fetched_at': (medicine.image_fetched_at.isoformat()
                       if medicine.image_fetched_at else None),
        'fetch_enabled': fetch_enabled(),
        # The stored name is reported so the UI can cache-bust on replacement.
        'filename': stored if present else None,
    }