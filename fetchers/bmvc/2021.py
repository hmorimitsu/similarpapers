import dateutil.parser
import sys
import urllib.request
import bs4
from bs4 import BeautifulSoup
from tqdm import tqdm
from typing import List

sys.path.append('../')
sys.path.append('../../')
from db_manager import DBManager

import pickle


def main() -> None:
    db_manager = DBManager()
    base_url = 'https://www.bmvc2021-virtualconference.com/'
    list_url = base_url + 'programme/accepted-papers/'
    fetch_papers(db_manager, base_url, list_url, 'BMVC2021', 'Main', 'BMVC2021')
    db_manager.write_db()


def fetch_papers(db_manager: DBManager,
                 base_url: str,
                 list_url: str,
                 conf_id: str,
                 conf_sub_id: str,
                 conf_name: str) -> None:
    """ Fetches the data of all the papers found at list_url and add them to
    the database, if the data is valid.
    """
    print(conf_name)
    print(conf_id, conf_sub_id)
    print(list_url)
    with urllib.request.urlopen(list_url) as url:
        response = url.read()
    soup = BeautifulSoup(response, 'html.parser')
    papers_meta_list = [m.find_all('td')[1] for m in [c for c in soup.find_all('tr') if 'id="paper' in str(c)]]
    titles_list = [m.find('strong').string.strip() for m in papers_meta_list]
    authors_list = [format_authors(str(m).strip()) for m in papers_meta_list]
    pdf_urls_list = [m.find('a', {'class': 'btn btn-info btn-sm mt-1'}).get('href') for m in papers_meta_list]
    conf_year = conf_id[-4:]
    conf_date = dateutil.parser.parse(conf_year + '-09')

    if (len(titles_list) == len(authors_list) and
            len(titles_list) == len(pdf_urls_list)):
        for i in tqdm(range(len(titles_list))):
            pid = db_manager.create_paper_id(conf_id, conf_sub_id, titles_list[i])
            if not db_manager.exists(pid):
                print(pdf_urls_list[i])
                print(titles_list[i])
                page_url = ''
                summary = ''

                db_manager.add_paper(
                    conf_id, conf_sub_id, conf_sub_id.lower() != 'main',
                    conf_name, titles_list[i], authors_list[i],
                    page_url, pdf_urls_list[i], conf_date, summary)
            else:
                print('Skipping {:} - Exists'.format(titles_list[i]))
    else:
        print('SKIPPING!!! Wrong list sizes. ({:d}, {:d}, {:d})'.format(
            len(pdf_urls_list), len(authors_list), len(titles_list)))


def flatten_content_list(content_list: List[bs4.element.NavigableString]) -> str:
    """ Tranforms a list of NavigableString into a string. """
    out = ''
    for c in content_list:
        stack = [c]
        while len(stack) > 0:
            tag = stack.pop()
            if tag.string is not None:
                out += tag.string.replace('\n', ' ').replace('  ', '')
            else:
                stack.extend(tag.contents)
    if out.lower().startswith('abstract:'):
        out = out[9:]
    return out.strip()


def format_authors(authors: str) -> List[str]:
    """ Tranforms the raw authors string into a list of authors. """
    i = authors.find('<br/>')
    authors = authors[i+5:]
    i = authors.find('<br/>')
    authors = authors[:i]
    authors = authors.replace(' and', ',')
    authors = [a.strip() for a in authors.split(',')]
    return authors


if __name__ == '__main__':
    main()
