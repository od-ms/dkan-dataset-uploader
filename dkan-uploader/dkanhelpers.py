import sys
import json
import logging
import hashlib
import os.path
from timeit import default_timer as timer
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
