import bs4
import datetime
import dateutil.parser
import urllib.request
from bs4 import BeautifulSoup
from tqdm import tqdm
from typing import List

from db_manager import DBManager

CONFERENCES = [
    'ACCV2020',
    'CVPR2022', 'CVPR2021', 'CVPR2020', 'CVPR2019', 'CVPR2018', 'CVPR2017', 'CVPR2016', 'CVPR2015',
    'ICCV2021', 'ICCV2019', 'ICCV2017', 'ICCV2015',
    'ECCV2020', 'ECCV2018',
    'WACV2022', 'WACV2021', 'WACV2020',
    'ACCV2020_workshops',
    'CVPR2022_workshops', 'CVPR2021_workshops', 'CVPR2020_workshops', 'CVPR2019_workshops', 'CVPR2018_workshops', 'CVPR2017_workshops', 'CVPR2016_workshops', 'CVPR2015_workshops',
    'ICCV2019_workshops', 'ICCV2017_workshops', 'ICCV2015_workshops',
    'ECCV2018_workshops',
    'WACV2022_workshops', 'WACV2021_workshops', 'WACV2020_workshops',
]


def main():
    base_url = 'http://openaccess.thecvf.com/'
    db_manager = DBManager()

    for conf_id in CONFERENCES:
        if 'workshop' in conf_id.lower():
            fetch_workshop_papers(db_manager, base_url, conf_id)
        else:
            list_url = base_url + conf_id
            with urllib.request.urlopen(list_url) as url:
                response = url.read()
            soup = BeautifulSoup(response, 'html.parser')
            days_links = [str(m.find('a').get('href')) for m in soup.find_all('dd')]
            days_links = [d[d.find('?'):] for d in days_links]
            all_days = [d for d in days_links if 'day=all' in d]
            if len(all_days) == 1:
                days_links = all_days
            else:
                days_links = [d for d in days_links if len(d) > 1]
                if len(days_links) == 0:
                    days_links = ['']
            for dl in days_links:
                fetch_papers(db_manager, base_url, list_url+dl, conf_id, 'Main', conf_id)
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
    papers_meta_list1 = soup.find_all('dt')
    page_urls_list = []
    for m in papers_meta_list1:
        link = m.find('a').get('href')
        if link[0] == '/':
            link = link[1:]
        page_urls_list.append(base_url + link)
    titles_list = [str(m.find('a').string) for m in papers_meta_list1]
    papers_meta_list2 = soup.find_all('dd')
    print(list_url, 'day=all' in list_url)
    if 'day=all' in list_url:
        papers_meta_list2 = papers_meta_list2[1:]
        authors_list = [format_authors(m) for m in papers_meta_list2[::2]]
        authors_list = authors_list[:-1]
    else:
        authors_list = [format_authors(m) for m in papers_meta_list2[::2]]
    pdf_urls_list = []
    for m in papers_meta_list2[1::2]:
        link = m.find('a').get('href')
        if link[0] == '/':
            link = link[1:]
        pdf_urls_list.append(base_url + link)
    dates_list = [format_date(m.find('div', {'class', 'bibref'})) for m in papers_meta_list2[1::2]]
    print(titles_list[0])
    print(authors_list[0])
    print(pdf_urls_list[0])
    print(dates_list[0])
    sds

    if (len(page_urls_list) == len(pdf_urls_list) and
            len(page_urls_list) == len(authors_list) and
            len(page_urls_list) == len(titles_list)):
        for i in tqdm(range(len(page_urls_list))):
            pid = db_manager.create_paper_id(conf_id, conf_sub_id, titles_list[i])
            if not db_manager.exists(pid):
                summary = get_abstract(page_urls_list[i])
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


def fetch_workshop_papers(db_manager: DBManager,
                          base_url: str,
                          conf_id: str) -> None:
    """ Fetches data from workshop papers. """
    main_conf_id = conf_id.replace('_workshops', '')
    page_url = base_url + conf_id + '/menu'
    print('Workshop: ' + page_url)
    with urllib.request.urlopen(page_url) as url:
        response = url.read()
    soup = BeautifulSoup(response, 'html.parser')
    workshops_meta_list = soup.find_all('dd')
    workshop_ids_list = []
    for m in workshops_meta_list:
        id_link = m.find('a').get('href')
        if '.py' in id_link:
            id_link = id_link.replace('.py', '').replace(' ', '_')
        else:
            id_link = id_link.split('/')[-1]
        workshop_ids_list.append(id_link)
    workshop_names_list = [str(m.find('a').string) for m in workshops_meta_list]
    workshop_names_list = [conf_id + ' - ' + n for n in workshop_names_list]
    for i in range(len(workshop_names_list)):
        workshop_base_url = base_url + conf_id + '/'
        list_url = workshop_base_url + workshop_ids_list[i]
        conf_sub_id = workshop_ids_list[i]
        conf_sub_id = conf_sub_id[conf_sub_id.find('_')+1:]
        if conf_sub_id.lower() == '../menu':
            continue
        fetch_papers(db_manager, base_url, list_url, main_conf_id, conf_sub_id, workshop_names_list[i])
        db_manager.write_db()


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
    authors_out = authors.find_all('a')
    authors_out = [str(a.string).strip() for a in authors_out]
    return authors_out


def format_date(bibtex_entry: bs4.element.Tag) -> datetime.datetime:
    """ Gets the date from the bibtex entry. """
    cont = bibtex_entry.contents
    if len(cont) == 1:
        cont = cont[0].split('\n')
    lines = []
    for c in cont:
        try:
            lines.append(c.replace('\n', ''))
        except TypeError:
            continue
    for l in lines:
        if l.strip().startswith('month'):
            month_line = l
        elif l.strip().startswith('year'):
            year_line = l
    start = month_line.find('{')
    end = month_line.find('}')
    month = month_line[start+1:end]
    start = year_line.find('{')
    end = year_line.find('}')
    year = int(year_line[start+1:end])  # Cast to int just as a safety check
    date = dateutil.parser.parse(str(year)+'-'+month)
    return date


def get_abstract(page_url):
    """ Opens paper page and retrieves the abstract. """
    try:
        print('page_url', page_url)
        with urllib.request.urlopen(page_url) as url:
            response = url.read()
        soup = BeautifulSoup(response, 'html.parser')
        abstract = flatten_content_list(soup.find('div', {'id': 'abstract'}).contents)
        abstract = abstract.replace('\n', '')
        return abstract.strip()
    except (urllib.error.HTTPError, urllib.error.URLError):
        print('Cannot open page', page_url)
        return 'Abstract not found.'


if __name__ == '__main__':
    main()
