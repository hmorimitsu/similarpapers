"""
computes various cache things on top of db.py so that the server
(running from serve.py) can start up and serve faster when restarted.

this script should be run whenever db.p is updated, and 
creates db2.p, which can be read by the server.
"""

import time
import pickle
import dateutil.parser

from utils import safe_pickle_dump, Config

CACHE = {}

print('loading the paper database', Config.db_path)
db = pickle.load(open(Config.db_path, 'rb'))

db = {pid: p for pid,p in db.items() if int(dateutil.parser.parse(p['published']).strftime('%Y')) >= Config.minimum_year}
if not Config.include_workshop_papers:
    db = {pid: p for pid,p in db.items() if not p['is_workshop']}

print('loading tfidf_meta', Config.meta_path)
meta = pickle.load(open(Config.meta_path, "rb"))
vocab = meta['vocab']
idf = meta['idf']

print('decorating the database with additional information...')
for pid,p in db.items():
    timestruct = dateutil.parser.parse(p['published'])
    p['time_published'] = int(timestruct.strftime("%s")) # store in struct for future convenience

    p['pid'] = pid
    p['conf_id'] = p['conf_id'] + ('W' if p['is_workshop'] else '')
    p['composed_conf_id'] = p['conf_id'] + ('_'+p['conf_sub_id'] if p['is_workshop'] else '')

print('computing min/max time for all papers...')
tts = [time.mktime(dateutil.parser.parse(p['published']).timetuple()) for pid,p in db.items()]
ttmin = min(tts)*1.0
ttmax = max(tts)*1.0
for pid,p in db.items():
    tt = time.mktime(dateutil.parser.parse(p['published']).timetuple())
    p['tscore'] = (tt-ttmin)/(ttmax-ttmin+1)

print('precomputing papers date sorted...')
scores = [(p['time_published'], pid) for pid,p in db.items()]
scores.sort(reverse=True, key=lambda x: x[0])
CACHE['date_sorted_pids'] = [sp[1] for sp in scores]

composed_conference_ids = set([p['conf_id'] for pid,p in db.items()])
print('composed_conference_ids')
print(composed_conference_ids)
CACHE['conference_sorted_pids'] = {
    cid: [pid for pid,p in db.items() if p['conf_id'] == cid] for cid in composed_conference_ids
}

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
