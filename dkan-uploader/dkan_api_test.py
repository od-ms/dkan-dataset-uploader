#! /usr/bin/python

import logging
import os.path
import json
from .datasetuploader import DatasetUploader
from . import config
from . import constants
from . import excelwriter

def test():
    er = DkanApiTest()
    er.run()

def analyze():
    er = DkanApiTest()
    er.analyze_api()

def validate(node_id):
    er = DkanApiTest()
    er.validate_node(node_id)


class DkanApiTest:
    """
        1. Write a dataset + resource to dkan
        2. Read the dataset and resource from dkan
        3. Verify we got the same content in 1. and 2.
    """

    datasetuploader = None

    def __init__(self):
        logging.info(" == Starting DKAN API test == ")
        self.datasetuploader = DatasetUploader()


    def run(self):
        row = {}
        with open(os.path.normpath('dkan-uploader/example_row.json')) as json_file:
            row = json.load(json_file)

        self.create_dataset(row)


    def analyze_api(self):
        ''' Write a dataset with reduced fields to DKAN '''
        row = {}
        with open(os.path.normpath('dkan-uploader/example_row.json')) as json_file:
            row = json.load(json_file)

        # remove keys from
        remove_keys = [
            'Geo', 'License', 'Temporal', 'Data ', 'Frequency', 'Granularity',
            'Textformat', 'Tags', 'Groups', 'Language', 'Schlagworte', 'Public Access Level'
            #,'Related Content'
            ]
        for remove_key in remove_keys:
            row = dict([(key, val) for key, val in
                row.items() if key.find(remove_key) == -1])

        print(json.dumps(row, indent=2))

        self.create_dataset(row)


    def create_dataset(self, row):
        dataset = constants.Dataset.create(row)
        resource = constants.Resource.create(row)

        node_id = self.datasetuploader.processDataset(dataset, [resource])
        if not node_id:
            logging.error(_("Fehler #5001: Datensatz konnte nicht angelegt werden!"))
            return None

        logging.info(_("Anlegen erfolgreich. Datensatz-ID: %s"), node_id)
        self.validate_node(node_id)
        return None

    def validate_node(self, node_id):
        logging.info("Checking node %s", node_id)
        row = {}
        with open(os.path.normpath('dkan-uploader/example_row.json')) as json_file:
            row = json.load(json_file)

        error_fields = excelwriter.validate_single_dataset_row(row, node_id)
        if error_fields:
            logging.error(_("Fehler #5001: Datensatz konnte nicht 1:1 angelegt werden."))
            logging.error(_("Bitte prüfe Sie die Log-Ausgaben weiter oben, um die Problemdetails zu sehen."))
