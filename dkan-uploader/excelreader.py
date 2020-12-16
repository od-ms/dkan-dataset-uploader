#! /usr/bin/python

import sys
import logging
import xlrd
from . import config
from . import constants


def read(command_line_excel_filename):
    """ read first row of file """

    dkan_dataset_fields = constants.get_column_config_dataset()
    dkan_resource_fields = constants.get_column_config_resource()
    dkan_fields = {**dkan_dataset_fields, **dkan_resource_fields}

    excel_filename = command_line_excel_filename if command_line_excel_filename else config.excel_filename
    logging.info(_("Excel Datei wird eingelesen: %s"), excel_filename)
    loc = (excel_filename)

    try:
        wb = xlrd.open_workbook(loc)
        sheet = wb.sheet_by_index(0)
        sheet.cell_value(0, 0)

        used_fields = {}
        logging.info(_("Gefundene Spaltenüberschriften der Excel-Datei:"))
        for i in range(sheet.ncols):
            column_name = sheet.cell_value(0, i)
            if column_name in dkan_fields:
                used_fields[column_name] = 1
                logging.info(" o %s", column_name)
            elif column_name[:6] == "Extra-":
                logging.info(_(" o %s => Zusätzliches Info-Feld"), column_name)
            else:
                logging.warning(_(" X %s => Kein passendes DKAN-Feld gefunden"), column_name)

        for field in dkan_fields:
            if not field in used_fields:
                logging.warning(_(" > %s => Fehlt in Excel-Datei"), field)

    except:
        e = sys.exc_info()[0]
        logging.warning(_("Fehler: %s"), e)


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
