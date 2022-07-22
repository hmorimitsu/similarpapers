"""
computes various cache things on top of db.py so that the server
(running from serve.py) can start up and serve faster when restarted.

this script should be run whenever db.p is updated, and 
creates db2.p, which can be read by the server.
"""

import time
import pickle
import dateutil.parser
import string

from utils import safe_pickle_dump, Config, load_json_db

CACHE = {}
IGNORE_WORD = [
    'about', 'am', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'do', 'does', 'for', 'from', 'he', 'in', 'is', 'it', 'me', 'my', 'of', 'on', 'she', 'so', 'the', 'they', 'to', 'under', 'using', 'via', 'we', 'with', 'without', 'you'
]


def clean_title(title):
    # Remove punctuation code from: https://datagy.io/python-remove-punctuation-from-string/
    title = title.translate(str.maketrans('', '', string.punctuation))

    # TODO: use a smarter text processing technique

    title_words = [w for w in title.split(' ') if len(w) > 1 and w.lower() not in IGNORE_WORD]
    title = ' '.join([s for s in title.split(' ') if len(s) > 1])
    return ' '.join(title_words)


def format_booktitle(conf_id, conf_name):
    if conf_id[-1] == 'W':
        conf_id = conf_id[:-1]
    conf_name = conf_name.replace('_workshop', ' workshop')
    conf_name = conf_name.replace(conf_id, conf_id[:-4])
    return conf_name


print('loading the paper database from json files in', Config.json_dir)
db = load_json_db()

db = {pid: p for pid,p in db.items() if int(dateutil.parser.parse(p['published']).strftime('%Y')) >= Config.minimum_year}
if not Config.include_workshop_papers:
    db = {pid: p for pid,p in db.items() if not p['is_workshop']}

print('loading tfidf_meta', Config.meta_path)
meta = pickle.load(open(Config.meta_path, "rb"))
vocab = meta['vocab']
idf = meta['idf']

print('decorating the database with additional information...')
for pid,p in db.items():
    p['year'] = p['conf_id'][-4:]
    p['pid'] = pid
    p['conf_id'] = p['conf_id'] + ('W' if p['is_workshop'] else '')
    p['composed_conf_id'] = p['conf_id'] + ('_'+p['conf_sub_id'] if p['is_workshop'] else '')
    bib_id_title = clean_title(p['title'])
    bib_id_title = bib_id_title.split(' ')
    bib_id_title = ''.join(bib_id_title[:3])
    p['bib_id'] = f'{p["authors"][0].split(" ")[-1]}{p["published"][:4]}{bib_id_title}'
    bib_authors = [a.replace('.', '. ').split(' ') for a in p["authors"]]
    bib_authors = [[a.strip() for a in authors_list if len(a) > 0] for authors_list in bib_authors]
    for authors_list in bib_authors:
        for i, aut in enumerate(authors_list[1:-1]):
            authors_list[i+1] = f'{aut[0]}.'
    bib_authors = [f'{a[-1]}, {" ".join(a[:-1])}' for a in bib_authors]
    bib_authors = ' and '.join(bib_authors)
    p['bib_authors'] = bib_authors
    p['bib_booktitle'] = format_booktitle(p['conf_id'], p['conf_name'])

print('computing min/max time for all papers...')
tts = [time.mktime(dateutil.parser.parse(p['published']).timetuple()) for pid,p in db.items()]
ttmin = min(tts)*1.0
ttmax = max(tts)*1.0
for pid,p in db.items():
    tt = time.mktime(dateutil.parser.parse(p['published']).timetuple())
    p['tscore'] = (tt-ttmin)/(ttmax-ttmin+1)

print('precomputing conference data...')
composed_conference_ids = set([(p['conf_id'], dateutil.parser.parse(p['published'])) for pid,p in db.items()])
CACHE['conference_sorted_pids'] = {
    cid[0]: [pid for pid,p in db.items() if p['conf_id'] == cid[0]] for cid in composed_conference_ids
}
composed_conference_ids = sorted(list(composed_conference_ids), key=lambda x: x[1], reverse=True)
most_recent_conference_idx = composed_conference_ids[0][0]
if most_recent_conference_idx.endswith('W'):
    most_recent_conference_idx = most_recent_conference_idx[:-1]
CACHE['most_recent_conference_name'] = most_recent_conference_idx[:-4]
CACHE['newest_conference_year'] = composed_conference_ids[0][1].strftime('%Y')
CACHE['oldest_conference_year'] = composed_conference_ids[-1][1].strftime('%Y')

# some utilities for creating a search index for faster search
punc = "'!\"#$%&\'()*+,./:;<=>?@[\\]^_`{|}~'" # removed hyphen from string.punctuation
trans_table = {ord(c): None for c in punc}
def makedict(s, forceidf=None, scale=1.0):
    words = set(s.lower().translate(trans_table).strip().split())
    idfd = {}
    for w in words: # todo: if we're using bigrams in vocab then this won't search over them
        if forceidf is None:
            if w in vocab:
                # we have idf for this
                idfval = idf[vocab[w]]*scale
            else:
                idfval = 1.0*scale # assume idf 1.0 (low)
        else:
            idfval = forceidf
        idfd[w] = idfval
    return idfd

def merge_dicts(dlist):
    m = {}
    for d in dlist:
        for k, v in d.items():
            m[k] = m.get(k, 0) + v
    return m

print('building an index for faster search...')
search_dict = {}
for pid,p in db.items():
    dict_title = makedict(p['title'], forceidf=5, scale=3)
    dict_authors = makedict(' '.join(x for x in p['authors']), forceidf=5)
    dict_categories = {p['composed_conf_id'].lower(): 5}
    dict_conf_name = makedict(p['conf_name'], forceidf=5, scale=3)
    if 'and' in dict_authors: 
        # special case for "and" handling in authors list
        del dict_authors['and']
    dict_summary = makedict(p['summary'])
    search_dict[pid] = merge_dicts([dict_title, dict_authors, dict_categories, dict_summary, dict_conf_name])
CACHE['search_dict'] = search_dict

# save the cache
print('writing', Config.serve_cache_path)
safe_pickle_dump(CACHE, Config.serve_cache_path)
print('writing', Config.db_serve_path)
safe_pickle_dump(db, Config.db_serve_path)
