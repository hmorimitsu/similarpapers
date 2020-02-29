"""
Reads txt files of all papers and computes tfidf vectors for all papers.
Dumps results to file tfidf.p
"""
import dateutil.parser
import os
import pickle
from collections import namedtuple
from random import shuffle, seed

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from utils import Config, safe_pickle_dump

PidConf = namedtuple('PidConf', 'pid, name, year, subid')

seed(1337)
max_train = 25000  # max number of tfidf training documents (chosen randomly), for memory efficiency
max_features = 5000

# read database
db = pickle.load(open(Config.db_path, 'rb'))

# read all text files for all papers into memory
txt_paths, pids = [], []
pid_confs = []
n = 0
# for pid,j in db.items():
for key in db:
    n += 1
    basename = db[key]['pdf_url'].split('/')[-1]
    txt_path = os.path.join(
        Config.txt_dir, db[key]['conf_id'], db[key]['conf_sub_id'], 
        basename) + '.txt'
    if os.path.isfile(txt_path): # some pdfs dont translate to txt
        pub_year = int(dateutil.parser.parse(db[key]['published']).strftime('%Y'))
        if not Config.include_workshop_papers and db[key]['is_workshop']:
            print("skipped %d/%d (%s): not using workshops" % (n, len(db), key))
        elif pub_year < Config.minimum_year:
            print("skipped %d/%d (%s): older than minimum year" % (n, len(db), key))
        else:
            with open(txt_path, 'r') as f:
                txt = f.read()
            if len(txt) > 1000 and len(txt) < 500000: # 500K is VERY conservative upper bound
                txt_paths.append(txt_path) # todo later: maybe filter or something some of them
                pids.append(key)
                conf_id = db[key]['conf_id']
                pid_confs.append(PidConf(key, conf_id[:-4], conf_id[-4:], db[key]['conf_sub_id'].lower()))
                print("read %d/%d (%s) with %d chars" % (n, len(db), key, len(txt)))
            else:
                print("skipped %d/%d (%s) with %d chars: suspicious!" % (n, len(db), key, len(txt)))
    # else:
    #     print("could not find %s in txt folder." % (txt_path, ))
print("in total read in %d text files out of %d db entries." % (len(txt_paths), len(db)))

# compute tfidf vectors with scikits
v = TfidfVectorizer(
    input='content', 
    encoding='utf-8', decode_error='replace', strip_accents='unicode', 
    lowercase=True, analyzer='word', stop_words='english', 
    token_pattern=r'(?u)\b[a-zA-Z_][a-zA-Z0-9_]+\b',
    ngram_range=(1, 2), max_features = max_features, 
    norm='l2', use_idf=True, smooth_idf=True, sublinear_tf=True,
    max_df=1.0, min_df=1)


# create an iterator object to conserve memory
def make_corpus(paths):
    for p in paths:
        with open(p, 'r') as f:
            txt = f.read()
        yield txt


# train
train_txt_paths = list(txt_paths) # duplicate
shuffle(train_txt_paths) # shuffle
train_txt_paths = train_txt_paths[:min(len(train_txt_paths), max_train)] # crop
print("training on %d documents..." % (len(train_txt_paths), ))
train_corpus = make_corpus(train_txt_paths)
v.fit(train_corpus)

# transform
print("transforming %d documents..." % (len(txt_paths), ))
corpus = make_corpus(txt_paths)
X = v.transform(corpus)
print(v.vocabulary_)
print(X.shape)

# write full matrix out
out = {}
out['X'] = X # this one is heavy!
print("writing", Config.tfidf_path)
safe_pickle_dump(out, Config.tfidf_path)

# writing lighter metadata information into a separate (smaller) file
out = {}
out['vocab'] = v.vocabulary_
out['idf'] = v._tfidf.idf_
out['pids'] = pids # a full idvv string (id and version number)
out['ptoi'] = { x:i for i,x in enumerate(pids) } # pid to ix in X mapping
print("writing", Config.meta_path)
safe_pickle_dump(out, Config.meta_path)

# Find newest year of each conference
composed_conference_ids = set([(p['conf_id'], dateutil.parser.parse(p['published'])) for pid,p in db.items()])
composed_conference_ids = sorted(list(composed_conference_ids), key=lambda x: x[1], reverse=True)
newest_conf_years = {}
for conf_id, conf_year in composed_conference_ids:
    conf_name = conf_id[:-4]
    if newest_conf_years.get(conf_name) is None:
        newest_conf_years[conf_name] = conf_year.strftime('%Y')


# Counts how many papers in the latest conferences are already in the top picks
def count_conference_papers(top_pids, newest_conf_years, db):
    counters = {conf_name: 0 for conf_name in newest_conf_years}
    for pid in top_pids:
        conf_id = db[pid]['conf_id']
        conf_name = conf_id[:-4]
        conf_year = conf_id[-4:]
        if db[pid]['conf_sub_id'].lower() == 'main' and conf_year == newest_conf_years[conf_name]:
            counters[conf_name] += 1
    return counters


# Find more top pids until all latest conferences have at least top_k_by_conf papers in the list
def get_top_pids_by_conference(top_k, top_k_by_conf, conf_counters, newest_conf_years, sort_idx, pid_confs, db):
    sorted_pid_confs = [pid_confs[i] for i in sort_idx]
    filtered_pid_confs = [
        pc for pc in sorted_pid_confs[top_k:]
        if pc.subid == 'main' and
        pc.year == newest_conf_years[pc.name]]
    conf_top_pids = []
    for pc in filtered_pid_confs:
        if conf_counters[pc.name] < top_k_by_conf:
            conf_top_pids.append(pc.pid)
            conf_counters[pc.name] += 1
    return conf_top_pids


print("precomputing nearest neighbor queries in batches...")
X = X.todense() # originally it's a sparse matrix
sim_dict = {}
batch_size = 200
top_k = 200
top_k_by_conf = 50
for i in range(0, len(pids), batch_size):
    i1 = min(len(pids), i+batch_size)
    xquery = X[i:i1] # BxD
    ds = -np.asarray(np.dot(X, xquery.T)) #NxD * DxB => NxB
    IX = np.argsort(ds, axis=0) # NxB
    for j in range(i1-i):
        top_pids = [pids[q] for q in list(IX[1:top_k, j])]
        conf_counters = count_conference_papers(top_pids, newest_conf_years, db)
        conf_top_pids = get_top_pids_by_conference(top_k, top_k_by_conf, conf_counters, newest_conf_years, IX[:, j], pid_confs, db)
        top_pids += conf_top_pids
        sim_dict[pids[i+j]] = top_pids
    print('%d/%d...' % (i, len(pids)))

print("writing", Config.sim_path)
safe_pickle_dump(sim_dict, Config.sim_path)
