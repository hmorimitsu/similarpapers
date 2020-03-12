import pickle

from utils import Config, dump_db_as_json


def main():
    db = pickle.load(open(Config.db_path, 'rb'))
    dump_db_as_json(db)


if __name__ == '__main__':
    main()
