import bs4
import dateutil.parser
import sys
import urllib.request
from bs4 import BeautifulSoup
from tqdm import tqdm
from typing import List

sys.path.append('../')
sys.path.append('../../')
from db_manager import DBManager

import pickle


def main() -> None:
    db_manager = DBManager()
    base_url = 'https://www.bmvc2020-conference.com/'
    list_url = '../html/BMVC2020.html'
    fetch_papers(db_manager, base_url, list_url, 'BMVC2020', 'Main', 'BMVC2020')
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
    with open(list_url, 'r') as f:
        response = f.read()
    soup = BeautifulSoup(response, 'html.parser')
    papers_meta_list = soup.find_all('div', {'class': 'myCard col-xs-6 col-md-4'})
    page_urls_list = [m.find('a', {'class': 'text-muted'}).get('href') for m in papers_meta_list]
    titles_list = [m.find('h5', {'class': 'card-title'}).string.strip() for m in papers_meta_list]
    authors_list = [format_authors(m.find('h6', {'class': 'card-subtitle text-muted'}).string.strip()) for m in papers_meta_list]
    conf_year = conf_id[-4:]
    conf_date = dateutil.parser.parse(conf_year + '-09')
    # print(papers_meta_list[0])
    # print(page_urls_list[0])
    # print(pdf_urls_list[0])
    # print(authors_list[0])
    # print(titles_list[0])

    if (len(titles_list) == len(authors_list) and
            len(titles_list) == len(page_urls_list)):
        for i in tqdm(range(len(titles_list))):
            pid = db_manager.create_paper_id(conf_id, conf_sub_id, titles_list[i])
            if not db_manager.exists(pid):
                print(page_urls_list[i])
                print(titles_list[i])
                try:
                    with urllib.request.urlopen(page_urls_list[i]) as url:
                        response2 = url.read()
                    soup2 = BeautifulSoup(response2, 'html.parser')
                    pdf_url = soup2.find_all('a', {'class': 'btn btn-info btn-sm mt-1'})
                    pdf_url = [p.get('href') for p in pdf_url]
                    pdf_url = [p for p in pdf_url if '/papers/' in p][0]
                    summary = flatten_content_list(soup2.find('div', {'class': 'col-12 col-lg-8'}).find('p'))
                    print(pdf_url)
                    print(summary)

                    db_manager.add_paper(
                        conf_id, conf_sub_id, conf_sub_id.lower() != 'main',
                        conf_name, titles_list[i], authors_list[i],
                        page_urls_list[i], pdf_url, conf_date, summary)
                except urllib.error.URLError:
                    print('Skipping {:} - URLError'.format(titles_list[i]))
            else:
                print('Skipping {:} - Exists'.format(titles_list[i]))
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
    if out.lower().startswith('abstract:'):
        out = out[9:]
    return out.strip()


def format_authors(authors: bs4.element.Tag) -> List[str]:
    """ Tranforms the raw authors string into a list of authors. """
    authors = str(authors)
    authors = authors.replace('\n', '').replace('  ', ' ').replace(', ', ',')
    authors_out = authors.split(',')
    authors_out = [a.strip() for a in authors_out]
    return authors_out


if __name__ == '__main__':
    main()
