from argparse import ArgumentParser, Namespace
from distutils.command.clean import clean
import json
from pathlib import Path

from tqdm import tqdm

KNOWN_CODE_SITES = ['github.com', 'gitlab.com']


def _init_parser() -> ArgumentParser:
    parser: ArgumentParser = ArgumentParser()
    parser.add_argument('--json_dir', type=str, default='data/json')
    parser.add_argument('--txt_dir', type=str, default='data/txt')
    parser.add_argument('--output_dir', type=str, default='data/code_links')
    return parser


def main(args: Namespace) -> None:
    json_paths = sorted(list(Path(args.json_dir).glob('*.json')))

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for jpath in json_paths:
        print(jpath.stem)
        with open(jpath, 'r') as f:
            conf_meta = json.load(f)

        output_path = output_dir / jpath.stem

        not_found = 0
        with open(output_path, 'w') as fout:
            for paper_id, paper_info in tqdm(conf_meta.items()):
                conf_meta[paper_id]['code_link'] = ''
                basename = paper_info['pdf_url'].split('/')[-1]
                txt_path = Path(args.txt_dir) / paper_info['conf_id'] / paper_info['conf_sub_id'] / f'{basename}.txt'
                if txt_path.exists():
                    with open(txt_path, 'r') as f:
                        txt = f.read()
                    txt = txt.replace('\r\n', '\n').replace('\n', ' ')
                    words = txt.split(' ')
                    code_links = [w for w in words if is_code_link(w)]
                    code_links = clean_code_links(code_links)
                    if len(code_links) > 0:
                        fout.write(f'{paper_id} {" ".join(c for c in code_links)}\n')
                        if len(code_links) == 1:
                            conf_meta[paper_id]['code_link'] = code_links[0]
                else:
                    not_found += 1

        if not_found > 0:
            print(f'Skipped {not_found} papers because the txt file was not found.')

        with open(jpath, 'w') as f:
            json.dump(conf_meta, f, indent=2)


def clean_code_links(code_links):
    clean_code_links = []
    for i, link in enumerate(code_links):
        while not is_alphanum(link[-1]):
            link = link[:-1]
        start = max([link.find(site) for site in KNOWN_CODE_SITES])
        link = link[start:]
        tokens = link.split('/')
        if len(tokens) == 3 and min([len(t) for t in tokens]) > 0:  # A valid link is github.com/username/reponame
            clean_code_links.append(f'https://{link}')
    return clean_code_links


def is_alphanum(c):
    if (ord('a') <= ord(c) <= ord('z')) or (ord('A') <= ord(c) <= ord('Z')) or (ord('0') <= ord(c) <= ord('9')):
        return True
    return False


def is_code_link(word):
    for site in KNOWN_CODE_SITES:
        if site in word:
            return True
    return False


if __name__ == '__main__':
    parser: ArgumentParser = _init_parser()
    args: Namespace = parser.parse_args()
    main(args)
