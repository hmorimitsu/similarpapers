import bs4
import datetime
import dateutil.parser
import urllib.request
from bs4 import BeautifulSoup
from tqdm import tqdm
from typing import List

from db_manager import DBManager

CONFERENCES = [
    'ECCV2020'
]


def main():
    base_url = 'https://www.ecva.net/'
    db_manager = DBManager()

    for conf_id in CONFERENCES:
        list_url = base_url + 'papers.php'
        fetch_papers(db_manager, base_url, list_url, conf_id, 'Main', conf_id)
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
    titles_meta_list = soup.find_all('dt')
    full_page_urls_list = [base_url + m.find('a').get('href') for m in titles_meta_list]
    full_titles_list = [str(m.find('a').string).replace('\n', '') for m in titles_meta_list]

    authors_meta_list = soup.find_all('dd')
    full_authors_list = [format_authors(m) for m in authors_meta_list[::2]]
    full_pdf_urls_list = [base_url + m.find('a').get('href') for m in authors_meta_list[1::2]]
    full_pdf_urls_list = [m for m in full_pdf_urls_list if m.endswith('.pdf') and not '-supp' in m]

    authors_meta_list = soup.find_all('dd')

    conf_year = conf_id[-4:]
    conf_mask = [True if 'eccv_'+conf_year in p.lower() else False for p in full_page_urls_list]

    page_urls_list = []
    titles_list = []
    authors_list = []
    pdf_urls_list = []
    for i in range(len(conf_mask)):
        if conf_mask[i]:
            page_urls_list.append(full_page_urls_list[i])
            titles_list.append(full_titles_list[i])
            authors_list.append(full_authors_list[i])
            pdf_urls_list.append(full_pdf_urls_list[i])
    dates_list = [dateutil.parser.parse('2020-08') for _ in range(len(page_urls_list))]

    if (len(page_urls_list) == len(pdf_urls_list) and
            len(page_urls_list) == len(authors_list) and
            len(page_urls_list) == len(titles_list)):
        for i in tqdm(range(len(page_urls_list))):
            pid = db_manager.create_paper_id(conf_id, conf_sub_id, titles_list[i])
            if not db_manager.exists(pid):
                summary = get_abstract(page_urls_list[i])
                print(titles_list[i])
                print(summary)
                db_manager.add_paper(
                    conf_id, conf_sub_id, conf_sub_id.lower() != 'main',
                    conf_name, titles_list[i], authors_list[i], page_urls_list[i],
                    pdf_urls_list[i], dates_list[i], summary)
            else:
                print('Skipping {:} - exists'.format(page_urls_list[i]))
    else:
        print('SKIPPING!!! Wrong list sizes. ({:d}, {:d}, {:d}, {:d})'.format(
            len(page_urls_list), len(pdf_urls_list), len(authors_list),
            len(titles_list)))


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
    return out


def format_authors(authors: bs4.element.Tag) -> List[str]:
    """ Retrieves list of authors from the tag. """
    authors = str(authors).replace('<dd>', '').replace('</dd>', '').replace(', ', ',').strip()
    authors = authors.split(',')
    return authors


def get_abstract(page_url):
    """ Opens paper page and retrieves the abstract. """
    try:
        with urllib.request.urlopen(page_url) as url:
            response = url.read()
        soup = BeautifulSoup(response, 'html.parser')
        abstract = flatten_content_list(soup.find('div', {'id': 'abstract'}).contents)
        abstract = abstract.replace('\n', '')
        abstract = abstract.strip()
        return abstract
    except (urllib.error.HTTPError, urllib.error.URLError):
        print('Cannot open page', page_url)
        return 'Abstract not found.'


if __name__ == '__main__':
    main()
