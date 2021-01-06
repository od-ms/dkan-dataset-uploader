import sys
import re
import json
import logging
import hashlib
import os.path
from timeit import default_timer as timer
from dkan.client import DatasetAPI, LoginError
import requests
from . import config
from . import constants


class HttpHelper:
    ''' helper methods .. refactor '''

    @staticmethod
    def read_dkan_node(node_id):
        node_data = HttpHelper.read_remote_json_with_cache(config.x_api_get_node_details.format(node_id), '{}-complete.json'.format(node_id))
        return node_data


    @staticmethod
    def read_remote_json_with_cache(remote_url, temp_file):
        """download a remote url to a temp directory first, then use it"""

        # prefix with tempdir and convert slashes to backslashes on windows
        temp_file = os.path.normpath(config.x_temp_dir + temp_file)
        remote_url = config.dkan_url + remote_url
        data = None

        try:
            if os.path.isfile(temp_file):
                logging.debug(_('Nutze Cachedatei "%s" '), temp_file)
            else:
                ti = timer()
                r = requests.get(remote_url)
                myfile = r.text

                logging.info(_('{:.4f}s URL load: "{}"').format(timer() - ti, remote_url))

                with open(temp_file, 'w') as fw:
                    fw.write(myfile)

            with open(temp_file, 'r') as json_data:
                data = json.load(json_data)

        except json.decoder.JSONDecodeError as err:
            logging.debug("Fehlermeldung (beim Parsen der DKAN-API JSON-Daten): %s", err)
            logging.error("Fehler 5001 beim Lesen der Eingabedaten. Cache Datei wird gelöscht.")
            logging.error("Bitte versuchen Sie es erneut. Wenn das nicht hilft, prüfen Sie die Fehlermeldung (s.o.) und konsultieren Sie die Dokumentation.")
            os.remove(temp_file)

        return data

    @staticmethod
    def get_all_dkan_tags(pydkan_instance):

        # When logged in via pydkan, it is possible to send requests to the administration interface..
        # I dont know if that is intended behaviour or just a side effect..
        # But it can be used to read the taxonomy admin HTML page and scrape dataset_tags from it
        # Which seems to be the only way to get a list of the dataset_tags with their according IDs

        tags_url = config.dkan_url + '/admin/structure/taxonomy/dataset_tags'
        res = pydkan_instance.get(tags_url)

        if res.status_code != 200:
            logging.debug("Response content: %s", res.text)
            logging.info("Tags URL: %s", tags_url)
            logging.error("Something went wrong when trying to get all dataset_tags from dkan instance.")

        # parse html content to get dataset_tags names and IDs
        page_content = res.text
        matches = re.findall(
            r'id="edit-tid(\d+)0-view">([^<]+)</a><',
            page_content,
            flags = re.S|re.M
            )

        taglist = {}
        for result in matches:
            logging.debug("found tag %s", result)
            taglist[result[0]] = result[1]

        return taglist


    @staticmethod
    def log_in_to_dkan_admin_interface():

        # This method was supposed to log you into the admin interface of DKAN.
        # I dont know what they are doing to prevent logging in,
        # But this does not work at all.
        # I wasted half a day trying.. so I want to at least commit this code once before I delete it..

        headers = {
            'User-Agent': 'Mozilla/5.0',
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "accept-language": "en-US,en;q=0.9,de;q=0.8",
            "authorization": "Basic bXVlbnN0ZXI6ZGthbm11ZW5zdGVydA==",
            "cache-control": "max-age=0",
            "content-type": "application/x-www-form-urlencoded",
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "same-origin",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
            "Referer": "https://dkan-muenster-test.stadt-koeln.de/user/login",
            }
        payload = {
            'name': config.dkan_username,
            'pass': config.dkan_password,
            "form_build_id": "form-pajoUAxL1t4DvHwCytkTCDvASEzzocglMt1q1atTTvQ",
            "form_id": "user_login",
            "feed_me": "",
            "op": "Anmelden"
        }

        with requests.Session() as s:
            p = s.get(config.dkan_url + '/user/login', headers=headers)
            loginform_html = p.text
            logging.info("response %s %s", p.status_code, p.text)

            logging.debug("session1:")

            print(s.cookies.get_dict())

            m = re.search(
                r'id="main-content".*name="form_build_id"\s+value="([^"]*)"',
                loginform_html,
                flags = re.S|re.M
                )
            form_id = m.group(1)
            logging.debug("result formid %s", form_id)
            payload['form_build_id'] = form_id
            logging.debug("payload:")
            print(json.dumps(payload, indent=2))

            p = s.post(config.dkan_url + '/user/login', headers=headers, data=payload)
