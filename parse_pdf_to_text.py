"""
Very simple script that simply iterates over all files data/pdf/f.pdf
and create a file data/txt/f.pdf.txt that contains the raw text, extracted
using the "pdftotext" command. If a pdf cannot be converted, this
script will not produce the output file.
"""

import os
import sys
import time
import shutil

from utils import Config

# make sure pdftotext is installed
if not shutil.which('pdftotext'): # needs Python 3.3+
    print('ERROR: you don\'t have pdftotext installed. Install it first before calling this script')
    sys.exit()

files = []
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
            files.extend(file_ids)
print('Have {:d} PDFs in our data folder'.format(len(files)))

have = []
if os.path.exists(Config.txt_dir):
    conf_dirs = [f for f in os.listdir(Config.txt_dir)
                 if os.path.isdir(os.path.join(Config.txt_dir, f))]
    for cdir in conf_dirs:
        conf_sub_dirs = [
            f for f in os.listdir(os.path.join(Config.txt_dir, cdir))
            if os.path.isdir(os.path.join(Config.txt_dir, cdir, f))]
        for sdir in conf_sub_dirs:
            file_ids = os.listdir(os.path.join(Config.txt_dir, cdir, sdir))
            file_ids = [os.path.join(cdir, sdir, f) for f in file_ids]
            have.extend(file_ids)
print('Have {:d} TXTs in our data folder'.format(len(have)))

for i, f in enumerate(files): # there was a ,start=1 here that I removed, can't remember why it would be there. shouldn't be, i think.
    os.makedirs(os.path.join(Config.txt_dir, os.path.split(f)[0]), exist_ok=True)
    txt_basename = f + '.txt'
    if txt_basename in have:
        print('%d/%d skipping %s, already exists.' % (i+1, len(files), txt_basename, ))
        continue

    pdf_path = os.path.join(Config.pdf_dir, f)
    txt_path = os.path.join(Config.txt_dir, txt_basename)
    cmd = "pdftotext %s %s" % (pdf_path, txt_path)
    os.system(cmd)

    print('%d/%d %s' % (i+1, len(files), cmd))

    # check output was made
    if not os.path.isfile(txt_path):
        # there was an error with converting the pdf
        print('there was a problem with parsing %s to text, creating an empty text file.' % (pdf_path, ))
        os.system('touch ' + txt_path) # create empty file, but it's a record of having tried to convert

    time.sleep(0.01) # silly way for allowing for ctrl+c termination
