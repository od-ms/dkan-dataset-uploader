"""Module to handle DKAN API calls"""
import re
from typing import List
import json
import logging
from dkan.client import DatasetAPI, LoginError
from .constants import Dataset, Resource, ResourceType, AbortProgramError
from . import dkanhelpers
from . import config

# pylint: disable=global-statement

api = None

def expand_into(varname, id_list):
    result = []
    for single_id in id_list:
        result.append({varname: single_id})
    return result

def getDkanData(dataset: Dataset):
    """Generate default data for DKAN Datasets"""

    # if description does not contain html, then add html linebreaks
    description = dataset.getValue(Dataset.DESCRIPTION)
    if ('\n' in description) and '<' not in description:
        description = description.replace('\n', '<br />')

    dkanData = {
        "type": "dataset",
        "title": dataset.getValue(Dataset.TITLE),
        "body": {"und": [{
            "value": description,
            "format": dataset.getValue(Dataset.TEXT_FORMAT, "full_html")   # plain_text, full_html, ...
        }]}
    }

    if dataset.getValue(Dataset.AUTHOR):
        dkanData["field_author"] = {"und": [{"value": dataset.getValue(Dataset.AUTHOR)}]}
    if dataset.getValue(Dataset.CONTACT_EMAIL):
        dkanData["field_contact_email"] = {"und": [{"value": dataset.getValue(Dataset.CONTACT_EMAIL)}]}
    if dataset.getValue(Dataset.CONTACT_NAME):
        dkanData["field_contact_name"]= {"und": [{"value": dataset.getValue(Dataset.CONTACT_NAME)}]}
    if dataset.getValue(Dataset.GEO_LOCATION):
        dkanData["field_spatial_geographical_cover"]= {"und": [{"value": dataset.getValue(Dataset.GEO_LOCATION)}]}
    if dataset.getValue(Dataset.GEO_AREA):
        dkanData["field_spatial"] = {"und":[{"wkt":dataset.getValue(Dataset.GEO_AREA)}]}
    # LICENS
    # LICENSE_CUSTOM
    # [x] DESCRIPTION s.o.
    # [x] TEXT_FORMAT s.o.
    # URL ?
    if dataset.getValue(Dataset.HOMEPAGE):
        dkanData["field_landing_page"] = {"und": [{"url": dataset.getValue(Dataset.HOMEPAGE)}]}

    if dataset.getRawValue(Dataset.TAGS):
        dkanData["field_tags"] ={"und": expand_into("tid", dataset.getValue(Dataset.TAGS))}


    if dataset.getRawValue(Dataset.GROUPS):
        # check if the desired groups are really in the system, otherwise dkan will throw error
        group_ids = dataset.getValue(Dataset.GROUPS)
        groups = []
        for group_name, group_id in group_ids:
            group_data = dkanhelpers.HttpHelper.read_dkan_node(group_id)
            if not (("type" in group_data) and (group_data['type'] == "group")):
                logging.error("Datensatz kann nicht angelegt werden, weil die Gruppe nicht gefunden wurde: %s ('%s')", group_id, group_name)
                raise RuntimeError("Unknown group " + group_id + " " + group_name)
            if group_data['title'] != group_name:
                logging.warning("Gruppenname %s weicht ab: '%s' != '%s'", group_id, group_name, group_data["title"])
            groups.append({"target_id": group_id})
        dkanData["og_group_ref"] ={"und": groups}

    if dataset.getValue(Dataset.FREQUENCY):
        dkanData["field_frequency"] = {"und": [{"value": dataset.getValue(Dataset.FREQUENCY)}]}
    if dataset.getValue(Dataset.GRANULARITY):
        dkanData["field_granularity"] = {"und": [{"value": dataset.getValue(Dataset.GRANULARITY)}]}
    if dataset.getValue(Dataset.DATA_DICT_TYPE):
        dkanData["field_data_dictionary_type"] = {"und": [{"value": dataset.getValue(Dataset.DATA_DICT_TYPE)}]}
    if dataset.getValue(Dataset.DATA_DICT):
        dkanData["field_data_dictionary"] = {"und": [{"value": dataset.getValue(Dataset.DATA_DICT)}]}
    if dataset.getValue(Dataset.PUBLIC_ACCESS_LEVEL):
        dkanData["field_public_access_level"] = {"und": [{"value": dataset.getValue(Dataset.PUBLIC_ACCESS_LEVEL)}]}
    if dataset.getValue(Dataset.LANG):
        dkanData["field_language"] = {"und": [{"value": dataset.getValue(Dataset.LANG)}]}
    if dataset.getValue(Dataset.DATA_STANDARD):
        dkanData["field_conforms_to"] = {"und": [{"url": dataset.getValue(Dataset.DATA_STANDARD)}]}

    if dataset.getValue(Dataset.RELATED_CONTENT):
        logging.debug("Converting data structure of 'related content' field:")
        relatedcontent = dataset.getValue(Dataset.RELATED_CONTENT)
        print(json.dumps(relatedcontent, indent=2))
        related_list = []
        for related_entry in relatedcontent:
            related_list.append({
                "title": related_entry[0],
                "url": related_entry[1],
                "attributes": []
                })
        dkanData["field_related_content"] = {"und": related_list}
        print(json.dumps(dkanData["field_related_content"], indent=2))

    # STATE = 'State'
    # DATE_CREATED = 'Created'
    # DATE_MODIFIED = 'Modified'


    if dataset.getRawValue(Dataset.KEYWORDS):
        tags_in_dataset = dataset.getValue(Dataset.KEYWORDS)
        dkanData["field_dataset_tags"] ={"und": expand_into("tid", tags_in_dataset)}

        # "field_granularity": {"und": [{"value": "longitude/latitude"}]},

        # list of api fields in dkan dokumentation:
        # https://github.com/GetDKAN/dkan/blob/7.x-1.x/modules/dkan/dkan_dataset/modules/dkan_dataset_content_types/dkan_dataset_content_types.features.field_base.inc

        # No longer working (2020-09-22)
        # "field_spatial": {"und": {"master_column": "wkt", "wkt": "{\"type\":\"FeatureCollection\",\"features\":[{\"type\":\"Feature\",\"geometry\":{\"type\":\"Polygon\",\"coordinates\":[[[7.5290679931641,51.89293553285],[7.5290679931641,52.007625513725],[7.7350616455078,52.007625513725],[7.7350616455078,51.89293553285]]]},\"properties\":[]}]}"}},
        # "field_tags": {"und": {"value_field": ("\"\"\"" + data['tags'] + "\"\"\"")}},
        # "field_license": {"und": {"select": "Datenlizenz Deutschland Namensnennung 2.0"}},
        # "field_license": {"und": [{"select": "Datenlizenz+Deutschland+–+Namensnennung+–+Version+2.0"}]},

        # working example for license (2020-09-22)
        # Valid values (confirmed): cc-zero, notspecified, cc-by
        # BUT => they will be added to field "custom license"..?
        # doesnt work: dL-de, dl-de/2.0
        # example: https://opendata.stadt-.de/api/dataset/node/41344.json
        # LICENSE list: https://github.com/GetDKAN/dkan/blob/7.x-1.x/modules/dkan/dkan_dataset/modules/dkan_dataset_content_types/dkan_dataset_content_types.license_field.inc#L64
        #"field_license": {"und": [{
        #    "value": "cc-by"
        #    # DOESNT HELP: "safe_value": "cc-zeroo" #"Datenlizenz Deutschland – Namensnennung – Version 2.0"
        #}]},

        # working example for tags (2020-09-22):
        # find tags ids on this page: https://opendata.stadt-.de/admin/structure/taxonomy/tags

    if dataset.getRawValue(Dataset.TEMPORAL_START):


        dkanData["field_temporal_coverage"] = {
            "und": [{
                "value": dataset.getRawValue(Dataset.TEMPORAL_START)
            }]
        }
        if dataset.getRawValue(Dataset.TEMPORAL_END):
            dkanData["field_temporal_coverage"]['und'][0]['value2'] = dataset.getRawValue(Dataset.TEMPORAL_END)


    extra_fields = dataset.getExtraFields()
    if extra_fields:
        logging.debug("additional_infos: %s", extra_fields)
        fieldWeight = 0
        additional_fields = []
        for field, value in extra_fields.items():
            if field and value:
                additional_fields.append({"first": field, "second": value, "_weight": fieldWeight})
                fieldWeight += 1
        dkanData["field_additional_info"] = {"und": additional_fields}

    return dkanData


def disconnect():
    global api
    api = None


def getApi():
    if not api:
        connect()
    return api


def connect():
    global api
    if api:
        return ""

    try:
        logging.debug(_("DKAN-Login: %s @ %s"), config.dkan_username, config.dkan_url)
        # Last parameter is debug mode: True = Debugging ON
        api = DatasetAPI(config.dkan_url, config.dkan_username, config.dkan_password, True)
        return ""
    except LoginError as err:
        logging.error(_("Fehler bei Verbindung zur DKAN-Instanz!"))
        logging.error(_("Fehlermeldung %s"), str(err))
        logging.error(_("Bitte prüfen Sie die angegebenen DKAN-Url und -Zugangsdaten."))
        return "Fehler: " + str(err)


def create(data: Dataset):
    connect()
    logging.info(_("Erstelle DKAN-Datensatz: %s"), data)
    res = api.node('create', data=getDkanData(data))
    logging.debug("result %s", res.text)
    json_response = res.json()
    if not 'nid' in json_response:
        logging.error(_('DKAN-Fehler beim Erstellen des Datensatzes:'))
        logging.error(_('Fehlermeldung: %s'), json_response)
        return None
    else:
        return json_response['nid']

    # BEKANNTE FEHLER
    # - "Fehler bei der Eingabe\u00fcberpr\u00fcfung des Feldes"
    #   => DKAN API hat ein Problem mit den Eingabedaten. Wahrscheinlich hat sich das Input-Json-Format geändert.


def update(dataset: Dataset):
    connect()
    logging.info(_("Datensatz-Update: %s"), dataset)
    response = api.node(
        'update',
        node_id=dataset.getValue(Dataset.NODE_ID),
        data=getDkanData(dataset)
    )
    if response.status_code != 200:
        logging.error(_("Fehler beim Datensatz-Update %s %s"), response, response.content)
        return None

    logging.info(_("Ergebnis vom Datensatz-Update: %s"), response.json())
    return dataset.getValue(Dataset.NODE_ID)


def remove(nodeId):
    connect()
    logging.debug(_('Lösche Datensatz %s'), nodeId)
    response = api.node('delete', node_id=nodeId)
    logging.debug(_("Lösch-Ergebnis: %s"), response.json())


def find(title):
    connect()
    params = {
        'parameters[type]': 'dataset',
        'parameters[title]': title
    }
    results = api.node(params=params).json()
    return results[0] if results else 0


def getDatasetDetails(nid):
    connect()
    r = api.node('retrieve', node_id=nid)
    if r.status_code == 404:
        raise Exception('Did not find existing dkan node:', nid)

    return r.json()


def getResourceDkanData(resource, nid, title):
    """Return dkan node json data structure for RESOURCES"""

    if not isinstance(resource, Resource):
        raise AbortProgramError("Fehlerhafter Aufruf von getResourceDkanData(..)")

    rFormat = resource.getValue(Resource.FORMAT)
    if rFormat[0:3] == "WFS":  # omit WFS Version in type
        rFormat = "WFS"

    if rFormat[0:3] == "WMS":  # omit WMS Details in type
        rFormat = "WMS"

    lowerFormat = rFormat.lower()
    formatLookup = dkanhelpers.HttpHelper.get_all_dkan_fileformats()
    formatId = 0
    if lowerFormat in formatLookup:
        formatId = formatLookup[lowerFormat]
    else:
        logging.warning('Unbekanntes Dateiformat: %s', rFormat)
        logging.warning('Wenn Sie dieses Dateiformat nutzen möchten, müssen Sie es erst über das DKAN-Adminstrationsinterface anlegen.')

    rTitle = resource.getValue(Resource.NAME)
    if not rTitle:
        rTitle = title + " - " + resource.getValue(Resource.FORMAT)
        if rFormat == "HTML":
            rTitle = title + " - " + "Vorschau"

    rData = {
        "type": "resource",
        "field_dataset_ref": {"und": [{"target_id": nid}]},
        "title": rTitle,
        "body": {"und": [{
            "value": resource.getValue(Resource.DESCRIPTION),
            "format": resource.getValue(Resource.DESCRIPTION_FORMAT) if resource.getValue(Resource.DESCRIPTION_FORMAT) else 'plain_text'
        }]},
        "field_format": {"und": [{"tid": formatId}]},
        "field_link_remote_file": {"und": [{
            "filefield_dkan_remotefile": {"url": ""},
            "fid": 0,
            "display": 1
        }]},
        "field_link_api": {"und": [{"url": ""}]}
    }

    fileUploadPath = resource.getUploadFilePath()
    if fileUploadPath:
        rData.update({
            "upload_file": fileUploadPath,
        })

    elif resource.getValue(Resource.TYP) == ResourceType.TYPE_DATASTORE:
        raise AbortProgramError("Nicht implementiert: Resource Type Datastore!!")

    elif resource.getValue(Resource.TYP) == ResourceType.TYPE_REMOTE_FILE:
        rData.update({
            "field_link_remote_file": {"und": [{
                "filefield_dkan_remotefile": {"url": resource.getValue(Resource.URL)},
                "fid": 0,
                "display": 1
            }]}
        })
    else:
        rData.update({
            "field_link_api": {"und": [{"url": resource.getValue(Resource.URL)}]},
        })

    return rData


def createResource(resource: Resource, nid, title):
    data = getResourceDkanData(resource, nid, title)
    createResourceFromData(data)


def createResourceFromData(data):
    connect()
    logging.info(_(" -> [wird erstellt] %s"), data['title'])
    r = api.node('create', data=data)
    if r.status_code != 200:
        raise Exception('Error during create resource:', r, r.text)
    resourceResponse = r.json()
    newResourceNodeId = resourceResponse['nid']
    logging.debug(_('  Neue Resource wurde erstellt: %s'), newResourceNodeId)
    handleFileUpload(data, newResourceNodeId)


def updateResource(data, existingResource):
    connect()
    nodeId = existingResource['nid']
    logging.info(_(" '-> [aktualisiere] %s %s"), nodeId, data['title'])
    if 'upload_file' in data:
        # There seems to be a bug in DKAN:
        # I did not manage to update a resource that has an uploaded file.
        # Always receives weird http 500 errors from server:
        # "500 Internal Server Error : An error occurred (HY000): SQLSTATE[HY000]:
        #     General error: 1366 Incorrect integer value: '' for column 'field_upload_grid' at row 1"
        # So we delete and recreate if necessary:
        removeHtml = re.compile(r'(<!--.*?-->|<[^>]*>)')
        body1 = body2 = ""
        if "body" in data:
            body1 = removeHtml.sub('', data['body']['und'][0]['value'])
        if ("body" in existingResource) and ("und" in existingResource["body"]):
            body2 = removeHtml.sub('', existingResource['body']['und'][0]['value'])

        if (data['title'] != existingResource['title']) or (body1 != body2):
            logging.debug("[DELETE NODE AND RECREATE] (required if changes in name or description of resources with file uploads)")
            logging.debug('newtitle: %s', data['title'])
            logging.debug('oldTitle: %s', existingResource['title'])
            logging.debug("newBody: %s", body1)
            logging.debug("oldBody: %s", body2)

            response = api.node('delete', node_id=nodeId)
            if response.status_code != 200:
                logging.error(_("Fehler: %s - %s"), response, response.content)
                raise Exception('Error during resource update:', response, response.text)

            createResourceFromData(data)
        else:
            handleFileUpload(data, nodeId)
    else:
        r = api.node('update', node_id=nodeId, data=data)
        if r.status_code != 200:
            logging.error(_("ERROR %s %s"), r, r.content)
            raise Exception('Error during resource update:', r, r.text)


def handleFileUpload(data, nodeId):
    connect()

    if "upload_file" in data:
        filename = data["upload_file"]
        logging.info(_("  Datei-Upload zu Resource %s: %s"), nodeId, filename)
        logging.debug(_("  Node Daten: %s"), data)
        aResponse = api.attach_file_to_node(filename, nodeId, 'field_upload')
        logging.debug(_("  Ergebnis: %s - %s"), aResponse.status_code, aResponse.text)


def updateResources(newResources:List[Resource], existingResources, dataset, forceUpdate):
    connect()
    logging.info(_("Prüfe bestehende Resourcen:"))

    for existingResource in existingResources:
        logging.info(_("  Resource-ID %s"), existingResource['target_id'])
        # ^ existingResource is crap, because it's only a list of target_ids!
        # Don't use existingResource, use resourceData instead!

        resourceData = getDatasetDetails(existingResource['target_id'])

        logging.debug("%s", [x.getUniqueId() for x in newResources])

        # check if the existing resource url also is in the new resource urls
        el = [x for x in newResources if x.equals_existing_resource(resourceData)]
        if el:
            # Found url => That means this is an update

            # remove element from the resources that will be created
            newResource = el[0]
            newResources.remove(newResource)
            # Only update if resource title has changed
            newData = getResourceDkanData(newResource, dataset['nid'], dataset['title'])
            if (newData['title'] != resourceData['title']) or forceUpdate:
                updateResource(newData, resourceData)
            else:
                logging.info(_("  '-> [nicht geändert] %s"), newResource)
        else:
            # This seems to be an old url that we dont want anymore => delete it
            logging.info(_("  '-> [löschen] %s"), existingResource)
            op = api.node('delete', node_id=existingResource['target_id'])
            logging.debug(_("Ergebnis: Status=%s, Text=%s"), op.status_code, op.text)

    # Create new resources
    for resource in newResources:
        createResource(resource, dataset['nid'], dataset['title'])
