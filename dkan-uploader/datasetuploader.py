
import json
import logging
import requests
from . import dkanhandler
from . import config
from .constants import Dataset

class DatasetUploader:
    """ Handle creation of Excel content """

    # runtime config
    current_row = 0

    def __init__(self):
        self.current_row = 0


    def getValue(self, dataset, value_name):
        if not value_name in dataset:
            logging.error(_("Pflichtfeld ist leer %s", value_name))
            value = ''
        else:
            value = dataset[value_name]
        return value


    def processDataset(self, dataset, resources):

        if not dataset:
            raise Exception(_("Fehler: Kein Datensatz zum Erstellen in datasetuploader.processDataset()"))

        logging.debug("dataset %s", dataset)
        logging.debug("resources %s", resources)

        dataset_id = None
        if dataset.getValue(Dataset.NODE_ID):
            # update existing datasetlogging.error
            dataset_id = dataset.getValue(Dataset.NODE_ID)
            dkanhandler.update(dataset_id, dataset)

        elif dataset.getValue(Dataset.DATASET_ID):
            # update by package_id
            package_id = dataset.getValue(Dataset.DATASET_ID)
            remote_url = config.x_api_find_node_id.format(package_id)
            r = requests.get(remote_url)
            node_search = json.load(r.text)

            if node_search[0]['nid']:
                dataset_id = node_search[0]['nid']
                dkanhandler.update(dataset_id, dataset)
            else:
                logging.error(_("Datensatz mit der ID %s wurde nicht gefunden"), package_id)

        else:
            # create new dataset
            dataset_id = dkanhandler.create(dataset)
            logging.debug(_("NEUE Dataset-ID: %s"), dataset_id)

        if not dataset_id:
            raise Exception(_("Fehler beim Erstellen oder beim Update des Datensatzes"))

        # add or update resources
        raw_dataset = dkanhandler.getDatasetDetails(dataset_id)
        self.processResources(raw_dataset, resources)

        return dataset_id


    def deleteDataset(self, node_id):
        dkanhandler.remove(node_id)


    def processResources(self, raw_dataset, resources):

        if (('field_resources' in raw_dataset) and ('und' in raw_dataset['field_resources'])):
            existingResources = raw_dataset['field_resources']['und']
            if existingResources:

                importOptions = {} # TODO .. das feature wieder einbauen
                dkanhandler.updateResources(
                    resources,
                    existingResources,
                    raw_dataset,
                    ('force' in importOptions)
                )
        else:
            # Create all resources
            for resource in resources:
                dkanhandler.createResource(resource, raw_dataset['nid'], raw_dataset['title'])

