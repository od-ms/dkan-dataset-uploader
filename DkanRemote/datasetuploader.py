
import re
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

    _ignore_resources = False
    limit = 100000
    dataset_count = 0

    def __init__(self):
        self.dataset_count = 0
        dataset_query = config.dataset_ids
        match = re.search(r'limit\s*=\s*(\d+)\s*',dataset_query,flags = re.S|re.M)
        if match:
            self.limit = int(match.group(1))
            logging.info(_("Beschränkung per 'Limit'-Query auf %s Datensätze."), self.limit)

    def setIngoreResources(self, val):
        self._ignore_resources=val


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

        if self.limit:
            logging.debug(_("Datensatz: %s/%s"), self.dataset_count, self.limit)

        if self.dataset_count >= self.limit:
            logging.info(_("Datensatz wird übersprungen. Limit von %s erreicht."), self.limit)
            return None

        logging.info(_("Bearbeite Datensatz: '%s'"), dataset)
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
            self.dataset_count += 1
            node_id = dkanhandler.create(dataset)
            logging.debug(_("NEUE Dataset-ID: %s"), node_id)

        if not node_id:
            raise Exception(_("Fehler beim Erstellen oder beim Update des Datensatzes"))

        elif node_id == '-':
            return None

        raw_dataset = dkanhandler.getDatasetDetails(node_id)

        # Summary with changes
        raw_dataset2 = dkanhelpers.HttpHelper.read_dkan_node(node_id)
        logging.debug(_(" == Datensatz-Änderung: == "))
        logging.debug(diff(raw_dataset, raw_dataset2))

        # add or update resources
        if not self._ignore_resources:
            self.processResources(raw_dataset, resources)

        return node_id


    def updateDataset(self, dataset):
        package_id = dataset.getValue(Dataset.DATASET_ID)
        node_id = dataset.getValue(Dataset.NODE_ID)

        p = re.compile('[-\w]*limit\s*=\s*(\d+)[\w,]*')
        dataset_query = p.sub('', config.dataset_ids)

        if dataset_query and (dataset_query.find(package_id) == -1):
            logging.warning(_("Wird übersprungen wegen Datensatz-Beschränkung: '%s' nicht in '%s'"), package_id, dataset_query)
            return '-'

        elif dataset_query:
            logging.info(_("Datensatz-Beschränkung passt: %s(%s) ist in '%s'"), package_id, node_id, dataset_query)
            self.dataset_count += 1
            return dkanhandler.update(dataset)

        else:
            self.dataset_count += 1
            return dkanhandler.update(dataset)


    def deleteDataset(self, node_id):
        dkanhandler.remove(node_id)


    def processResources(self, raw_dataset, resources):

        if (('field_resources' in raw_dataset) and ('und' in raw_dataset['field_resources'])):
            existingResources = raw_dataset['field_resources']['und']
            if existingResources:

                dkanhandler.updateResources(
                    resources,
                    existingResources,
                    raw_dataset
                )
        else:
            # Create all resources
            for resource in resources:
                dkanhandler.createResource(resource, raw_dataset['nid'], raw_dataset['title'])
