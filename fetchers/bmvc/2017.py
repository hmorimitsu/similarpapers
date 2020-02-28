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


def main() -> None:
    db_manager = DBManager()
    base_url = 'http://www.bmva.org/bmvc/2017/'
    list_url = base_url + 'toc.html'
    fetch_papers(db_manager, base_url, list_url, 'BMVC2017', 'Main', 'BMVC2017')
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
    papers_meta_list = get_meta_list(soup)
    titles_list = [flatten_content_list(m.find('span', {'class', 'title'}).contents) for m in papers_meta_list]
    authors_list = [format_authors(m.find('span', {'class', 'authors'})) for m in papers_meta_list]
    page_urls_list = [base_url + m.find('a').get('href') for m in papers_meta_list]
    conf_year = conf_id[-4:]
    conf_date = dateutil.parser.parse(conf_year + '-09')
    # print(papers_meta_list[0])
    # print(page_urls_list[0])
    # print(pdf_urls_list[0])
    # print(authors_list[0])
    # print(titles_list[0])

    if (len(titles_list) == len(authors_list) and
            len(titles_list) == len(page_urls_list)):
        for i, page_url in enumerate(tqdm(page_urls_list)):
            pid = db_manager.create_paper_id(conf_id, conf_sub_id, titles_list[i])
            if not db_manager.exists(pid):
                print(page_url)
                paper_id = page_url.split('/')[-2]
                pdf_url = page_url.replace('index.html', paper_id + '.pdf')
                summary = get_summary(page_url)
                print(summary)

                db_manager.add_paper(
                    conf_id, conf_sub_id, conf_sub_id.lower() != 'main',
                    conf_name, titles_list[i], authors_list[i],
                    page_urls_list[i], pdf_url, conf_date, summary)
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


def format_authors(authors: bs4.element.Tag) -> List[str]:
    """ Tranforms the raw authors string into a list of authors. """
    authors_out = str(authors.text).replace(' and ', ',')
    authors_out = authors_out.split(',')
    authors_out = [a.strip() for a in authors_out]
    return authors_out


def get_meta_list(soup: bs4.BeautifulSoup) -> List[bs4.element.Tag]:
    meta_list = soup.find_all('li')
    meta_list = [
        m for m in meta_list
        if (m.find('a') is not None and
            len(m.find('a').get('href')) > 0 and
            m.find('span', {'class', 'title'}) is not None and
            m.find('span', {'class', 'authors'}) is not None)]
    return meta_list


def get_summary(page_url: str) -> str:
    summary = ''
    try:
        with urllib.request.urlopen(page_url) as url:
            response = url.read()
        soup = BeautifulSoup(response, 'html.parser')
        summary = soup.find_all('div', {'class': 'container'})
        summary = [s for s in summary if s.find('span', {'class': 'authorlist'}) is not None][0]
        found_summary_title = False
        found_summary_content = False
        for s in summary.contents:
            if found_summary_title:
                s = s.strip()
                if len(s) > 50:
                    summary = s
                    found_summary_content = True
            if 'Abstract' in s:
                found_summary_title = True
            if found_summary_content:
                break
        summary = summary.replace('\n', ' ')
        while summary.find('  ') >= 0:
            summary = summary.replace('  ', ' ')
    except urllib.error.URLError:
        print('Skipping {:} - URLError'.format(page_url))
    return summary


if __name__ == '__main__':
    main()
