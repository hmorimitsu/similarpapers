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
    base_url = 'https://bmvc2019.org'
    list_url = base_url + '/programme/detailed-programme/'
    fetch_papers(db_manager, base_url, list_url, 'BMVC2019', 'Main', 'BMVC2019')
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
    titles_list = [flatten_content_list(m.find('a').contents) for m in papers_meta_list]
    authors_list = [format_authors(m) for m in papers_meta_list]
    pdf_urls_list = [base_url + m.find('a').get('href') for m in papers_meta_list]
    conf_year = conf_id[-4:]
    conf_date = dateutil.parser.parse(conf_year + '-09')
    # print(papers_meta_list[0])
    # print(page_urls_list[0])
    # print(pdf_urls_list[0])
    # print(authors_list[0])
    # print(titles_list[0])

    if (len(titles_list) == len(authors_list) and
            len(titles_list) == len(pdf_urls_list)):
        for i in tqdm(range(len(titles_list))):
            pid = db_manager.create_paper_id(conf_id, conf_sub_id, titles_list[i])
            if not db_manager.exists(pid):
                print(titles_list[i])
                try:
                    summary = ''
                    page_url = ''

                    db_manager.add_paper(
                        conf_id, conf_sub_id, conf_sub_id.lower() != 'main',
                        conf_name, titles_list[i], authors_list[i],
                        page_url, pdf_urls_list[i], conf_date, summary)
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
    return out


def format_authors(authors: bs4.element.Tag) -> List[str]:
    """ Tranforms the raw authors string into a list of authors. """
    tags = authors.contents
    author_tag = None
    for t in tags:
        t = str(t).strip()
        if len(t) > 1 and '<' not in t:
            author_tag = t
            break
    assert author_tag is not None
    authors_out = remove_affiliation(author_tag)
    authors_out = authors_out.split(';')
    authors_out = [a.strip() for a in authors_out]
    return authors_out


def get_meta_list(soup: bs4.BeautifulSoup) -> List[bs4.element.Tag]:
    meta_list_tmp = soup.find_all('p')
    meta_list_tmp = [m for m in meta_list_tmp if m.find('a') is not None and m.find('b') is not None]
    meta_list = []
    for m in meta_list_tmp:
        try:
            int(m.find('b').contents[0].strip().replace('.', ''))
            meta_list.append(m)
        except ValueError:
            continue
    return meta_list


def remove_affiliation(author_str: str) -> str:
    clean_str = ''
    is_affil = False
    for i in range(len(author_str)):
        c = author_str[i]
        if c == '(':
            is_affil = True
        if not is_affil:
            clean_str += c
        elif c == ')':
            is_affil = False
    assert is_affil == False
    return clean_str


if __name__ == '__main__':
    main()
