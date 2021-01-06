"""Module to handle DKAN API calls"""
import re
import os
import json
import hashlib
import logging
import requests
from dkan.client import DatasetAPI, LoginError
from .constants import Dataset, Resource
from . import dkanhelpers

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
    # TEMPORAL ...

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
        all_tags_in_dkan = dkanhelpers.HttpHelper.get_all_dkan_tags(api)
        tags_in_dataset = dataset.getValue(Dataset.KEYWORDS)
        correct_tags = []
        for tag in tags_in_dataset:
            if tag in all_tags_in_dkan:
                logging.debug("Gefundener Tag %s: '%s'", tag, all_tags_in_dkan[tag])
                correct_tags.append(tag)
            else:
                logging.error("Unbekannte Tag-ID %s wird verworfen!", tag)

        dkanData["field_dataset_tags"] ={"und": expand_into("tid", correct_tags)}

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

    #fieldWeight = 0
    #additionalFields = [
    #    {"first": "Kennziffer", "second": data['id'], "_weight": fieldWeight}
    #]

    #if "musterds" in data:
    #    fieldWeight += 1
    #    additionalFields.append({"first": "Kategorie", "second": data['musterds'], "_weight": fieldWeight})

    # TODO: These are broken, check the changes in API and fix it
    # dkanData["field_additional_info"] = {"und": additionalFields}

    return dkanData


def connect(args):
    global api
    if api:
        return ""

    try:
        logging.debug("DKAN url: %s", args.dkan_url)
        # Last parameter is debug mode: True = Debugging ON
        api = DatasetAPI(args.dkan_url, args.dkan_username, args.dkan_password, True)
        return ""
    except LoginError as err:
        return "Fehler: " + str(err)



def create(data: Dataset):
    global api
    logging.info(_("Erstelle DKAN-Datensatz: %s"), data)
    res = api.node('create', data=getDkanData(data))
    logging.debug("result %s", res.text)
    json = res.json()
    if not 'nid' in json:
        logging.error(_('DKAN-Fehler beim Erstellen des Datensatzes:'))
        logging.error(_('Fehlermeldung: %s'), json)
        return None
    else:
        return json['nid']

    # BEKANNTE FEHLER
    # - "Fehler bei der Eingabe\u00fcberpr\u00fcfung des Feldes"
    #   => DKAN API hat ein Problem mit den Eingabedaten. Wahrscheinlich hat sich das Input-Json-Format geändert.


def update(nodeId, data: Dataset):
    global api
    logging.info(_("Datensatz-Update: '%s'"), data)
    res = api.node('update', node_id=nodeId, data=getDkanData(data))
    print("result", res.json())


def find(title):
    global api
    params = {
        'parameters[type]': 'dataset',
        'parameters[title]': title
    }
    results = api.node(params=params).json()
    return results[0] if results else 0


def getDatasetDetails(nid):
    global api
    r = api.node('retrieve', node_id=nid)
    if r.status_code == 404:
        raise Exception('Did not find existing dkan node:', nid)

    return r.json()


def getResourceDkanData(resource, nid, title):
    """Return Base data for RESOURCE URLS"""
    isUpload = False

    if isinstance(resource, Resource):

        # TODO 'Resource-ID': 'id',
        # [x] 'Resource-Name': 'name',
        # [x] 'Format': 'format',
        # [x] 'Externe Url': 'url',
        # [x] 'Description': 'description',
        # 'Prüfung OK?': 'response_ok',
        # 'HTTP-Responsecode':'response_code'
        resource = {
            "type": resource.getValue(Resource.FORMAT),
            "url": resource.getValue(Resource.URL),
            "title": resource.getValue(Resource.NAME),
            "body": resource.getValue(Resource.DESCRIPTION),
            "storage": '' # TODO: denkbar wäre z.B. a) remote / b) download to dkan / c) import into dkan datastore
        }


    rFormat = resource['type']
    if rFormat[0:3] == "WFS":  # omit WFS Version in type
        rFormat = "WFS"

    if rFormat[0:3] == "WMS":  # omit WMS Details in type
        rFormat = "WMS"

    if rFormat[-7:] == '-upload':
        resource['type'] = rFormat = rFormat[0:-7]
        isUpload = True


    # Resource FORMAT ID LIST: https://opendata.stadt-.de/admin/structure/taxonomy/format
    # TODO: we should probably read this list from somewhere, as it can be different on every portal
    # BAAD it seems there is no API endpoint in DKAN to get this list
    formatLookup = {
        "csv": 69,
        "data": 70,
        "pdf": 74,
        "shape": 160,
        "wfs": 159,
        "xlsx": 169
    }
    lowerFormat = rFormat.lower()
    formatId = formatLookup[lowerFormat] if (lowerFormat in formatLookup) else 70

    rTitle = title + " - " + resource['type']
    if rFormat == "HTML":
        rTitle = title + " - " + "Vorschau"
    if ('title' in resource) and resource['title']:
        rTitle = resource['title']


    rData = {
        "type": "resource",
        "field_dataset_ref": {"und": [{"target_id": nid}]},
        "title": rTitle,
        "body": {"und": [{
            "value": resource['body'] if ("body" in resource) and resource['body'] else "",
            "format": "plain_text"
        }]},
        "field_format": {"und": [{"tid": formatId}]},
        "field_link_remote_file": {"und": [{
            "filefield_dkan_remotefile": {"url": ""},
            "fid": 0,
            "display": 1
        }]},
        "field_link_api": {"und": [{"url": ""}]}
    }
    if isUpload:
        rData.update({
            "upload_file": resource['url'],
        })
    elif rFormat == "REMOVEME---CSV":
        # TODO: Something is wrong here, fix it
        # New setting in our DKAN:
        #   "hochladen" or "external url" => SHOW PREVIEW IFRAME
        #   "api or website url" => dont show
        #
        # We want previews only for CSV, because of DSGVO
        rData.update({
            "field_link_remote_file": {"und": [{
                "filefield_dkan_remotefile": {"url": resource['url']},
                "fid": 0,
                "display": 1
            }]}
        })
    else:
        rData.update({
            "field_link_api": {"und": [{"url": resource['url']}]},
        })

    return rData


def createResource(resource: Resource, nid, title):
    data = getResourceDkanData(resource, nid, title)
    createResourceFromData(data)


def createResourceFromData(data):
    global api
    print("[create]", data['title'])
    r = api.node('create', data=data)
    if r.status_code != 200:
        raise Exception('Error during create resource:', r, r.text)
    resourceResponse = r.json()
    newResourceNodeId = resourceResponse['nid']
    print(newResourceNodeId, "[created]")
    handleFileUpload(data, newResourceNodeId)


def updateResource(data, existingResource):
    global api
    nodeId = existingResource['nid']
    print("[update]", nodeId, data['title'])
    if 'upload_file' in data:
        # There seems to be a bug in DKAN:
        # I did not manage to update a ressource that has an uploaded  file.
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
            print("[DELETE NODE AND RECREATE] (required if changes in name or description of resources with file uploads)")
            print('newtitle:', data['title'])
            print('oldTitle:', existingResource['title'])
            print("newBody:", body1)
            print("oldBody", body2)

            response = api.node('delete', node_id=nodeId)
            if response.status_code != 200:
                print("ERROR", response, response.content)
                raise Exception('Error during resource update:', response, response.text)

            createResourceFromData(data)
        else:
            handleFileUpload(data, nodeId)
    else:
        r = api.node('update', node_id=nodeId, data=data)
        if r.status_code != 200:
            print("ERROR", r, r.content)
            raise Exception('Error during resource update:', r, r.text)


def generateUploadFilename(url):
    return hashlib.md5(url.encode('utf-8')).hexdigest() + '.csv'


def handleFileUpload(data, nodeId):
    global api

    if "upload_file" in data:
        # download remote content
        downloadUrl = data["upload_file"]
        filename = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), '.', 'temp-files',
            generateUploadFilename(downloadUrl))
        print(nodeId, "[file-upload]", downloadUrl)
        print("    Temp file:", filename)
        del data['upload_file']
        fileContent = requests.get(downloadUrl)
        if fileContent.status_code != 200:
            raise Exception('Error during download')

        # save content to temp file
        tempFile = open(filename, "w")
        tempFile.write(fileContent.text)
        tempFile.close()

        # attach temp file to resource
        aResponse = api.attach_file_to_node(filename, nodeId, 'field_upload')
        print(aResponse.status_code, aResponse.text)


def updateResources(newResources, existingResources, dataset, forceUpdate):
    print("CHECKING RESOURCES")

    # add unique ids to newResources
    for res in newResources:
        if res['type'][-7:] == '-upload':
            res["uniqueId"] = generateUploadFilename(res["url"])
        else:
            res["uniqueId"] = res["url"]

    for existingResource in existingResources:
        print(existingResource['target_id'], end=' ')
        # TODO: existingResource is crap, because it's only a list of target_ids!
        # TODO: Don't use existingResource, use resourceData instead!

        resourceData = getDatasetDetails(existingResource['target_id'])
        if "und" in resourceData['field_link_api']:
            uniqueId = resourceData['field_link_api']['und'][0]['url']
        elif 'und' in resourceData['field_link_remote_file']:
            uniqueId = resourceData['field_link_remote_file']['und'][0]['uri']
        elif 'und' in resourceData['field_upload']:
            uniqueId = resourceData['field_upload']['und'][0]['filename']
        else:
            print("[EXISTING RESOURCE WITHOUT URL -> MAKES NO SENSE -> DELETE]")
            uniqueId = resourceData['nid']

        # check if the existing resource url also is in the new resource urls
        el = [x for x in newResources if x['uniqueId'] == uniqueId]
        if el:
            # Found url => That means this is an update

            # remove element from the resources that will be created
            newResources = [x for x in newResources if x['uniqueId'] != uniqueId]

            # Only update if resource title has changed
            newData = getResourceDkanData(el[0], dataset['nid'], dataset['title'])
            if (newData['title'] != resourceData['title']) or forceUpdate:
                updateResource(newData, resourceData)
            else:
                print("[no-change]", el[0]["url"])
        else:
            # This seems to be an old url that we dont want anymore => delete it
            print("[remove]", existingResource)
            op = api.node('delete', node_id=existingResource['target_id'])
            print(op.status_code, op.text)

    # Create new resources
    for resource in newResources:
        createResource(resource, dataset['nid'], dataset['title'])
