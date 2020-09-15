#! /usr/bin/python

import sys
import json
import logging
import xlsxwriter
import xlrd
import httplib2
from . import config
import pprint

class ExcelResultFile:
    """ Handle creation of Excel content """

    filename = ''
    workbook = ''
    worksheet = ''
    bold = None
    current_row = 0
    old_excel_content = []

    def __init__(self, filename):
        self.filename = filename

    def read_existing_content(self):
        """ Read the extisting excel and save ALL content to "old_excel_content",
            so we can then write it to a "new" file (=to continue from where we left off)
            Also return all dataset_ids as dict, so we can skip them
        """
        logging.info("Reading excel file: %s", self.filename)
        loc = (self.filename)
        existing_dataset_ids = {}
        old_excel_content = []

        try:
            wb = xlrd.open_workbook(loc)
            sheet = wb.sheet_by_index(0)
            for j in range(1, sheet.nrows):
                excelrow = []
                for i in range(sheet.ncols):
                    excelrow.append(sheet.cell_value(j, i))
                existing_dataset_ids[excelrow[0]] = True
                old_excel_content.append(excelrow)
        except FileNotFoundError:
            pass

        self.old_excel_content = old_excel_content

        pprint.pprint(existing_dataset_ids)
        return existing_dataset_ids

    def initialize_new_excel_file_with_existing_content(self):
        self.initialize_new_excel_file()
        for row in self.old_excel_content:
            self.add_dkan_resource(*row)

    def initialize_new_excel_file(self):
        self.workbook = xlsxwriter.Workbook(self.filename)
        self.worksheet = self.workbook.add_worksheet()
        self.bold = self.workbook.add_format({'bold': True})
        self.worksheet.set_column('A:A', 20)
        self.worksheet.write_row(
            'A1',
            ('ID', 'Created', 'Modified', 'Dataset name', 'Format', 'Resource title', 'Resource URL', 'OK', 'Responsecode'),
            self.bold)

    def add_dkan_resource(self, *args): #identifier, title, rtitle, rurl, ok, response_code
        self.current_row += 1
        self.worksheet.write_row(self.current_row, 0, args)

    def finish(self):
        self.workbook.close()


class ResourceStatus:
    """Check status of a resource"""

    def check(self, url):
        htl = httplib2.Http(".cache", disable_ssl_certificate_validation=True)
        resp = htl.request(url, 'HEAD')
        return (int(resp[0]['status']) < 400), resp[0]['status']


def write():
    json_file = 'data.json'

    with open(json_file) as json_data:
        data = json.load(json_data)

    excel_output = ExcelResultFile(config.excel_filename)
    existing_dataset_ids = excel_output.read_existing_content()

    excel_output.initialize_new_excel_file_with_existing_content()

    resource_status = ResourceStatus()

    number = 0
    for dataset in data['dataset']:

        dataset_id = dataset['identifier']
        if dataset_id in existing_dataset_ids:
            logging.debug("skipping %s", dataset_id)
            continue

        number += 1
        if number == 20:
            logging.debug("Stopping now")
            break

        if 'distribution' in dataset:
            for resource in dataset['distribution']:
                resource_url = ""
                if 'accessURL' in resource:
                    resource_url = resource['accessURL']
                if 'downloadURL' in resource:
                    resource_url = resource['downloadURL']

                logging.debug("Check: %s %s %s", dataset['identifier'], resource['title'], resource_url[0:30])
                (ok, response_code) = resource_status.check(resource_url)
                logging.debug("=> Response: %s %s", ok, response_code)
                excel_output.add_dkan_resource(
                    dataset['identifier'],
                    dataset['issued'],
                    dataset['modified'],
                    dataset['title'],
                    resource['format'],
                    resource['title'],
                    resource_url,
                    ok,
                    response_code)


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
