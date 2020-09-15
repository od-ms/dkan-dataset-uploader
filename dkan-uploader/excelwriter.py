#! /usr/bin/python

import json
import logging
import xlsxwriter


class ExcelFile:
    """ Handle creation of Excel content """

    filename = ''
    workbook = ''
    worksheet = ''
    bold = None
    current_row = 0

    def __init__(self, filename):
        self.filename = filename
        self.workbook = xlsxwriter.Workbook(filename)
        self.worksheet = self.workbook.add_worksheet()
        self.bold = self.workbook.add_format({'bold': True})
        self.worksheet.set_column('A:A', 20)
        self.worksheet.write('A1', 'Dataset', self.bold)
        self.worksheet.write('B1', 'Resource title', self.bold)
        self.worksheet.write('C1', 'Resource URL', self.bold)

    def add_file(self, identifier, title, rtitle, rurl):
        self.current_row += 1
        self.worksheet.write(self.current_row, 0, identifier)
        self.worksheet.write(self.current_row, 1, title)
        self.worksheet.write(self.current_row, 2, rtitle)
        self.worksheet.write(self.current_row, 3, rurl)

    def finish(self):
        self.workbook.close()


def write():
    json_file = 'data.json'

    with open(json_file) as json_data:
        data = json.load(json_data)

    excel_output = ExcelFile('resources2018.xlsx')
    for dataset in data['dataset']:
        if 'distribution' in dataset:
            for resource in dataset['distribution']:

                resource_url = ""
                if 'accessURL' in resource:
                    resource_url = resource['accessURL']
                if 'downloadURL' in resource:
                    resource_url = resource['downloadURL']

                if '2018' in resource_url:
                    logging.info(dataset['title'])
                    logging.info("  %s", resource['title'])
                    logging.info("  `-> %s", resource_url)
                    excel_output.add_file(dataset['identifier'], dataset['title'], resource['title'], resource_url)

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
