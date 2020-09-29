# -*- coding: utf-8 -*-
import re
import shelve

try:
    from pathlib import Path

    Path().expanduser()
except (ImportError, AttributeError):
    from pathlib2 import Path  # Patch for Python 2.x

import requests
import mechanicalsoup
import demjson

DATA_DIR = Path.home().joinpath(".uricli")
if not DATA_DIR.exists():
    DATA_DIR.mkdir()

SHELVE_PATH = str(DATA_DIR.joinpath('config'))


def restore_session():
    session = requests.session()
    with shelve.open(SHELVE_PATH) as db:
        if not db.get("cookies", None):
            cookies = requests.utils.cookiejar_from_dict(db["cookies"])
            session.cookies = cookies

    return session


def save_session(session):
    cookies = requests.utils.dict_from_cookiejar(session.cookies)
    with shelve.open(SHELVE_PATH) as db:
        db["cookies"] = cookies
        db.sync()


def get_browser():
    browser = mechanicalsoup.StatefulBrowser(session=restore_session())
    return browser


def submit(solution_path, problem_id):
    if problem_id is None:
        problem_id = int(Path(solution_path).resolve().stem)

    with open(solution_path, 'r') as f:
        source_code = f.read()

    language = get_language()

    browser = get_browser()
    browser.open("https://www.urionlinejudge.com.br/judge/en/runs/add")
    ensure_logged_in(browser)

    browser.select_form('form[method="post"]')

    browser['problem_id'] = problem_id
    browser['source_code'] = source_code
    browser['language_id'] = language

    browser.submit_selected()
    print_toast(browser)


def print_toast(browser):
    html = str(browser.get_current_page())
    toast_data = re.findall("show\((\{[^\})]+\})", html)
    if toast_data:
        toast_data = demjson.decode(toast_data[0])
        print(toast_data['message'] + " vc pode acompanhar o status da sua submissao no link:\n\033[1;32;48m" + str(browser.get_url()) + '\033[1;37;0m')


def set_login(email, password):
    with shelve.open(SHELVE_PATH) as db:
        db['email'] = email
        db['password'] = password
        db['cookies'] = None
        db.sync()


def get_login():
    with shelve.open(SHELVE_PATH) as db:
        if "email" not in db or "password" not in db:
            raise Exception("Must set email and password first.")

        return db['email'], db['password']


def ensure_logged_in(browser):
    email, password = get_login()

    if "/login" in browser.get_url():
        browser.select_form('form[action$="/judge/en/login?redirect=%2Fen%2Fruns%2Fadd"]')
        browser['email'] = email
        browser['password'] = password
        browser['remember_me'] = 1
        browser.submit_selected()

    if "/login" in browser.get_url():
        print_toast(browser)
        raise RuntimeError("Failed to login.")

    save_session(browser.session)


def list_languages():
    browser = get_browser()
    browser.open("https://www.urionlinejudge.com.br/judge/en/runs/add")
    ensure_logged_in(browser)

    browser.select_form('form[method="post"]')
    select = browser.get_current_page().find("select", {"name": "language_id"})
    options = select.find_all("option")
    options.sort(key=lambda a: int(a.attrs['value']))

    return [
        (option.attrs['value'], option.text)
        for option in options
    ]


def get_language():
    with shelve.open(SHELVE_PATH) as db:
        if 'language_id' not in db:
            raise Exception("Must set language first.")
        return db['language_id']


def set_language(language_id):
    with shelve.open(SHELVE_PATH) as db:
        db['language_id'] = language_id
