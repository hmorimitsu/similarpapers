import bs4
import dateutil.parser
import sys
import urllib.request
from bs4 import BeautifulSoup
from tqdm import tqdm
from typing import List

sys.path.append('../')
from db_manager import DBManager


CONF_LINKS = ['paper/2021', 'paper/2020']
CONF_NAMES = ['NeurIPS2021', 'NeurIPS2020']


def main() -> None:
    db_manager = DBManager()
    base_url = 'https://papers.nips.cc'
    for conf_link, conf_name in zip(CONF_LINKS, CONF_NAMES):
        list_url = base_url + '/' + conf_link
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
    papers_meta_list = soup.find('div', {'class', 'container-fluid'}).find_all('li')
    page_urls_list = [base_url + m.find('a').get('href') for m in papers_meta_list]
    titles_list = [str(m.find('a').string) for m in papers_meta_list]
    authors_list = [format_authors(m.find('i').string) for m in papers_meta_list]
    conf_date = dateutil.parser.parse(conf_id[-4:] + '-12')

    if (len(page_urls_list) == len(titles_list) and
            len(page_urls_list) == len(authors_list)):
        for i, page_url in enumerate(tqdm(page_urls_list)):
            pid = db_manager.create_paper_id(conf_id, conf_sub_id, titles_list[i])
            if not db_manager.exists(pid):
                try:
                    with urllib.request.urlopen(page_url) as url:
                        response2 = url.read()
                    soup2 = BeautifulSoup(response2, 'html.parser')
                    pdf_url = soup2.find('div', {'class', 'container-fluid'}).find_all('a')
                    pdf_url = [p.get('href') for p in pdf_url]
                    pdf_url = base_url + [p for p in pdf_url if p.lower().endswith('paper.pdf')][0]
                    summary = soup2.find('div', {'class', 'container-fluid'}).find_all('p')[-1]
                    summary = flatten_content_list(summary.contents)
                    print(titles_list[i])
                    print(authors_list[i])
                    print(page_urls_list[i])
                    print(pdf_url)
                    print(summary)
                    db_manager.add_paper(
                        conf_id, conf_sub_id, conf_sub_id.lower() != 'main',
                        conf_name, titles_list[i], authors_list[i],
                        page_urls_list[i], pdf_url, conf_date, summary)
                except urllib.error.URLError:
                    print('Skipping {:} - URLError'.format(page_url))
            else:
                print('Skipping {:} - Exists'.format(page_url))
    else:
        print('SKIPPING!!! Wrong list sizes. ({:d}, {:d}, {:d})'.format(
            len(page_urls_list), len(titles_list), len(authors_list)))


def flatten_content_list(content_list: List[bs4.element.NavigableString]) -> str:
    """ Tranforms a list of NavigableString into a string. """
    out = ''
    for c in content_list:
        stack = [c]
        while len(stack) > 0:
            tag = stack.pop()
            if tag.string is not None:
                out += tag.string.replace('\n', ' ').replace('  ', '').replace('<p>', '').replace('</p>', '')
            else:
                stack.extend(tag.contents)
    return out


def format_authors(authors: str) -> List[str]:
    """ Tranforms the raw authors string into a list of authors. """
    authors = authors.replace('  ', ' ').replace(', ', ',')
    authors = authors.split(',')
    authors_out = [a.strip() for a in authors]
    return authors_out


if __name__ == '__main__':
    main()
