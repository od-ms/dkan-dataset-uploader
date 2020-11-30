#! /usr/bin/python

import sys
import json
import jsonschema
import logging
import xlsxwriter
import xlrd
import httplib2
import os.path
from pprint import pprint
from jsonschema import validate
from urllib.request import urlopen
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
    existing_dataset_ids = {}

    def __init__(self, filename, extra_columns):
        self.filename = filename
        self.extra_columns = extra_columns

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
        columns = self.get_column_config().keys()
        self.worksheet.write_row('A1', columns, self.bold)


    def add_plain_row(self, column_contents):
        self.current_row += 1
        self.worksheet.write_row(self.current_row, 0, column_contents)


    def get_column_config(self):
        """ This contains the default configuration of a row"""
        columns = {
            'Dataset-ID': "id",
            'Dataset-Name': "name",
            'Dataset-Title': "title",
            'Author': "author",
            'Email': "author_email",
            'License': "license_title",
            #'Description': "notes",
            'URL': "url",
            'State': "state",
            'Created': "metadata_created",
            'Modified': "metadata_modified"
        }
        for col in self.extra_columns:
            columns["Extra-" + col] = "EXTRA|" + col

        return columns

    def add_dataset(self, dataset):
        columns_config = self.get_column_config().values()
        columns = []
        for column_key in columns_config:
            value = None
            if (column_key[:6] == "EXTRA|") and ("extras" in dataset):
                extra_key = column_key[6:]
                #logging.debug("searching extra key %s", extra_key)
                extra_obj = [x for x in dataset["extras"] if x["key"] == extra_key]
                #logging.debug("found extra obj %s", extra_obj)
                value = extra_obj[0]["value"] if len(extra_obj) else None
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

                resource_row.extend([
                    '#' + str(resource_number+1),
                    resource['id'],
                    resource['name'],
                    resource['format'],
                    resource['url'],
                    resource['response_ok'],
                    resource['response_code']
                ])
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
        "maintainer": {"type": "string"},           # ??
        "maintainer_email": {"type": "string"},     # ??
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

        # TODO: Read and parse the following fields.
        # TODO: How to access dynamic combined list/dict entries see ../test.py
        # THE FOLLOWING FIELDS ARE MISSING IN "current_package_list_with_resources"
        # How to get them? We have to query:
        # 1. https://opendata.stadt-muenster.de/api/dataset/node.json?parameters[uuid]=29a3d573-98e1-412c-af0c-c356a07eff7b
        #    => to get the node id
        # 2. https://opendata.stadt-muenster.de/api/dataset/node/41334.json
        #    => to get the missing details..
        "contact_name": {"type": "string"}, # field_contact_name['und'][0]['value']
        "data_dictionary": {"type": "string"},
        "frequency": {"type": "string"},
        "granularity": {"type": "string"},
        "spatial": {"type": "object"}, # ... TODO add object definition?
        "spatial_geographical_cover": {"type": "string"}, # field_spatial_geographical_cover['und'][0]['value']
        "homepage": {"type": "string"}, # field_landing_page['und'][0]['url']

        # OK back to current_package_list_with_resources
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
    "required": [ "id", "name", "metadata_created", "type", ]
}

def validateJson(jsonData):
    try:
        validate(instance=jsonData, schema=datasetSchema)
    except jsonschema.exceptions.ValidationError as err:
        pprint(err)
        return False
    return True


def read_package_list_with_resources():
    temp_file = '.current_package_list_with_resources'

    try:
        if os.path.isfile(temp_file):
            logging.info('Using cached file "' + temp_file + '"')
        else:
            remote_url = config.dkan_url + config.api_resource_list
            logging.info('Reading remote url: "' + remote_url +'"')
            f = urlopen(remote_url)
            myfile = f.read()
            with open(temp_file, 'w') as fw:
                fw.write(myfile.decode(config.api_encoding))

        with open(temp_file, 'r') as json_data:
            data = json.load(json_data)

    except json.decoder.JSONDecodeError as err:
        logging.debug("Fehlermeldung (beim Parsen der DKAN-API JSON-Daten): %s", err)
        logging.error("Fehler beim Lesen der Eingabedaten. Cache Datei wird gelöscht.")
        logging.error("Bitte versuchen Sie es erneut. Wenn das nicht hilft, prüfen Sie die Fehlermeldung (s.o.)")
        os.remove(temp_file)

    return data


def write():
    data = read_package_list_with_resources()

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
    logging.info("All extras of file: %s", extras)

    # initialize excel file
    excel_output = ExcelResultFile(config.excel_filename, extras)

    excel_output.initialize_new_excel_file_with_existing_content()
    existing_dataset_ids = excel_output.get_existing_dataset_ids()

    resource_status = ResourceStatus()

    # write all datasets and resources to excel file
    number = 0
    for dataset in data['result'][0]:

        isValid = validateJson(dataset)
        if not isValid:
            pprint(dataset)
            raise ValueError('Dataset format is not valid. Scroll up, see detailed error in line before pprint(dataset)')

        dataset_id = dataset['id']
        if dataset_id in existing_dataset_ids:
            logging.debug("Already in Excel. Skipping %s", dataset_id)
            continue

        if dataset['type'] != 'Dataset':
            logging.debug("Item is not of type 'Dataset'. Skipping %s", dataset_id)
            continue

        number += 1
        if number == 1000:
            logging.debug("Stopping now")
            break

        # http-check dataset resources and add check result into nested resource list
        if (not config.skip_resources) and ('resources' in dataset):
            for index, resource in enumerate(dataset['resources']):
                logging.debug("Check: %s", resource['url'])
                if config.check_resources:
                    (ok, response_code) = resource_status.check(resource['url'])
                else:
                    ok = response_code = None
                dataset['resources'][index]['response_ok'] = ok
                dataset['resources'][index]['response_code'] = response_code
                logging.debug("Response: %s %s", ok, response_code)

        excel_output.add_dataset(dataset)


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
