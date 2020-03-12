import os
import time
import pickle
import shutil
import sys
import random
from  urllib.request import urlopen

sys.path.append('../')
from utils import Config, load_json_db

timeout_secs = 10 # after this many seconds we give up on a paper
have = []
if os.path.exists(Config.pdf_dir):
    conf_dirs = [f for f in os.listdir(Config.pdf_dir)
                 if os.path.isdir(os.path.join(Config.pdf_dir, f))]
    for cdir in conf_dirs:
        conf_sub_dirs = [
            f for f in os.listdir(os.path.join(Config.pdf_dir, cdir))
            if os.path.isdir(os.path.join(Config.pdf_dir, cdir, f))]
        for sdir in conf_sub_dirs:
            file_ids = os.listdir(os.path.join(Config.pdf_dir, cdir, sdir))
            file_ids = [os.path.join(cdir, sdir, f) for f in file_ids]
            have.extend(file_ids)
print('Have {:d} PDFs in our data folder'.format(len(have)))

os.makedirs('tmp', exist_ok=True)
numok = 0
numtot = 0
db = load_json_db()
db_keys = list(db)
random.shuffle(db_keys)
for key in db_keys:
    out_dir = os.path.join(Config.pdf_dir, db[key]['conf_id'], db[key]['conf_sub_id'])
    os.makedirs(out_dir, exist_ok=True)
    pdf_url = db[key]['pdf_url'].replace(' ', '%20')
    if db[key]['conf_id'].lower().startswith('aaai'):
        pdf_url = pdf_url.replace('/view/', '/download/')
    basename = pdf_url.split('/')[-1]
    fname = os.path.join(out_dir, basename)
    fid = os.path.join(db[key]['conf_id'], db[key]['conf_sub_id'], basename)

    # try retrieve the pdf
    numtot += 1
    try:
        if not fid in have:
            print('fetching {:} into {:}'.format(pdf_url, fname))
            req = urlopen(pdf_url, None, timeout_secs)
            with open('tmp/dowloading', 'wb') as fp:
                shutil.copyfileobj(req, fp)
            shutil.move('tmp/dowloading', fname)
            time.sleep(0.05 + random.uniform(0,0.1))
        else:
            print('{:} exists, skipping'.format(fname))
        numok+=1
    except Exception as e:
        print('error downloading: ', pdf_url)
        print(e)
    
    print('{:d}/{:d} of {:d} downloaded ok.'.format(numok, numtot, len(db)))
  
print('final number of papers downloaded okay: {:d}/{:d}'.format(numok, len(db)))
