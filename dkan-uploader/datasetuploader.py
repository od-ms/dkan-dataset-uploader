
import json
import logging
import requests
from jsondiff import diff
from . import dkanhandler
from . import dkanhelpers
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

        logging.info(_("Bearbeite Datensatz: %s"), dataset)
        logging.debug(_("Resourcen: %s"), resources)

        node_id = dataset.getValue(Dataset.NODE_ID)
        if node_id:
            # update existing dataset by node_id
            node_id = self.updateDataset(dataset)

        elif dataset.getValue(Dataset.DATASET_ID):
            # update by package_id
            package_id = dataset.getValue(Dataset.DATASET_ID)
            if not node_id:
                remote_url = config.x_api_find_node_id.format(package_id)
                r = requests.get(remote_url)
                node_search = json.load(r.text)

                if node_search[0]['nid']:
                    node_id = node_search[0]['nid']
                    dataset.set(Dataset.NODE_ID, node_id)

                node_id = self.updateDataset(dataset)
            else:
                logging.error(_("Datensatz mit der Package-ID '%s' wurde nicht gefunden"), package_id)

        else:
            # create new dataset
            node_id = dkanhandler.create(dataset)
            logging.debug(_("NEUE Dataset-ID: %s"), node_id)

        if not node_id:
            raise Exception(_("Fehler beim Erstellen oder beim Update des Datensatzes"))

        elif node_id == '-':
            return None

        # add or update resources
        raw_dataset = dkanhandler.getDatasetDetails(node_id)

        # TODO remove this if diff is always empty
        raw_dataset2 = dkanhelpers.HttpHelper.read_dkan_node(node_id)
        logging.debug(_(" == Dieser Datensatz-Diff sollte leer sein: == "))
        logging.debug(diff(raw_dataset, raw_dataset2))

        self.processResources(raw_dataset, resources)

        return node_id

    def updateDataset(self, dataset):
        package_id = dataset.getValue(Dataset.DATASET_ID)
        node_id = dataset.getValue(Dataset.NODE_ID)

        if config.dataset_ids and (config.dataset_ids.find(package_id) == -1):
            logging.debug(_("%s nicht in Abfrage '%s'"), package_id, config.dataset_ids)
            return '-'

        elif config.dataset_ids:
            logging.info(_("Datensatz gefunden: %s(%s) ist in '%s'"), package_id, node_id, config.dataset_ids)
            return dkanhandler.update(dataset)

        else:
            return dkanhandler.update(dataset)




    def deleteDataset(self, node_id):
        dkanhandler.remove(node_id)


    def processResources(self, raw_dataset, resources):

        if (('field_resources' in raw_dataset) and ('und' in raw_dataset['field_resources'])):
            existingResources = raw_dataset['field_resources']['und']
            if existingResources:

                importOptions = {} # TODO .. das "force" feature wieder einbauen?

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
