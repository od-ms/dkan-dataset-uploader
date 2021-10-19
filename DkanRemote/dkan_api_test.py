#! /usr/bin/python

import logging
import os.path
import json
from .datasetuploader import DatasetUploader
from . import config
from . import constants
from . import excelwriter
from . import dkanhelpers

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
        logging.info(_(" == DKAN API Test - Start == "))
        self.datasetuploader = DatasetUploader()


    def run(self):
        row = {}
        with open(os.path.normpath('DkanRemote/example_row.json')) as json_file:
            row = json.load(json_file)

        node_id = self.create_dataset(row)
        if node_id:
            self.validate_node(node_id)
            self.remove_dataset(node_id)



    def analyze_api(self):
        ''' Can only be called from the console with commandline switch "-wt".
            Write a dataset with reduced fields to DKAN.
            Use this to debug the API instance. See instuctions in commentes below. '''

        row = {}
        with open(os.path.normpath('DkanRemote/example_row.json')) as json_file:
            row = json.load(json_file)

        # IF the DKAN api refuses to create a dataset
        # (error 500, or "unable to validate dataset" or similar error..)
        #
        # THEN use the following "search"-method to find the field(s) that produce the error:
        #   1.   uncomment keys in the following list, e.g. start with first 5 keys "license", "Data " etc
        #   2.   run the script with "python3 -m DkanRemote -wt"
        #   3.   A test dataset will be created without those uncommented fields
        #   4a.  if the creation of the dataset works, then one of the fields was the problem
        #   4b.  otherwise some other field might be the problem (or many fields)
        #   5.   uncomment / comment other keys in the list and restart the procedure (1.) until you find the broken field(s)
        #   6.   if you found the broken field(s), try to fix the json data creation in method dkanhandler::GetDkanData()

        remove_keys = [
            #'License'
            #,'Data '
            #,'Granularity'
            #,'Temporal'
            #,'Schlagworte'
            #,'Frequency'
            #,'Geo'
            #,'Textformat'
            #,'Language'
            #,'Tags'
            #,'Groups'
            #,'Public Access Level'
            #,'Related Content'
            ]
        for remove_key in remove_keys:
            row = dict([(key, val) for key, val in
                row.items() if key.find(remove_key) == -1])

        print(json.dumps(row, indent=2))

        node_id = self.create_dataset(row)
        if node_id:
            self.validate_node(node_id)
            self.remove_dataset(node_id)


    def create_dataset(self, row):
        dataset = constants.Dataset.create(row)
        resource = constants.Resource.create(row)

        node_id = self.datasetuploader.processDataset(dataset, [resource])
        if not node_id:
            logging.error(_("Fehler #5001: Datensatz konnte nicht angelegt werden!"))
            return None

        logging.info(_("Anlegen erfolgreich. Datensatz-ID: %s"), node_id)
        return node_id


    def remove_dataset(self, node_id):
        logging.info("Test-Datensatz %s wird wieder gelöscht.", node_id)
        self.datasetuploader.deleteDataset(node_id)


    def validate_node(self, node_id):
        logging.info("Checking node %s", node_id)
        row = {}
        with open(os.path.normpath('DkanRemote/example_row.json')) as json_file:
            row = json.load(json_file)

        error_fields = excelwriter.validate_single_dataset_row(row, node_id)
        if error_fields:
            logging.error(_("Fehler #5005: Datensatz konnte nicht 1:1 angelegt werden."))
            logging.error(_("Bitte prüfe Sie die Log-Ausgaben weiter oben, um die Problemdetails zu sehen."))
