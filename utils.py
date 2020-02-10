from contextlib import contextmanager

import os
import pickle
import tempfile

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


# global settings
# -----------------------------------------------------------------------------
class Config(object):
    minimum_year = 2015
    include_workshop_papers = True
    suffix = '_' + str(minimum_year)
    suffix += '_wshop' if include_workshop_papers else ''

    # main paper information repo file
    db_path = os.path.join(ROOT_DIR, 'db.p')
    # intermediate processing folders
    pdf_dir = os.path.join(ROOT_DIR, 'data', 'pdf')
    txt_dir = os.path.join(ROOT_DIR, 'data', 'txt')
    thumbs_dir = os.path.join(ROOT_DIR, 'static', 'thumbs')
    # intermediate pickles
    tfidf_path = os.path.join(ROOT_DIR, 'tfidf{:}.p'.format(suffix))
    meta_path = os.path.join(ROOT_DIR, 'tfidf_meta{:}.p'.format(suffix))
    sim_path = os.path.join(ROOT_DIR, 'sim_dict{:}.p'.format(suffix))
    # sql database file
    db_serve_path = os.path.join(ROOT_DIR, 'db2{:}.p'.format(suffix))  # an enriched db.p with various preprocessing info
    serve_cache_path = os.path.join(ROOT_DIR, 'serve_cache{:}.p'.format(suffix))

    tmp_dir = 'tmp'


# Context managers for atomic writes courtesy of
# http://stackoverflow.com/questions/2333872/atomic-writing-to-file-with-python
@contextmanager
def _tempfile(*args, **kws):
    """ Context for temporary file.

    Will find a free temporary filename upon entering
    and will try to delete the file on leaving

    Parameters
    ----------
    suffix : string
        optional file suffix
    """

    fd, name = tempfile.mkstemp(*args, **kws)
    os.close(fd)
    try:
        yield name
    finally:
        try:
            os.remove(name)
        except OSError as e:
            if e.errno == 2:
                pass
            else:
                raise e


@contextmanager
def open_atomic(filepath, *args, **kwargs):
    """ Open temporary file object that atomically moves to destination upon
    exiting.

    Allows reading and writing to and from the same filename.

    Parameters
    ----------
    filepath : string
        the file path to be opened
    fsync : bool
        whether to force write the file to disk
    kwargs : mixed
        Any valid keyword arguments for :code:`open`
    """
    fsync = kwargs.pop('fsync', False)

    with _tempfile(dir=os.path.dirname(filepath)) as tmppath:
        with open(tmppath, *args, **kwargs) as f:
            yield f
            if fsync:
                f.flush()
                os.fsync(f.fileno())
        os.rename(tmppath, filepath)


def safe_pickle_dump(obj, fname):
    with open_atomic(fname, 'wb') as f:
        pickle.dump(obj, f, -1)


def isvalidid(pid):
    return 'favicon' not in pid
