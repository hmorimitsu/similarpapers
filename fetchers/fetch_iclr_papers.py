import bs4
import dateutil.parser
import sys
import urllib.request
from bs4 import BeautifulSoup
from tqdm import tqdm
from typing import List

sys.path.append('../')
from db_manager import DBManager

CONF_NAMES = ['ICLR2019', 'ICLR2018', 'ICLR2017', 'ICLR2016', 'ICLR2015']
LIST_LINKS = {
    'ICLR2019': 'https://iclr.cc/Conferences/2019/Schedule',
    'ICLR2018': 'https://iclr.cc/Conferences/2018/Schedule',
    'ICLR2017': 'iclr17.html',  # ICLR 2017 page is generated on-the-fly, so we use a cached version
    'ICLR2016': 'https://iclr.cc/archive/www/doku.php%3Fid=iclr2016:accepted-main.html',
    'ICLR2015': 'https://iclr.cc/archive/www/doku.php%3Fid=iclr2015:accepted-main.html'
}


def main() -> None:
    db_manager = DBManager()
    for conf_name in CONF_NAMES:
        list_url = LIST_LINKS[conf_name]
        fetch_papers(db_manager, list_url, conf_name, 'Main', conf_name)
        db_manager.write_db()


def fetch_papers(db_manager: DBManager,
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
    conf_year = int(conf_id[-4:])
    if conf_year not in [2017]:
        with urllib.request.urlopen(list_url) as url:
            response = url.read()
    else:
        with open(list_url, 'r') as f:
            response = f.read()
    soup = BeautifulSoup(response, 'html.parser')
    if conf_year in [2019, 2018]:
        papers_meta_list = (
            soup.find_all('div', {'class': 'maincard narrower Oral'}) +
            soup.find_all('div', {'class': 'maincard narrower Poster'}))
        for i in range(len(papers_meta_list)-1, -1, -1):
            if papers_meta_list[i].find('a', {'title': 'PDF'}) is None:
                del papers_meta_list[i]
        titles_list = [flatten_content_list(m.find('div', {'class', 'maincardBody'}).contents) for m in papers_meta_list]
        authors_list = [format_authors(m.find('div', {'class': 'maincardFooter'}).string, conf_year) for m in papers_meta_list]
        page_urls_list = [m.find('a', {'title': 'PDF'}).get('href') for m in papers_meta_list]
    elif conf_year in [2017]:
        papers_meta_list = soup.find_all('div', {'class': 'note panel'})
        page_urls_list = ['https://openreview.net' + m.find_all('a')[0].get('href') for m in papers_meta_list]
        titles_list = [flatten_content_list(m.find_all('a')[0].contents) for m in papers_meta_list]
        authors_list = [format_authors(m.find('span', {'class': 'signatures'}).find_all('a'), conf_year) for m in papers_meta_list]
    elif conf_year in [2016, 2015]:
        papers_meta_list = soup.find_all('li', {'class': 'level1'})[1:]
        page_urls_list = [m.find('a', {'class': 'urlextern'}).get('href') for m in papers_meta_list]
        titles_list = [flatten_content_list(m.find('a', {'class': 'urlextern'}).contents) for m in papers_meta_list]
        authors_list = [format_authors(m.find('div', {'class': 'li'}).contents[-1], conf_year) for m in papers_meta_list]
    conf_date = dateutil.parser.parse(conf_id[-4:] + '-05')
    # print(papers_meta_list[0])
    # print(page_urls_list[0])
    # print(authors_list[0])
    # print(titles_list[0])

    if (len(page_urls_list) == len(authors_list) and\
            len(page_urls_list) == len(titles_list)):
        for i, page_url in enumerate(tqdm(page_urls_list)):
            if len(page_url) < 2:
                continue
            pid = db_manager.create_paper_id(conf_id, conf_sub_id, titles_list[i])
            if not db_manager.exists(pid):
                try:
                    print(page_url)
                    with urllib.request.urlopen(page_url) as url:
                        response2 = url.read()
                    soup2 = BeautifulSoup(response2, 'html.parser')
                    try:
                        if conf_year in [2019, 2018, 2017]:
                            pdf_url = 'https://openreview.net' + soup2.find('a', {'class': 'note_content_pdf'}).get('href')
                            summary = flatten_content_list(soup2.find('span', {'class', 'note-content-value'}).contents)
                        elif conf_year in [2016, 2015]:
                            pdf_url = 'https://arxiv.org' + soup2.find('a', {'accesskey': 'f'}).get('href')
                            summary = flatten_content_list(soup2.find('blockquote', {'class', 'abstract mathjax'}).contents[1:])
                    except AttributeError:
                        # Some links don't have PDF
                        continue
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
                out += tag.string.replace('\n', ' ').replace('  ', '').replace('"', '')
            else:
                stack.extend(tag.contents)
    return out


def format_authors(authors: str,
                   conf_year: int) -> List[str]:
    """ Tranforms the raw authors string into a list of authors. """
    if conf_year in [2019, 2018]:
        authors_out = authors.replace(' · ', ',')
        authors_out = authors_out.split(',')
        authors_out = [a.strip() for a in authors_out]
    elif conf_year in [2017]:
        authors_out = [str(a.string) for a in authors]
    elif conf_year in [2016, 2015]:
        if authors.startswith(','):
            authors = authors[1:]
        authors_out = authors.replace('\n', '').replace(', and ', ',').replace(' and ', ',').replace('  ', '')
        authors_out = authors_out.split(',')
        authors_out = [a.strip() for a in authors_out]
    return authors_out


if __name__ == '__main__':
    main()
