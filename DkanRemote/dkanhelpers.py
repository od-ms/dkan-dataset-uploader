import re
import json
import logging
import os.path
import os
import cgi
import ssl
from urllib.parse import urlparse
from urllib.request import urlopen
from urllib.request import urlretrieve
from random import random
from timeit import default_timer as timer
import requests
from . import config
from . import dkanhandler
from . import constants


class JsonHelper:

    def get_resource_url(resource_node):
        url_value = JsonHelper.get_nested_json_value(resource_node, ["field_link_api", 'und', 0, 'url'])
        if url_value:
            return constants.ResourceType.TYPE_URL, url_value
        url_value = JsonHelper.get_nested_json_value(resource_node, ["field_link_remote_file", 'und', 0, 'uri'])
        if url_value:
            return constants.ResourceType.TYPE_REMOTE_FILE, url_value
        url_value = JsonHelper.get_nested_json_value(resource_node, ["field_upload", 'und', 0, 'filename'])
        if url_value:
            return constants.ResourceType.TYPE_UPLOAD, url_value
        url_value = JsonHelper.get_nested_json_value(resource_node, ["field_datastore_status", 'und', 0, 'filename'])
        if url_value:
            return constants.ResourceType.TYPE_DATASTORE, url_value
        return constants.ResourceType.TYPE_NO_FILE, ''


    def get_nested_json_value(target_dict, keys):
        node_value = None
        try:
            if len(keys) == 4:
                node_value = target_dict[keys[0]][keys[1]][keys[2]][keys[3]]
            elif len(keys) == 3:
                node_value = target_dict[keys[0]][keys[1]][keys[2]]
            elif len(keys) == 1:
                node_value = target_dict[keys[0]]
            else:
                raise Exception("get_nested_json_value() not implemented for {} keys in: {}".format(len(keys), keys))


        except (TypeError, KeyError, IndexError):
            if not (len(keys)>2 and isinstance(keys[2], int) and keys[2]>0):
                logging.debug(_(" [ ] %s"), keys[0])

        return node_value




class HttpHelper:
    ''' helper methods .. refactor '''

    file_formats = None
    taxonomy_cache = {}

    @staticmethod
    def read_dkan_node(node_id):
        node_data = HttpHelper.read_remote_json_with_cache(config.x_api_get_node_details.format(node_id, random()), '{}-complete.json'.format(node_id))
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
                r = requests.get(remote_url, headers={'Cache-Control': 'no-cache', "Pragma": "no-cache"})
                myfile = r.text

                logging.debug(_('HTTP {} | {:.2f}s für: "{}"').format(r.status_code, timer() - ti, remote_url))
                if r.status_code not in [200,302]:
                    logging.warning(_('Warnung: HTTP {} ist vermutlich ein Problem!').format(r.status_code))
                    logging.warning(_('Betroffene URL: {} ').format(remote_url))

                with open(temp_file, mode='w', encoding='utf-8') as fw:
                    fw.write(myfile)

            with open(temp_file, mode='r', encoding='utf-8') as json_data:
                data = json.load(json_data)

        except json.decoder.JSONDecodeError as err:
            logging.debug(_("Fehlermeldung (beim Parsen der DKAN-API JSON-Daten): %s"), err)
            logging.error(_("Fehler 5001 beim Lesen der Eingabedaten."))
            os.remove(temp_file)

        return data


    @staticmethod
    def get_taxonomy_values(taxonomy_name):
        if taxonomy_name not in HttpHelper.taxonomy_cache:
            HttpHelper.taxonomy_cache[taxonomy_name] = HttpHelper.parse_admin_page_contents(dkanhandler.getApi(), '/admin/structure/taxonomy/{}'.format(taxonomy_name))
        return HttpHelper.taxonomy_cache[taxonomy_name]


    @staticmethod
    def get_all_dkan_fileformats():
        if not HttpHelper.file_formats:
            fileformats = HttpHelper.parse_admin_page_contents(dkanhandler.getApi(), '/admin/structure/taxonomy/format')
            HttpHelper.file_formats = {str(value).lower():key for key, value in fileformats.items()}
        return dict(HttpHelper.file_formats)


    @staticmethod
    def get_resource_filename(url):
        file_url = urlparse(url)
        file_path = file_url.path                    # Output: /dir/-47-571378756077.jpg
        file_name = os.path.basename(file_path)
        return file_name


    @staticmethod
    def download_resource(url, lfd_nr, r_format):

        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        try:
            logging.debug("URL: %s", url)
            remotefile = urlopen(url, context=ctx)
        except Exception as err:
            logging.warning('Fehler: %s', repr(err))
            logging.error('Resource-URL kann nicht geöffnet werden: %s', url)
            return None

        backup_filename = filename = ''
        try:
            logging.debug("remotefile info %s", remotefile.info())
            cd_header = remotefile.info()['Content-Disposition']
            logging.debug("header %s", cd_header)
            value, params = cgi.parse_header(cd_header)
            filename = params["filename"]
            logging.debug("Dateiname aus Header: %s", filename)
        except Exception as err:
            logging.debug('Kein Dateiname im Header, Fehler: %s', repr(err))
            filename = HttpHelper.get_resource_filename(url)
            if filename:
                logging.debug("Dateiname aus URL: %s", filename)
        if filename and (filename.find(".") == -1):
            filename = filename + '.' + r_format

        if not filename:
            backup_filename = 'unknown.{}'.format(r_format)
            logging.warning("Dateiname in URL und Header Leer. Download-Datei wird '%s' genannt.", backup_filename)

        targetpath = os.path.normpath(os.path.join(config.download_dir, lfd_nr + '-' + filename + backup_filename))
        logging.debug("Download Ziel: %s", targetpath)

        ti = timer()
        urlretrieve(url, targetpath)
        logging.info(_(' * Download in {:.4f}s: {} "{}"').format(timer() - ti, (lfd_nr + '-' + filename + backup_filename), url))

        return filename


    @staticmethod
    def parse_admin_page_contents(pydkan_instance, admin_page_path):

        # When logged in via pydkan, it is possible to send requests to the administration interface..
        # I dont know if that is intended behaviour or just a side effect..
        # But it can be used to read the taxonomy admin HTML page and scrape dataset_tags from it
        # Which seems to be the only way to get a list of the dataset_tags with their according IDs

        if not pydkan_instance:
            pydkan_instance = dkanhandler.getApi()
        if not pydkan_instance:
            logging.error(_("Anmeldung am DKAN fehlgeschlagen: %s"), admin_page_path)
            return []

        tags_url = config.dkan_url + admin_page_path
        res = pydkan_instance.get(tags_url)

        if res.status_code != 200:
            logging.debug(_("Server-Antwort: %s"), res.text)
            logging.info(_("Administrations-URL: %s"), tags_url)
            logging.error(_("Folgende DKAN-Administrations-Seite konnte nicht gelesen werden: %s"), admin_page_path)

        # parse html content to get dataset_tags names and IDs
        page_content = res.text
        matches = re.findall(
            r'id="edit-tid(\d+)0-view">([^<]+)</a><',
            page_content,
            flags = re.S|re.M
            )

        taglist = {}
        for result in matches:
            taglist[result[0]] = result[1]

        logging.debug(_("Admin-Scraping-Ergebnis: %s"), taglist)

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
