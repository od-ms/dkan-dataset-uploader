#! /usr/bin/python

import logging
import xlrd
from .datasetuploader import DatasetUploader
from . import config
from . import constants

def read(command_line_excel_filename):
    """ read first row of file """

    er = ExcelReader()
    er.import_excel_file_to_dkan(command_line_excel_filename if command_line_excel_filename else config.excel_filename)


class ExcelReader:
    """
        Reads all the rows and columns from the excel file and writes them to the nearest dkan instance
    """

    columns_in_file = {}
    datasetuploader = None

    def __init__(self):
        self.columns_in_file = {}
        self.datasetuploader = DatasetUploader()

    def import_excel_file_to_dkan(self, excel_filename):
        dkan_dataset_fields = constants.get_column_config_dataset()
        dkan_resource_fields = constants.get_column_config_resource()
        dkan_fields = {**dkan_dataset_fields, **dkan_resource_fields}

        logging.info(_("Excel Datei wird eingelesen: %s"), excel_filename)
        loc = (excel_filename)

        wb = xlrd.open_workbook(loc)
        sheet = wb.sheet_by_index(0)
        sheet.cell_value(0, 0)

        used_fields = {}
        columns = []
        logging.info(_("Gefundene Spaltenüberschriften der Excel-Datei:"))
        for i in range(sheet.ncols):

            column_name = sheet.cell_value(0, i)
            columns.append(column_name)

            if column_name in dkan_fields:
                used_fields[column_name] = 1
                logging.info(" o %s", column_name)
            elif column_name[:6] == "Extra-":
                logging.info(_(" o %s => Zusätzliches Info-Feld"), column_name)
            else:
                logging.warning(_(" X %s => Kein passendes DKAN-Feld gefunden"), column_name)

        missing_dataset_cols = 0
        for field in dkan_dataset_fields:
            if not field in used_fields:
                missing_dataset_cols+=1
                logging.warning(_(" > %s => Fehlt in Excel-Datei"), field)
        if missing_dataset_cols:
            logging.error(_('In der Excel-Datei fehlen Dataset-Spalten. Bitte fügen Sie erst die fehlenden Spalten hinzu.'))
            return None

        self.datasetuploader.setIngoreResources(False)
        missing_resource_cols = 0
        for field in dkan_resource_fields:
            if not field in used_fields:
                missing_resource_cols+=1
                logging.warning(_(" > %s => Ressource-Spalte fehlt in Excel-Datei"), field)
        if missing_resource_cols:
            if missing_resource_cols == len(dkan_resource_fields):
                # TODO we should pop up a window that asks the user if its ok to continue
                logging.error(_('Die Excel-Datei enthält keine Ressource-Informationen!'))
                logging.error(_('Daher werden nur Datensatz-Daten aktualisiert. Die Ressourcen werden nicht verändert.'))
                self.datasetuploader.setIngoreResources(True)

            else:
                logging.error('In der Excel-Datei fehlen Ressource-Spalten. Bitte fügen Sie erst die fehlenden Spalten hinzu.')
                return None


        constants.Dataset.verify()
        constants.Resource.verify()

        self.columns_in_file = columns
        self.parse_rows(sheet)


    def parse_rows(self, sheet):

        last_dataset = None
        resources = []
        for row_nr in range(1, sheet.nrows):

            row = {}
            for i in range(sheet.ncols):
                column_value = sheet.cell_value(row_nr, i)
                column_name = self.columns_in_file[i]
                row[column_name] = column_value

            logging.info(_("Zeile %s/%s"), row_nr, sheet.nrows)

            dataset = constants.Dataset.create(row)

            if dataset:
                logging.debug("Vorheriger Datensatz: %s", last_dataset)
                # All resource columns were collected. A new dataset should be created.
                if last_dataset:
                    self.datasetuploader.processDataset(last_dataset, resources)
                elif resources:
                    logging.warning(_("%s Resourcen werden ignoriert."), len(resources))

                resources = []
                last_dataset = dataset

            resource = constants.Resource.create(row)
            if resource:
                resources.append(resource)
            else:
                logging.info(_("Zeile %s enthielt keine Ressource."), row_nr)

        # create last dataset in file
        if last_dataset:
            self.datasetuploader.processDataset(last_dataset, resources)
