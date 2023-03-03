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

import requests
import warnings
import contextlib
from urllib3.exceptions import InsecureRequestWarning


old_merge_environment_settings = requests.Session.merge_environment_settings

# Fix problems with broken SSL certificates
# ref. https://stackoverflow.com/questions/15445981/how-do-i-disable-the-security-certificate-check-in-python-requests
@contextlib.contextmanager
def no_ssl_verification():
    opened_adapters = set()

    def merge_environment_settings(self, url, proxies, stream, verify, cert):
        # Verification happens only once per connection so we need to close
        # all the opened adapters once we're done. Otherwise, the effects of
        # verify=False persist beyond the end of this context manager.
        opened_adapters.add(self.get_adapter(url))

        settings = old_merge_environment_settings(self, url, proxies, stream, verify, cert)
        settings['verify'] = False

        return settings

    requests.Session.merge_environment_settings = merge_environment_settings

    try:
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', InsecureRequestWarning)
            yield
    finally:
        requests.Session.merge_environment_settings = old_merge_environment_settings

        for adapter in opened_adapters:
            try:
                adapter.close()
            except:
                pass

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
    if dataset.getValue(Dataset.HOMEPAGE):
        dkanData["field_landing_page"] = {"und": [{"url": dataset.getValue(Dataset.HOMEPAGE)}]}

    if dataset.getRawValue(Dataset.GROUPS):
        # check if the desired groups are really in the system, otherwise dkan will throw error
        group_ids = dataset.getValue(Dataset.GROUPS)
        groups = []
        for group_name, group_id in group_ids:
            group_data = dkanhelpers.HttpHelper.read_dkan_node(group_id)
            if not (("type" in group_data) and (group_data['type'] == "group")):
                logging.error(_("Datensatz kann nicht angelegt werden, weil die Gruppe nicht gefunden wurde: %s ('%s')"), group_id, group_name)
                logging.warning(_("Bitte legen Sie die Gruppe '%s' in ihrem DKAN an."),  group_name)
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
    if dataset.getValue(Dataset.LICENSE):
    #    dkanData["field_license"] = {"und": [
    #        {"select": "select_or_other",
    #        "other": [{ "value": dataset.getValue(Dataset.LICENSE)}] }]}
        dkanData["field_license"] = {"und": [
            {"value": dataset.getValue(Dataset.LICENSE)}] }

    # I guess these can all have multiple values ... TODO!
    if dataset.getValue(Dataset.DD_GEO_A):
        dkanData["field_spatial_geographical_cover"] = {"und": [{"value": dataset.getValue(Dataset.DD_GEO_A)}]}
    if dataset.getValue(Dataset.DD_LEGAL):
        dkanData["field_dcatapde_legalbase"] = {"und": [{"value": dataset.getValue(Dataset.DD_LEGAL)}]}
    if dataset.getValue(Dataset.DD_OTHER):
        dkanData["field_dcatapde_otherid"] = {"und": [{"value": dataset.getValue(Dataset.DD_OTHER)}]}
    if dataset.getValue(Dataset.DD_PROV):
        dkanData["field_dcatapde_provenance"] = {"und": [{"value": dataset.getValue(Dataset.DD_PROV)}]}

    for nextField in [Dataset.RELATED_CONTENT, Dataset.DD_CONTRIBUTOR, Dataset.DD_CREATOR, Dataset.DD_MAINTAINER,
        Dataset.DD_ORIGINATOR, Dataset.DD_PUBLISHER, Dataset.DD_GEONAMES, Dataset.DD_REL, Dataset.DD_SOURCE,
        Dataset.DD_QUAL]:

        if dataset.getValue(nextField):
            logging.debug("Converting data structure of 'related content' field:")
            relatedkey, relatedcontent = dataset.getTitleUrlAttributes(nextField)
            dkanData[relatedkey] = {"und": relatedcontent}
            print(json.dumps(dkanData[relatedkey], indent=2))

    for nextField in [Dataset.DD_GEOCODE, Dataset.DD_GEOLEVEL, Dataset.KEYWORDS, Dataset.TAGS, Dataset.DD_GRANU,
        Dataset.DD_LANG, Dataset.DD_PLACE, Dataset.DD_THEME]:
        if dataset.getRawValue(nextField):
            relatedkey, relatedcontent = dataset.getFieldNameAndTaxonomyValue(nextField)
            dkanData[relatedkey] ={"und": expand_into("tid", relatedcontent)}

    if dataset.getRawValue(Dataset.DD_TSTART):
        dkanData["field_dcatapde_temporal"] = {
            "und": [{
                "value": dataset.getRawValue(Dataset.DD_TSTART)
            }]
        }
        if dataset.getRawValue(Dataset.DD_TEND):
            dkanData["field_dcatapde_temporal"]['und'][0]['value2'] = dataset.getRawValue(Dataset.DD_TEND)


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
        with no_ssl_verification():
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


def getResourceDkanData(resource, nid, title, existingDataNode):
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

    # if updating an existing uploaded file - we need to copy over the old "filed_upload" values, otherwise update will fail with 505 error
    rTypeDetailed = resource.getRawValue(Resource.TYP2)
    if existingDataNode and (rTypeDetailed == ResourceType.TYPE_UPLOAD) and ("field_upload" in existingDataNode) and existingDataNode["field_upload"]:
        logging.debug("file is uploaded")
        rData.update({
            "field_upload": existingDataNode["field_upload"]
        })

    # if new file should be uploaded, add our internal field "x_upload_file" for later use
    fileUploadPath = resource.getUploadFilePath()
    if fileUploadPath:
        rData.update({
            "x_upload_file": fileUploadPath,
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
    elif not ("field_upload" in rData):
        rData.update({
            "field_link_api": {"und": [{"url": resource.getValue(Resource.URL)}]},
        })

    for nextField in [Resource.DD_LICENSE, Resource.DD_STATUS, Resource.DD_LANGUAGE, Resource.DD_AVAIL]:
        if resource.getRawValue(nextField):
            relatedkey, relatedcontent = resource.getFieldNameAndTaxonomyValue(nextField)
            rData[relatedkey] ={"und": expand_into("tid", relatedcontent)}

    if resource.getValue(Resource.DD_RIGHTS):
        rData["field_dcatapde_rights"] = {"und": [{"url": resource.getValue(Resource.DD_RIGHTS)}]}
    if resource.getValue(Resource.DD_LICENSETEXT):
        rData["field_dcatapde_licatt"] = {"und": [{"value": resource.getValue(Resource.DD_LICENSETEXT)}]}
    if resource.getValue(Resource.DD_CONFORM):
        rData["field_conforms_to"] = {"und": [{"url": resource.getValue(Resource.DD_CONFORM)}]}

    return rData


def createResource(resource: Resource, nid, title):
    data = getResourceDkanData(resource, nid, title, None)
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


def updateResource(data, oldData):
    connect()
    nodeId = oldData['nid']
    logging.info(_(" '-> [aktualisiere] %s %s"), nodeId, data['title'])
    if 'x_upload_file' in data:
        if None:
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
            if ("body" in oldData) and ("und" in oldData["body"]):
                body2 = removeHtml.sub('', oldData['body']['und'][0]['value'])

            if (data['title'] != oldData['title']) or (body1 != body2):
                logging.debug("[DELETE NODE AND RECREATE] (required if changes in name or description of resources with file uploads)")
                logging.debug('newtitle: %s', data['title'])
                logging.debug('oldTitle: %s', oldData['title'])
                logging.debug("newBody: %s", body1)
                logging.debug("oldBody: %s", body2)

                response = api.node('delete', node_id=nodeId)
                if response.status_code != 200:
                    logging.error(_("Fehler: %s - %s"), response, response.content)
                    raise Exception('Error during resource update:', response, response.text)

                createResourceFromData(data)
            else:
                handleFileUpload(data, nodeId)

        handleFileUpload(data, nodeId)

    else:
        r = api.node('update', node_id=nodeId, data=data)
        logging.debug("  update: result %s", r)
        if r.status_code != 200:
            logging.error(_("FEHLER %s %s"), r, r.content)
            raise Exception('Error during resource update:', r, r.text)


def handleFileUpload(data, nodeId):
    connect()

    if "x_upload_file" in data:
        filename = data["x_upload_file"]
        logging.info(_("  Datei-Upload zu Resource %s: %s"), nodeId, filename)
        logging.debug(_("  Node Daten: %s"), data)
        aResponse = api.attach_file_to_node(filename, nodeId, 'field_upload')
        logging.debug(_("  Ergebnis: %s - %s"), aResponse.status_code, aResponse.text)


def updateResources(newResources:List[Resource], existingResourceIds, dataset):
    connect()

    logging.info(_("Prüfe bestehende Resourcen: (forceUpdate=%s)"), config.force_resource_update)

    for existingResourceId in existingResourceIds:
        logging.info(_(" Checke Resource-ID %s:"), existingResourceId['target_id'])

        oldData = getDatasetDetails(existingResourceId['target_id'])

        logging.debug("%s", [x.getUniqueId() for x in newResources])

        # check if the existing resource url also is in the new resource urls
        el = [x for x in newResources if x.equals_existing_resource(oldData)]
        if el:
            # Found url => That means this is an update

            # remove element from the resources that will be created
            newResource = el[0]
            newResources.remove(newResource)

            # Only update if something has changed
            newData = getResourceDkanData(newResource, dataset['nid'], dataset['title'], oldData)

            #logging.debug("new resource object %s", newResource)
            #logging.debug("- new Data %s", newData)
            #logging.debug("- old Data %s", oldData)

            hasChanged = config.force_resource_update
            hasChanged = hasChanged or (newData['title'] != oldData['title'])

            (oldResourceUrl, oldResourceType) = Resource.extractUrlFromResourceData(oldData)
            (newResourceUrl, newResourceType) = Resource.extractUrlFromResourceData(newData)
            #logging.debug("oldResourceUrl %s %s", oldResourceType, oldResourceUrl)
            #logging.debug("newResourceUrl %s %s", newResourceType, newResourceUrl)
            hasChanged = hasChanged or (oldResourceType != newResourceType)
            hasChanged = hasChanged or (oldResourceUrl != newResourceUrl)

            oldBody1 = dkanhelpers.JsonHelper.get_nested_json_value(oldData, ['body', 'und', 0, 'safe_value'])
            oldBody2 = dkanhelpers.JsonHelper.get_nested_json_value(oldData, ['body', 'und', 0, 'value'])
            newBody = dkanhelpers.JsonHelper.get_nested_json_value(newData, ['body', 'und', 0, 'value'])
            bodyIsTheSame = (oldBody1 == newBody) or (oldBody2 == newBody)
            hasChanged = hasChanged or not bodyIsTheSame

            compareFields = [['field_dcatapde_licatt', 'value'], ["field_dcatapde_avail", "tid"], ["field_dcatapde_status", "tid"], ['field_dcatapde_license', "tid"],
                ['field_dcatapde_languagesingle', "tid"], ['field_dcatapde_rights', "url"], ['field_conforms_to', "url"]]
            for fieldSetting in compareFields:
                (field, compareValue) = fieldSetting
                oldVal = ''
                newVal = ''
                if field in oldData:
                    # oldVal = "{}".format(oldData[field]) if oldData[field] else ""
                    oldVal = dkanhelpers.JsonHelper.get_nested_json_value(oldData, [field, 'und', 0, compareValue])
                    oldVal = oldVal.replace("\r\n", "\n").replace("_x000D_", "").strip() if oldVal else ""
                if field in newData:
                    # newVal = "{}".format(newData[field]) if newData[field] else ""
                    newVal = dkanhelpers.JsonHelper.get_nested_json_value(newData, [field, 'und', 0, compareValue])
                    newVal = newVal.replace("\r\n", "\n").replace("_x000D_", "").strip() if newVal else ""
                #logging.debug(" - oldVal %s", oldVal)
                #logging.debug(" - newVal %s", newVal)
                fieldHasChanged = (oldVal != newVal)
                hasChanged = hasChanged or fieldHasChanged
                logging.debug(" -> FieldhasChanged '%s'? %s (all = %s)", field, fieldHasChanged, hasChanged)

            if hasChanged:
                logging.warn(_("  ..hat sich geändert."))
                updateResource(newData, oldData)
            else:
                logging.info(_(" '-> [nicht geändert]"))

        else:
            # This seems to be an old url that we dont want anymore => delete it
            logging.info(_("  '-> [löschen] %s"), oldData)
            op = api.node('delete', node_id=oldData['target_id'])
            logging.debug(_("Ergebnis: Status=%s, Text=%s"), op.status_code, op.text)

    # Create new resources
    for resource in newResources:
        createResource(resource, dataset['nid'], dataset['title'])
