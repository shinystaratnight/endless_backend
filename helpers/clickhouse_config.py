import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def clickhouse_config():
    from xml.etree import ElementTree as et

    conf = get_env()
    with open(os.path.join(BASE_DIR, 'conf/templates/users.xml'), 'r') as templ_conf_file:
        tree = et.parse(templ_conf_file)
        tree.find('.//USER_FROM_ENV/password').text = conf['LOGGER_PASSWORD']
        tree.find('.//USER_FROM_ENV').tag = conf['LOGGER_USER']

        with open(os.path.join(BASE_DIR, 'users.xml'), 'w') as conf_file:
            tree.write(conf_file)
        print("Clickhouse users config file was build.")
        return


def get_env():
    conf = {}
    configs = ['env_defaults',]
    for config in configs:
        with open(os.path.join(BASE_DIR, config), 'r') as f:
            for line in f.readlines():
                if not line.strip():
                    continue
                var, value = line.split('=', 1)
                conf[var.strip()] = value.strip().strip('"')
    return conf


if __name__ == '__main__':
    clickhouse_config()
