"""Module to handle DKAN API calls"""
import re
import os
import hashlib
import requests
import logging
from dkan.client import DatasetAPI, LoginError

api = None


def getDkanData(data):
    """Generate default data for DKAN Datasets"""
    if not(data['name'] and data['desc'] and data['tags']):
        raise Exception('Missing data entry', data)

    # if description does not contain html, then add html linebreaks
    description = data['desc']
    if ('\n' in description) and '<' not in description:
        description = description.replace('\n', '<br />')

    if (not data['tags'].isnumeric()):
        raise Exception('Aufgrund DKAN API Änderungen müssen Tags derzeit als IDs angegeben werden', data)

    dkanData = {
        "type": "dataset",
        "title": data['name'],
        "body": {"und": [{
            "value": description,
            "format": "full_html"  # plain_text, full_html, ...
        }]},
        "field_author": {"und": [{"value": "Stadt "}]},
        "field_contact_email": {"und": [{"value": "opendata@stadt"}]},
        "field_contact_name": {"und": [{"value": "Open Data Koordination der Stadt"}]},
        "og_group_ref": {"und": [{"target_id": 40612}]},
        "field_spatial_geographical_cover": {"und": [{"value": "somewhere"}]},
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
        "field_license": {"und": [{
            "value": "cc-by"
            # DOESNT HELP: "safe_value": "cc-zeroo" #"Datenlizenz Deutschland – Namensnennung – Version 2.0"
        }]},

        # working example for spatial (2020-09-22)
        "field_spatial":{"und":[{"wkt":"POLYGON ((7.5290679931641 51.89293553285, 7.5290679931641 52.007625513725, 7.7350616455078 52.007625513725, 7.7350616455078 51.89293553285))","geo_type":"polygon","lat":"51.9503","lon":"7.63206","left":"7.52907","top":"52.0076","right":"7.73506","bottom":"51.8929","srid":"","accuracy":"","source":""}]},

        # working example for tags (2020-09-22):
        # find tags ids on this page: https://opendata.stadt-.de/admin/structure/taxonomy/tags
        "field_tags":{"und": [{"tid": data['tags']}] }
    }

    groupData = {
        #...
    }

    # TODO groups muss repariert werden
    if ("group" in data) and data["group"]:
        if not data["group"] in groupData:
            raise Exception("groupData not found for group. Please define the following group in dkanhandler.py:", data["group"])
        dkanData.update(groupData[data["group"]])

    if "homepage" in data:
        dkanData["field_landing_page"] = {
            "und": [{"url": data["homepage"]}]
        }

    if "start" in data:
        dkanData["field_temporal_coverage"] = {
            "und": [{
                "value": {
                    "time": "00:00:00",
                    "date": data["start"]  # "MM/DD/YYYY"
                }
            }]
        }

    if "end" in data:
        # field_temporal_coverage%5Bund%5D%5B0%5D%5Bshow_todate%5D: 1
        # field_temporal_coverage%5Bund%5D%5B0%5D%5Bvalue2%5D%5Bdate%5D: 11%2F13%2F2019
        # field_temporal_coverage%5Bund%5D%5B0%5D%5Bvalue2%5D%5Btime%5D: 00%3A00%3A00
        print("ENDDATE NOT IMPLEMENTED")

    if "frequency" in data:
        dkanData["field_frequency"] = {
            "und": data["frequency"]
        }

    fieldWeight = 0
    additionalFields = [
        {"first": "Kennziffer", "second": data['id'], "_weight": fieldWeight}
    ]

    if "musterds" in data:
        fieldWeight += 1
        additionalFields.append({"first": "Kategorie", "second": data['musterds'], "_weight": fieldWeight})
    if "Koordinatenreferenzsystem" in data:
        fieldWeight += 1
        additionalFields.append({"first": "Koordinatenreferenzsystem", "second": data['Koordinatenreferenzsystem'], "_weight": fieldWeight})
    if "Quelle" in data:
        fieldWeight += 1
        additionalFields.append({"first": "Quelle", "second": data['Quelle'], "_weight": fieldWeight})

    # TODO: These are broken, check the changes in API and fix it
    # dkanData["field_additional_info"] = {"und": additionalFields}

    return dkanData


def connect(args):
    global api
    logging.debug("DKAN url: %s", args.dkan_url)
    try:
        # Last parameter is debug mode: True = Debugging ON
        api = DatasetAPI(args.dkan_url, args.dkan_username, args.dkan_password, True)
        return ""
    except LoginError as err:
        return "Fehler: " + str(err)



def create(data):
    global api
    print("Creating", data['name'])
    res = api.node('create', data=getDkanData(data))
    print("result", res.text)
    return res.json()['nid']

    # BEKANNTE FEHLER
    # - "Fehler bei der Eingabe\u00fcberpr\u00fcfung des Feldes"
    #   => DKAN API hat ein Problem mit den Eingabedaten. Wahrscheinlich hat sich das Input-Json-Format geändert.


def update(nodeId, data):
    global api
    print("Updating", data['name'])
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


def createResource(resource, nid, title):
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
