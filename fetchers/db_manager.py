import sys
from datetime import datetime
from typing import List

sys.path.append('../')
from utils import dump_db_as_json, load_json_db


class DBManager(object):
    """ Handles operations with the paper database. """
    def __init__(self,
                 save_interval: int = 100) -> None:
        self.save_interval = save_interval
        self.counter = 0

        # lets load the existing database to memory
        try:
            self.db = load_json_db()
        except Exception as e:
            print('error loading existing database:')
            print(e)
            print('starting from an empty database')
            self.db = {}
        print('database has {:d} entries at start'.format(len(self.db)))

    def add_paper(self,
                  conf_id: str,
                  conf_sub_id: str,
                  is_workshop: bool,
                  conf_name: str,
                  title: str,
                  authors: List[str],
                  page_url: str,
                  pdf_url: str,
                  published_date: datetime,
                  summary: str) -> None:
        """ Adds a paper to the database, if the data is valid. """
        pid = self.create_paper_id(conf_id, conf_sub_id, title)
        if not self.exists(pid):
            if self.check_values(
                    conf_id, conf_sub_id, is_workshop, conf_name, title,
                    authors, page_url, pdf_url, published_date, summary):
                self.db[pid] = {
                    'conf_id': conf_id,
                    'conf_sub_id': conf_sub_id,
                    'is_workshop': is_workshop,
                    'conf_name': conf_name,
                    'title': title,
                    'authors': authors,
                    'page_url': page_url,
                    'pdf_url': pdf_url,
                    'published': published_date.strftime('%Y-%m'),
                    'summary': summary}
                self.counter += 1
                if self.counter % (self.save_interval - 1) == 0:
                    self.write_db()
        else:
            print('Skipping {:} - exists'.format(pdf_url))

    def check_values(self,
                     conf_id: str,
                     conf_sub_id: str,
                     is_workshop: bool,
                     conf_name: str,
                     title: str,
                     authors: List[str],
                     page_url: str,
                     pdf_url: str,
                     published_date: datetime,
                     summary: str) -> bool:
        """ Roughly checks if the provided data is valid. """
        is_correct = True
        try:
            int(conf_id[-4:])
        except ValueError:
            print('The last 4 characters in conf_id must be the year: ' + conf_id)
            is_correct = False
        if len(conf_sub_id) == 0:
            print("conf_sub_id cannot be empty, for the main conference, set conf_sub_id='Main'")
            is_correct = False
        if len(conf_name) == 0:
            print('conf_name cannot be empty')
            is_correct = False
        if len(title) == 0:
            print('title cannot be empty')
            is_correct = False
        if len(authors) == 0:
            print('There must be at least one author')
            is_correct = False
        if not isinstance(authors, list):
            print('authors must be a list')
            is_correct = False
        for a in authors:
            if len(a) == 0:
                print('Author name cannot be empty')
                is_correct = False
        if len(page_url) == 0:
            print('Warning: page_url is empty')
        if len(pdf_url) == 0:
            print('Incorrect pdf_url')
            is_correct = False
        if len(summary) > 0 and len(summary) < 50:
            print('Incorrect summary (abstract). It must be either an empty string or have more than 50 characters')
            is_correct = False
        if not is_correct:
            print('Incorrect value found when processing ' + pdf_url)
        return is_correct

    def create_paper_id(self,
                        conference_id: str,
                        conference_sub_id: str,
                        paper_title: str) -> str:
        """ Creates a string ID for the paper """
        return self.remove_extra_chars(
            conference_id.lower() + '_' + conference_sub_id.lower() + '_' +
            paper_title.lower())

    def exists(self,
               pid: str) -> bool:
        """ Checks if paper already exists in the database. """
        return (self.db.get(pid) is not None)

    def remove_extra_chars(self,
                           text: str) -> str:
        extras = [' ', '\'', '"', '~', '`', '^', ':']
        for c in extras:
            if c in text:
                text = text.replace(c, '')
        return text

    def write_db(self) -> None:
        """ Writes database to disk. """
        print('Saving db as JSON to disk with {:d} entries'.format(len(self.db)))
        dump_db_as_json(self.db)
