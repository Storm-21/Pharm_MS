"""
Medicine image storage.

What is asserted, and why each case is here:

  1. a stored image is served back and reports has_image
  2. the file is stored as a NAME, not a path (so it survives the data dir moving)
  3. a traversal attempt in the stored name is refused, not sanitised
  4. an over-size upload is refused rather than written
  5. the wrong file type is refused with the reason
  6. replacing an image deletes the previous file - no orphans left behind
  7. removing an image clears both the row and the file
  8. web fetching is OFF unless explicitly enabled
  9. a fetch with no network fails cleanly and stores nothing

Run:  python test_medicine_images.py
"""

import io
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

PASSED = 0
FAILED = []


def check(label, condition, detail=''):
    global PASSED
    if condition:
        PASSED += 1
        print('  PASS  %s' % label)
    else:
        FAILED.append(label)
        print('  FAIL  %s %s' % (label, ('- ' + str(detail)) if detail else ''))


class FakeUpload:
    """Mimics the FileStorage bits the service uses."""

    def __init__(self, filename, data):
        self.filename = filename
        self._data = data

    def read(self):
        return self._data


# A 1x1 PNG - the smallest thing that is really a PNG.
PNG = (
    b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
    b'\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01'
    b'\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
)


def main():
    workdir = tempfile.mkdtemp(prefix='pharms-images-')
    os.environ['PHARMS_DATA_DIR'] = workdir

    from app import create_app, db
    from app.models import Medicine
    from app.services import medicine_image_service as images

    app = create_app()
    with app.app_context():
        db.create_all()

        medicine = Medicine.query.first()
        if not medicine:
            print('No medicines in the database - nothing to test against.')
            return 1

        data_dir = workdir
        print()
        print('Medicine images  (%s)' % medicine.name[:40])
        print('-' * 60)

        # --- 8. Fetching is off by default ----------------------------------
        check('web fetch is disabled unless explicitly enabled',
              not images.fetch_enabled())

        # --- 5. Wrong type is refused ---------------------------------------
        ok, message, _ = images.save_upload(
            medicine, FakeUpload('virus.exe', b'MZ\x90\x00'), data_dir)
        check('a non-image upload is refused', not ok and 'Unsupported' in message,
              message)

        # --- 4. Oversize is refused -----------------------------------------
        big = FakeUpload('huge.png', b'\x89PNG\r\n\x1a\n' + b'0' * (4 * 1024 * 1024))
        ok, message, _ = images.save_upload(medicine, big, data_dir)
        check('an over-size image is refused', not ok and 'limit' in message, message)
        # The folder is created lazily on the first successful write, so it may
        # legitimately not exist yet - assert on any file it does contain.
        folder = os.path.join(data_dir, 'medicines')
        written = os.listdir(folder) if os.path.isdir(folder) else []
        check('the over-size upload was not written', written == [], written)

        ok, message, _ = images.save_upload(medicine, FakeUpload('empty.png', b''), data_dir)
        check('an empty upload is refused', not ok, message)

        # --- 1. A real upload is stored and reported -------------------------
        ok, message, stored = images.save_upload(
            medicine, FakeUpload('paracetamol.png', PNG), data_dir)
        check('a PNG upload is accepted', ok, message)
        status = images.image_status(medicine, data_dir)
        check('the medicine now reports an image', status['has_image'])
        check('the source is recorded as an upload', status['source'] == 'upload')
        check('the stored value is a bare file NAME, not a path',
              stored and os.sep not in stored and ':' not in stored, stored)

        # --- 2. The name resolves against the current data directory ---------
        check('the stored name resolves to a real file',
              images.image_path(data_dir, medicine.image_filename) is not None)
        # A second data dir stands in for "the database was moved to another PC".
        other = tempfile.mkdtemp(prefix='pharms-images-moved-')
        check('an image does not resolve against an unrelated data directory',
              images.image_path(other, medicine.image_filename) is None)

        # --- 3. Traversal is refused ----------------------------------------
        for attack in ('../../pharmacy.db', '..\\..\\pharmacy.db',
                       'sub/dir.png', 'C:\\Windows\\win.ini', 'a.png.exe'):
            check('traversal refused: %s' % attack,
                  images.image_path(data_dir, attack) is None)
        check('safe_filename rejects a traversal name',
              images.safe_filename('../../evil.png') is None)
        check('safe_filename rejects an embedded separator',
              images.safe_filename('a/b.png') is None)
        check('safe_filename accepts a name we would write',
              images.safe_filename('paracetamol-20260101.png')
              == 'paracetamol-20260101.png')

        # --- 6. Replacing removes the old file -------------------------------
        first = medicine.image_filename
        ok, _message, second = images.save_upload(
            medicine, FakeUpload('new.png', PNG), data_dir)
        check('a replacement upload is accepted', ok)
        check('the old file was deleted, so no orphan is left',
              not os.path.exists(os.path.join(data_dir, 'medicines', first)),
              first)
        check('the new file exists',
              os.path.exists(os.path.join(data_dir, 'medicines', second)))

        # --- 7. Removal clears row and file ---------------------------------
        images.remove_image(medicine, data_dir)
        check('removing clears the record',
              medicine.image_filename is None
              and images.image_status(medicine, data_dir)['has_image'] is False)
        check('removing deletes the file',
              not os.path.exists(os.path.join(data_dir, 'medicines', second)))

        # --- 9. A fetch with no network fails cleanly -----------------------
        # Forced on so the disabled-guard is not what we are measuring here.
        os.environ['PHARMS_IMAGE_FETCH'] = '1'
        check('fetch_enabled honours the environment switch',
              images.fetch_enabled())
        try:
            import socket
            original = socket.create_connection

            def refuse(*a, **k):
                raise OSError('network disabled for this test')

            socket.create_connection = refuse
            ok, message, _ = images.fetch_from_web(medicine, data_dir)
            check('a fetch with no network fails and says why',
                  not ok and 'Upload' in message, message)
            check('a failed fetch stores nothing',
                  not images.image_status(medicine, data_dir)['has_image'])
        finally:
            import socket as _s
            _s.create_connection = original
            os.environ.pop('PHARMS_IMAGE_FETCH', None)

        # --- The disabled message has to be honest --------------------------
        ok, message, _ = images.fetch_from_web(medicine, data_dir)
        check('a fetch while disabled explains that it is off',
              not ok and 'off' in message.lower(), message)

    print()
    print('-' * 60)
    print('%d passed, %d failed' % (PASSED, len(FAILED)))
    if FAILED:
        for label in FAILED:
            print('   FAILED: %s' % label)
        return 1
    print('All medicine-image tests passed.')
    return 0


if __name__ == '__main__':
    sys.exit(main())