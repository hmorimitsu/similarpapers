import os
import pickle
import argparse
import dateutil.parser

from flask import Flask, request, url_for, redirect, render_template
from flask_limiter import Limiter

from utils import isvalidid, Config

# various globals
# -----------------------------------------------------------------------------

# database configuration
if os.path.isfile('secret_key.txt'):
    SECRET_KEY = open('secret_key.txt', 'r').read()
else:
    SECRET_KEY = 'devkey, should be in a file'
app = Flask(__name__)
app.config.from_object(__name__)
limiter = Limiter(app, default_limits=["100000 per hour", "20000 per minute"])

# -----------------------------------------------------------------------------
# search/sort functionality
# -----------------------------------------------------------------------------


def papers_search(qraw):
    qparts = qraw.lower().strip().split() # split by spaces
    # use reverse index and accumulate scores
    scores = []
    for pid, p in db.items():
        score = sum(SEARCH_DICT[pid].get(q,0) for q in qparts)
        if score == 0:
            continue # no match whatsoever, dont include
        # give a small boost to more recent papers
        score += 0.0001*p['tscore']
        scores.append((score, p))
    scores.sort(reverse=True, key=lambda x: x[0]) # descending
    out = [x[1] for x in scores if x[0] > 0]
    return out


def papers_similar(pid, confs_filter):
    # check if we have this paper at all, otherwise return empty list
    if pid not in db: 
        return []

    # check if we have distances to this specific version of paper id (includes version)
    if pid in sim_dict:
        # good, simplest case: lets return the papers
        if confs_filter == 'all':
            return [db[pid]] + [db[k] for k in sim_dict[pid]]
        else:
            confs_filter = confs_filter.split(',')
            if Config.include_workshop_papers:
                confs_filter.extend([c+'W' for c in confs_filter])
            return [db[pid]] + [db[k] for k in sim_dict[pid] if db[k]['conf_id'] in confs_filter]
    else:
        return [db[pid]]


def encode_json(ps, n=10, send_images=True, send_abstracts=True):
    ret = []
    for i in range(min(len(ps),n)):
        p = ps[i]
        struct = {}
        struct['title'] = p['title']
        struct['pid'] = p['pid']
        struct['authors'] = [a for a in p['authors']]
        struct['link'] = p['page_url']
        struct['pdf_link'] = p['pdf_url']
        struct['conf_name'] = p['conf_name']
        struct['composed_conf_id'] = p['composed_conf_id']
        if send_abstracts:
            struct['abstract'] = p['summary']

        # render time information nicely
        timestruct = dateutil.parser.parse(p['published'])
        struct['published_time'] = '%s/%s/%s' % (timestruct.month, timestruct.day, timestruct.year)
        timestruct = dateutil.parser.parse(p['published'])

        ret.append(struct)
    return ret


# -----------------------------------------------------------------------------
# conference handling
# -----------------------------------------------------------------------------

def gen_conferences_dict(conf_ids_list):
    conf_dict = {}
    for cid in conf_ids_list:
        is_workshop = False
        if cid.lower().endswith('w'):
            is_workshop = True
            cid = cid[:-1]
        try:
            year = str(int(cid[-4:]))
            conf_name = cid[:-4]
        except ValueError:
            try:
                year = str(int(cid[-2:]))
                conf_name = cid[:-2]
            except ValueError:
                raise ValueError('Cannot find year in conference ID.')
        type_str = 'Main'
        if is_workshop:
            type_str = 'Workshop'
        if conf_dict.get(conf_name) is None:
            conf_dict[conf_name] = {year: set([type_str])}
        else:
            if conf_dict[conf_name].get(year) is None:
                conf_dict[conf_name][year] = set([type_str])
            else:
                conf_dict[conf_name][year].add(type_str)

    # Ensures that 'Main' will be the first element after sorting
    def conf_type_sort_idx(type_str):
        if type_str.lower() == 'main':
            return '0'
        return type_str

    sorted_conf_dict = {}
    sorted_names = sorted(list(conf_dict))
    for conf_name in sorted_names:
        sorted_conf_dict[conf_name] = {}
        sorted_years = sorted(list(conf_dict[conf_name]))
        for year in sorted_years:
            sorted_conf_dict[conf_name][year] = sorted(conf_dict[conf_name][year], key=lambda x: conf_type_sort_idx(x))
    return sorted_conf_dict


# -----------------------------------------------------------------------------
# flask request handling
# -----------------------------------------------------------------------------

def default_context(papers, **kws):
    top_papers = encode_json(papers, 200)

    # prompt logic
    show_prompt = 'no'

    ans = dict(papers=top_papers, numresults=len(papers), totpapers=len(db), msg='', show_prompt=show_prompt, pid_to_users={})
    ans.update(kws)
    return ans


@app.route("/")
def intmain():
    conf_str = request.args.get('conf', None)
    year_str = request.args.get('year', None)
    type_str = request.args.get('year', None)
    if conf_str is None or year_str is None:
        if conf_str is None:
            conf_str = MOST_RECENT_CONFERENCE
        if year_str is None:
            year_str = list(CONFERENCES[conf_str])[-1]
        if type_str is None:
            type_str = 'Main'
        return redirect(url_for('intmain', conf=MOST_RECENT_CONFERENCE, year=year_str, type=type_str))
    else:
        suffix = '' if request.args.get('type', 'Main').lower() == 'main' else 'W'
        papers = [db[pid] for pid in CONFERENCE_SORTED_PIDS[conf_str+year_str+suffix]] # precomputed
        ctx = default_context(
            papers, render_format='recent', msg='Showing papers from {:}{:} {:}'.format(conf_str, suffix, year_str),
            conferences=CONFERENCES,
            include_workshop_papers=Config.include_workshop_papers)
        return render_template('main.html', **ctx)


@app.route("/<request_pid>")
def rank(request_pid=None):
    if not isvalidid(request_pid):
        return '' # these are requests for icons, things like robots.txt, etc
    confs_filter = request.args.get('confs', None)
    papers = papers_similar(request_pid, confs_filter)
    ctx = default_context(
        papers, render_format='paper',
        conferences=CONFERENCES,
        include_workshop_papers=Config.include_workshop_papers)
    return render_template('main.html', **ctx)


@app.route("/search", methods=['GET'])
def search():
    q = request.args.get('q', '') # get the search request
    papers = papers_search(q) # perform the query and get sorted documents
    ctx = default_context(
        papers, render_format='search',
        msg='Showing search results',
        conferences=CONFERENCES,
        include_workshop_papers=Config.include_workshop_papers)
    return render_template('main.html', **ctx)


@app.route("/info", methods=['GET'])
def info():
    ctx = default_context(
        [], render_format='search',
        msg='Showing search results',
        conferences=CONFERENCES,
        include_workshop_papers=Config.include_workshop_papers)
    return render_template('info.html', **ctx)

print('loading the paper database', Config.db_serve_path)
db = pickle.load(open(Config.db_serve_path, 'rb'))

print('loading tfidf_meta', Config.meta_path)
meta = pickle.load(open(Config.meta_path, "rb"))
vocab = meta['vocab']
idf = meta['idf']

print('loading paper similarities', Config.sim_path)
sim_dict = pickle.load(open(Config.sim_path, "rb"))

print('loading serve cache...', Config.serve_cache_path)
cache = pickle.load(open(Config.serve_cache_path, "rb"))
DATE_SORTED_PIDS = cache['date_sorted_pids']
CONFERENCE_SORTED_PIDS = cache['conference_sorted_pids']
SEARCH_DICT = cache['search_dict']

CONFERENCES = gen_conferences_dict(list(cache['conference_sorted_pids']))
MOST_RECENT_CONFERENCE = sorted(list(CONFERENCES))[0]

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--prod', dest='prod', action='store_true', help='run in prod?')
    parser.add_argument('--port', dest='port', type=int, default=5000, help='port to serve on')
    args = parser.parse_args()
    print(args)
    if args.prod:
        # run on Tornado instead, since running raw Flask in prod is not recommended
        print('starting tornado!')
        from tornado.wsgi import WSGIContainer
        from tornado.httpserver import HTTPServer
        from tornado.ioloop import IOLoop
        from tornado.log import enable_pretty_logging
        enable_pretty_logging()
        http_server = HTTPServer(WSGIContainer(app))
        http_server.listen(args.port)
        IOLoop.instance().start()
    else:
        print('starting flask!')
        app.debug = False
        app.run(port=args.port, host='127.0.0.1')
