

from contextlib import closing
import re
import csv
import sys
import json
import codecs
import logging
import requests
from . import dkanhandler
from . import config


class DatasetUploader:
    """ Handle creation of Excel content """

    # runtime config
    current_row = 0
    dkanhandler = None

    def __init__(self):
        self.current_row = 0
        # dkanhandler.connect(config)


    def getValue(self, dataset, value_name):
        if not value_name in dataset:
            logging.error(_("Pflichtfeld ist leer %s", value_name))
            value = ''
        else:
            value = dataset[value_name]
        return value


    def processDataset(self, dataset, resources):


        logging.debug("dataset %s", dataset)
        logging.debug("resources %s", resources)
        raise ValueError("Noch nicht fertigprogrammiert")

        data = {}
        resources = []

        # TODO 'Resource-ID': 'id',
        # [x] 'Resource-Name': 'name',
        # [x] 'Format': 'format',
        # [x] 'Externe Url': 'url',
        # [x] 'Description': 'description',
        # 'Prüfung OK?': 'response_ok',
        # 'HTTP-Responsecode':'response_code'

        resources.append({
            "type": self.getValue(dataset, 'Format'),
            "url": self.getValue(dataset, 'Externe Url'),
            "title": self.getValue(dataset, 'Resource-Name'),
            "body": self.getValue(dataset, 'Description'),
            "storage": '' # TODO: denkbar wäre z.B. a) remote / b) download to dkan / c) import into dkan datastore
        })

        self.importer(data, resources)




    def importer(self, data, resources):

        try:
            # Special feature: download external resources
            # E.g. this can be used for "desc-external" => if this contains a url then "desc" is filled with the content from that url.
            if 'storage':
                logging.error("download of external resources to dkan is not implemented")




                fieldName = hashkey[0:-9]
                downloadUrl = data[hashkey]
                print("Downloading external content for '" + fieldName + "':", downloadUrl)
                r = requests.get(downloadUrl)
                data[fieldName] = (data[fieldName] if fieldName in data else '') + r.text


            if ('nid' in data) and data['nid']:
                existingDataset = dkanhandler.getDatasetDetails(data['nid'])
            else:
                existingDataset = dkanhandler.find(data['name'])
            print()
            print('-----------------------------------------------------')
            print(data['name'], existingDataset['nid'] if existingDataset and 'nid' in existingDataset else ' => NEW')
            if existingDataset:
                nid = existingDataset['nid']
                dkanhandler.update(nid, data)
            else:
                nid = dkanhandler.create(data)

            dataset = dkanhandler.getDatasetDetails(nid)
            # print("RETRIEVED", dataset)
            self.updateResources(dataset, resources)
            datasets.append(nid)

        except:
            print("data", json.dumps(data))
            print("resources", resources)
            print("existingDataset", existingDataset)
            print("Unexpected error:", sys.exc_info())
            raise


    def updateResources(self, dataset, resourcesFromCsv):
        if (('field_resources' in dataset) and ('und' in dataset['field_resources'])):
            existingResources = dataset['field_resources']['und']
            if existingResources:
                dkanhandler.updateResources(resourcesFromCsv, existingResources, dataset, ('force' in importOptions))
        else:
            # Create all resources
            for resource in resources:
                dkanhandler.createResource(resource, dataset['nid'], dataset['title'])

