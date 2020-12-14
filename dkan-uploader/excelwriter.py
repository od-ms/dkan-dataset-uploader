#! /usr/bin/python

import sys
import json
import jsonschema
import logging
import xlsxwriter
import xlrd
import httplib2
import hashlib
import os.path
from pprint import pprint
from jsonschema import validate
from urllib.request import urlopen
from timeit import default_timer as timer
from . import config

class ExcelResultFile:
    """ Handle creation of Excel content """

    # startup values
    filename = ''
    extra_columns = {}

    # runtime config
    workbook = ''
    worksheet = ''
    bold = None
    current_row = 0
    current_dataset_nr = 0
    existing_dataset_ids = {}

    def __init__(self, filename, extra_columns):
        self.filename = filename
        self.extra_columns = extra_columns
        self.current_row = 0

    def initialize_new_excel_file_with_existing_content(self):
        """ Read the extisting excel and save ALL content to "old_excel_content",
            so we can then write it to a "new" file (=to continue from where we left off)
            Also return all dataset_ids as dict, so we can skip them
        """
        logging.info("Reading excel file: %s", self.filename)
        loc = (self.filename)
        self.existing_dataset_ids = {}
        old_excel_content = []

        try:
            wb = xlrd.open_workbook(loc)
            sheet = wb.sheet_by_index(0)
            for j in range(1, sheet.nrows):
                excelrow = []
                for i in range(sheet.ncols):
                    excelrow.append(sheet.cell_value(j, i))

                old_excel_content.append(excelrow)

                # save all dataset ids for later use (=lookup of existing ids)
                dataset_id = excelrow[0]
                if dataset_id:
                    self.existing_dataset_ids[dataset_id] = True

        except FileNotFoundError:
            pass

        self.initialize_new_excel_file()

        for row in old_excel_content:
            self.add_plain_row(row)

    def get_existing_dataset_ids(self):
        logging.debug("Existing ids: %s", self.existing_dataset_ids)
        return self.existing_dataset_ids

    def initialize_new_excel_file(self):

        # init workbook objects
        self.workbook = xlsxwriter.Workbook(self.filename)
        self.worksheet = self.workbook.add_worksheet()
        self.bold = self.workbook.add_format({'bold': True})
        self.worksheet.set_column('A:A', 20)

        # write header row
        columns = list(self.get_column_config_dataset().keys())
        if not config.skip_resources:
            columns.extend(self.get_column_config_resource().keys())

        self.worksheet.write_row('A1', columns, self.bold)


    def add_plain_row(self, column_contents):
        # logging.debug("Writing row %s", column_contents)
        self.current_row += 1
        self.worksheet.write_row(self.current_row, 0, column_contents)


    def get_nested_json_value(self, target_dict, keys):
        node_value = None
        try:
            if len(keys) == 4:
                node_value = target_dict[keys[0]][keys[1]][keys[2]][keys[3]]
            else:
                logging.error("Not implemented for {} keys in: %s".format(len(keys)), keys)
                raise Exception("Not implemented for {} keys in: %s".format(len(keys)), keys)

            logging.debug("got nested dkan node: %s => {}".format(node_value), keys)

        except (TypeError, KeyError):
            logging.debug("Probably empty value, did not find key: %s", keys)

        return node_value


    def get_column_config_dataset(self):
        """ This contains the default configuration of a row"""


        # Some FIELDS ARE MISSING IN "current_package_list_with_resources"
        # How to get them? We have to query:
        # 1. https://opendata.stadt-muenster.de/api/dataset/node.json?parameters[uuid]=29a3d573-98e1-412c-af0c-c356a07eff7b
        #    => to get the node id
        # 2. https://opendata.stadt-muenster.de/api/dataset/node/41334.json
        #    => to get the missing details..

        #   TODO: So kann man eine Liste der TAGS bekommen, aber ohne IDs..?!?!
        #           => https://opendata.stadt-muenster.de/autocomplete_deluxe/taxonomy/field_dataset_tags/%20/500?term=&synonyms=2

        #   TODO: Der Testdatensatz - da wurden alle Felder mit Daten gefüllt, aber nur teilweise sinnvoll.
        #           "bevölkerungsindikatoren-soziales" - 3877be7b-5cc8-4d54-adfe-cca0f4368a13
        #                                            ^ den nachher wieder richtig einstellen!
        columns = {
            'Dataset-ID': "id",
            'Dataset-Name': "name",
            'Titel': "title",
            'Author': "author",
            'Contact Name': ['field_contact_name', 'und', 0, 'value'],
            'Contact Email': "author_email",
            'Geographical Location': ['field_spatial_geographical_cover', 'und', 0, 'value'],
            'Geographical Coverage Area': ['field_spatial_geographical_cover', 'und', 0, 'wkt'],
            'License': "license_title",
            'Custom License': ['field_license', 'und', 0, 'value'],
            'Homepage URL': ['field_landing_page', 'und', 0, 'url'],
            'Description': "notes",
            'Textformat': ["body", "und", 0, "format"],
            'URL': "url",
            # 'Tags'
            'Groups': 'COLLECT|groups.title',
            'Frequency': ['field_frequency', 'und', 0, 'value'], #example value: "R/P1Y" ?
            'Temporal Coverage Start': ['field_temporal_coverage', 'und', 0, 'value'],
            'Temporal Coverage End': ['field_temporal_coverage', 'und', 0, 'value2'],
            'Granularity': ["field_granularity", "und", 0, "value"],
            'Data Dictionary': ["field_data_dictionary", 'und', 0, 'value'],
            'Data Dictionary Type': ["field_data_dictionary_type", 'und', 0, 'value'],
            'Public Access Level': ["field_public_access_level", "und", 0, "value"],
            'Data Standard': ['field_conforms_to', "und", 0, "url"],
            'Language': ["field_language", 'und', 0, 'value'],
            # Related Content

            # Additional Info --> ok
            # Resources --> ok

            # 'Schlagworte': TODO,
            # Playground => ziemlich viele Felder!
            # Harvest Source
            # Versionsinformationen ?
            # Einstellungen für Kommentare (Öffnen / Geschlossen)
            # Informationen zum Autor
                # Erstellt von
                # geschrieben am
            # Veröffentlichungseinstellungen
                # Veröffentlicht
                # Auf der Startseite
                # Oben in Listen
            'State': "state",
            'Created': "metadata_created",
            'Modified': "metadata_modified"
        }
        for col in self.extra_columns:
            columns["Extra-" + col] = "EXTRA|" + col

        return columns

    def get_column_config_resource(self):
        columns = {
            'Lfd-Nr': 'lfd-nr',
            'Resource-ID': 'id',
            'Resource-Name': 'name',
            'Format': 'format',
            'Externe Url': 'url',
            'Description': 'description',
            'Prüfung OK?': 'response_ok',
            'HTTP-Responsecode':'response_code'
        }

        return columns

    def add_dataset(self, dataset, dkan_node):
        self.current_dataset_nr += 1
        columns_config = self.get_column_config_dataset().values()
        columns = []
        for column_key in columns_config:
            value = None
            if isinstance(column_key, list):
                value = self.get_nested_json_value(dkan_node, column_key)
            elif (column_key[:6] == "EXTRA|") and ("extras" in dataset):
                extra_key = column_key[6:]
                #logging.debug("searching extra key %s", extra_key)
                extra_obj = [x for x in dataset["extras"] if x["key"] == extra_key]
                #logging.debug("found extra obj %s", extra_obj)
                value = extra_obj[0]["value"] if len(extra_obj) else None
            elif (column_key[:8] == "COLLECT|"):
                extra_key = column_key[8:]
                if 'groups' in dataset:
                    groups = []
                    for group in dataset['groups']:
                        groups.append(group['title'])
                    value = ", ".join(groups)

            else:
                value = dataset[column_key] if column_key in dataset else None
            columns.append(value)

        pprint(columns)

        # write dataset row without resources
        if (config.skip_resources) or ('resources' not in dataset):
            self.add_plain_row(columns)

        # write resource rows
        else:
            for resource_number, resource in enumerate(dataset['resources']):
                resource_row = []
                if resource_number == 0:
                    resource_row = columns.copy()
                else:
                    resource_row = [''] * len(columns)

                # get all resource fields according to resource column config
                rcolumns_config = self.get_column_config_resource().values()
                for rc_key in rcolumns_config:
                    rc_value = ""
                    if rc_key == 'lfd-nr':
                        rc_value = str(self.current_dataset_nr) + '-' + str(resource_number+1)
                    else:
                        try:
                            rc_value = resource[rc_key]
                        except KeyError:
                            logging.error('Key "%s" not found: %s', rc_key, resource)

                    resource_row.extend([rc_value])

                self.add_plain_row(resource_row)


    def finish(self):
        self.workbook.close()


class ResourceStatus:
    """Check status of a resource"""

    def check(self, url):
        try:
            htl = httplib2.Http(".cache", disable_ssl_certificate_validation=True)
            resp = htl.request(url, 'HEAD')
        except:
            e = sys.exc_info()
            logging.exception("Error during resource load")
            return (False, str(e[0]) + " " + str(e[1]))

        return (int(resp[0]['status']) < 400), resp[0]['status']

# JSON Schema of the dataset entries in endpoint "current_package_list_with_resources"
datasetSchema = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "name": {"type": "string"},
        "title": {"type": "string"},
        "author": {"type": "string"},
        "author_email": {"type": "string"}, # = "contact email"
        "maintainer": {"type": "string"},           # useless
        "maintainer_email": {"type": "string"},     # useless
        "license_title": {"type": "string"},
        "notes": {"type": "string"},        # = "description"
        "url": {"type": "string"},
        "state": {"type": "string"},
        "log_message": {"type": "string"},          # ??
        "private": {"type": "boolean"},             # ??
        "revision_timestamp": {"type": "string"},
        "metadata_created": {"type": "string"},
        "metadata_modified": {"type": "string"},
        "creator_user_id": {"type": "string"},
        "type": {"type": "string"},                 # always "Dataset"
        "resources": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "revision_id": {"type": "string"},
                    "url": {"type": "string"},
                    "description": {"type": "string"},
                    "format": {"type": "string"},
                    "state": {"type": "string"},
                    "revision_timestamp": {"type": "string"},
                    "name": {"type": "string"},
                    "mimetype": {"type": "string"},
                    "size": {"type": "string"},
                    "created": {"type": "string"},
                    "resource_group_id": {"type": "string"},
                    "last_modified": {"type": "string"},
                    # these are added by the check-script (see bottom of file)
                    "response_ok": {"type": "string"},
                    "response_code": {"type": "string"}
                },
                "required": [ "id", "revision_id", "name", "url" ]
            }
        },
        "tags": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "vocabulary_id": {"type": "string"},
                    "name": {"type": "string"}
                },
                "required": [ "id", "vocabulary_id", "name" ]
            }
        },
        "groups": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "title": {"type": "string"}, # this is the value that we want
                    "description": {"type": "string"},
                    "name": {"type": "string"}
                },
                "required": [ "name", "title", "id" ]
            }
        },
        "extras": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "key": {"type": "string"},
                    "value": {"type": "string"},
                },
                "required": [ "key", "value" ]
            }
        }
    },
    "required": [ "id", "name", "metadata_created", "type" ]
}

# TODO: JSON Schema for DKAN Nodes
nodeSchema = {

}

def validateJson(jsonData, check_schema):
    try:
        validate(instance=jsonData, schema=check_schema)
    except jsonschema.exceptions.ValidationError as err:
        pprint(err)
        return False
    return True


def read_remote_json_with_cache(remote_url, temp_file):
    """download a remote url to a temp directory first, then use it"""

    # prefix with tempdir and convert slashes to backslashes on windows
    temp_file = os.path.normpath('temp/' + temp_file)
    remote_url = config.dkan_url + remote_url

    try:
        if os.path.isfile(temp_file):
            logging.info('Using cached file "' + temp_file + '"')
        else:
            ti = timer()
            f = urlopen(remote_url)
            myfile = f.read()
            logging.info('Reading remote url ({:.4f}): "{}"'.format(timer() - ti, remote_url))

            with open(temp_file, 'w') as fw:
                fw.write(myfile.decode(config.api_encoding))

        with open(temp_file, 'r') as json_data:
            data = json.load(json_data)

    except json.decoder.JSONDecodeError as err:
        logging.debug("Fehlermeldung (beim Parsen der DKAN-API JSON-Daten): %s", err)
        logging.error("Fehler 5001 beim Lesen der Eingabedaten. Cache Datei wird gelöscht.")
        logging.error("Bitte versuchen Sie es erneut. Wenn das nicht hilft, prüfen Sie die Fehlermeldung (s.o.) und konsultieren Sie die Dokumentation.")
        os.remove(temp_file)

    return data

def read_package_list_with_resources():
    """Read all datasets and resources from DKAN portal
        Or from local cache file if it exists
    """
    return read_remote_json_with_cache(config.api_resource_list,
        'current_package_list_with_resources{}.json'.format( hashlib.md5(config.api_resource_list.encode()).hexdigest() )
    )


def write(command_line_excel_filename):
    data = read_package_list_with_resources()

    for item in dir(config):
        if not item.startswith("__"):
            logging.debug("CONFIG %s", "{}: {}".format(item, getattr(config,item)))


    # iterate all datasets once to find all defined extras
    extras = {}
    for dataset in data['result'][0]:
        if "extras" in dataset:
            for extra in dataset["extras"]:
                keyName = extra["key"]
                if keyName in extras:
                    extras[keyName] = extras[keyName] + 1
                else:
                    extras[keyName] = 0
    logging.info("All 'additional-info'-fields of DKAN response: %s", extras)

    # initialize excel file
    excel_output = ExcelResultFile(command_line_excel_filename if command_line_excel_filename else config.excel_filename, extras)

    excel_output.initialize_new_excel_file_with_existing_content()
    existing_dataset_ids = excel_output.get_existing_dataset_ids()

    resource_status = ResourceStatus()

    # write all datasets and resources to excel file
    number = 0
    for dataset in data['result'][0]:

        isValid = validateJson(dataset, datasetSchema)
        if not isValid:
            pprint(dataset)
            raise ValueError('Dataset format is not valid. Scroll up, see detailed error in line before pprint(dataset)')

        dataset_id = dataset['id']
        if config.dataset_ids and (config.dataset_ids.find(dataset_id) == -1):
            continue

        if (not config.overwrite_rows) and (dataset_id in existing_dataset_ids):
            logging.debug("Already in Excel. Skipping %s", dataset_id)
            continue

        if dataset['type'] != 'Dataset':
            logging.debug("Item is not of type 'Dataset'. Skipping %s", dataset_id)
            continue

        number += 1
        if number == 3:
            logging.debug("Stopping now")
            break

        node_data = None
        # Sadly all the api endpoints with a list of datasets have missing data
        # That is why we have to make two extra calls per dataset.  .. maybe if there is another way..?
        if config.download_extended_dataset_infos:
            node_search = read_remote_json_with_cache(config.api_find_node_id.format(dataset_id), '{}.json'.format(dataset_id))
            if node_search[0]['nid']:
                nid = node_search[0]['nid']
                node_data = read_remote_json_with_cache(config.api_get_node_details.format(nid), '{}-complete.json'.format(dataset_id))
                isValid = validateJson(node_data, nodeSchema)
                if not isValid:
                    pprint(dataset)
                    raise ValueError('Dataset format is not valid. Scroll up, see detailed error in line before pprint(dataset)')


        # http-check dataset resources and add check result into nested resource list
        if (not config.skip_resources) and ('resources' in dataset):
            for index, resource in enumerate(dataset['resources']):
                if config.check_resources:
                    logging.debug("Check: %s", resource['url'])
                    (ok, response_code) = resource_status.check(resource['url'])
                    logging.debug("Response: %s %s", ok, response_code)
                else:
                    ok = response_code = None
                dataset['resources'][index]['response_ok'] = ok
                dataset['resources'][index]['response_code'] = response_code

        excel_output.add_dataset(dataset, node_data)


    excel_output.finish()


# DKAN data.json file format:
# ---------------------------
#                   ( wget https://dkan-url/data.json )
"""
 'dataset': [{'@type': 'dcat:Dataset',
    'accessLevel': 'public',
    'contactPoint': {'fn': 'Open Data Koordination',
                    'hasEmail': '...'},
    'description': 'Am 30. Januar 2020 wurde die neue '
                    'beschlossen. Das Wahlgebiet "Stadt Münster" für '
    'distribution': [{'@type': 'dcat:Distribution',
                    'accessURL': '...',
                    'description': 'In dieser PDF-Datei ist die '
                                    'Änderung der '
                                    '2020 visuell dargestellt.',
                    'format': 'pdf',
                    'title': 'Übersicht der geänderten '
                                'Wahlbezirke'},
                    {'@type': 'dcat:Distribution',
                    'accessURL': '...',
                    'description': 'In dieser Shape-Datei sind die '
                                    'aktuellen Kommunalwahlbezirke '
                                    'verfügbar.',
                    'format': 'shape',
                    'title': 'Aktuelle Kommunalwahlbezirke 2020'}],
    'identifier': '0e5931cf-9e8f-4ff0-afe3-54798a39d1bb',
    'issued': '2020-08-25',
    'keyword': ['Politik und Wahlen'],
    'landingPage': '....',
    'license': 'https://www.govdata.de/dl-de/by-2-0',
    'modified': '2020-08-25',
    'publisher': {'@type': 'org:Organization',
                'name': 'Stadt '},
    'spatial': 'POLYGON ((7.5290679931641 51.89293553285, '
                '52.007625513725, 7.7350616455078 51.89293553285))',
    'title': 'Änderungen der Wahlbezirke zur Kommunalwahl  '
            '2020'},
"""
