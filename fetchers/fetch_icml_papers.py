import bs4
import dateutil.parser
import sys
import urllib.request
from bs4 import BeautifulSoup
from tqdm import tqdm
from typing import List

sys.path.append('../')
from db_manager import DBManager

CONF_NAMES = ['ICML2019', 'ICML2018', 'ICML2017', 'ICML2016', 'ICML2015']
PMLR_VOLUMES = [97, 80, 70, 48, 37]


def main() -> None:
    db_manager = DBManager()
    base_url = 'http://proceedings.mlr.press/'
    for volume, conf_name in zip(PMLR_VOLUMES, CONF_NAMES):
        list_url = base_url + 'v{:d}/'.format(volume)
        fetch_papers(db_manager, base_url, list_url, conf_name, 'Main', conf_name)
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
    papers_meta_list = soup.find_all('div', {'class': 'paper'})
    titles_list = [flatten_content_list(m.find('p', {'class', 'title'}).contents) for m in papers_meta_list]
    authors_list = [format_authors(m.find('span', {'class': 'authors'}).string) for m in papers_meta_list]
    page_urls_list = [m.find_all('a')[0].get('href') for m in papers_meta_list]
    pdf_urls_list = [m.find_all('a')[1].get('href') for m in papers_meta_list]
    conf_year = conf_id[-4:]
    conf_date = dateutil.parser.parse(conf_year + '-06')
    # print(papers_meta_list[0])
    # print(page_urls_list[0])
    # print(pdf_urls_list[0])
    # print(authors_list[0])
    # print(titles_list[0])

    if (len(page_urls_list) == len(authors_list) and
            len(page_urls_list) == len(pdf_urls_list) and
            len(page_urls_list) == len(titles_list)):
        for i, page_url in enumerate(tqdm(page_urls_list)):
            pid = db_manager.create_paper_id(conf_id, conf_sub_id, titles_list[i])
            if not db_manager.exists(pid):
                try:
                    print(page_url)
                    with urllib.request.urlopen(page_url) as url:
                        response2 = url.read()
                    soup2 = BeautifulSoup(response2, 'html.parser')
                    summary = flatten_content_list(soup2.find('div', {'id': 'abstract'}).contents)
                    print(summary)

                    db_manager.add_paper(
                        conf_id, conf_sub_id, conf_sub_id.lower() != 'main',
                        conf_name, titles_list[i], authors_list[i],
                        page_urls_list[i], pdf_urls_list[i], conf_date, summary)
                except urllib.error.URLError:
                    print('Skipping {:} - URLError'.format(page_url))
            else:
                print('Skipping {:} - Exists'.format(page_url))
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


def format_authors(authors: str) -> List[str]:
    """ Tranforms the raw authors string into a list of authors. """
    authors_out = authors.replace('\n', '').replace('  ', '')
    authors_out = authors_out.split(',')
    authors_out = [a.strip() for a in authors_out]
    return authors_out


if __name__ == '__main__':
    main()
