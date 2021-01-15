import re
import logging
import hashlib
from . import config


class ResourceType:
    """ Werte für die Felder Resource-Typ & Resource-Typ-Detail """
    TYPE_URL = 'url'
    TYPE_UPLOAD = 'uploaded'
    TYPE_DATASTORE = 'datastore'
    TYPE_REMOTE_FILE = 'remote_file' # Dieser Wert ist nur im Feld "Resource.TYP2" bei "detaillierten Ressourcen" mit drin
                                     # (was zig mal mehr DKAN-requests erfordert)


class Resource:
    """ Resource """

    RESOURCE_ID = 'Resource-ID'
    NAME = 'Resource-Name'
    FORMAT = 'Format'
    DESCRIPTION = 'Beschreibung'
    URL = 'Resource-Url'
    TYP = 'Resource-Typ'

    # Detaillierte Ressourcenfelder
    STICKY = 'Sticky'               # 1 = "Oben in Listen", 0 = sonst
    COMMENTS = 'Kommentare-Status'  # 1 = Geschlossen, 2 = Öffnen
    PUBLISHED = 'Veröffentlicht?'   # 1 = Veröffentlicht,  0 = Nicht veröffentlicht
    FRONTPAGE = 'Startseite'        # 1 = "Auf der Startseite", 0 = sonst
    TYP2 = 'Resource-Typ-Detail'    # gleiches wie "TYP", nur hier wird zusätzlich ausgegeben, ob es sich um "remote_file" handelt,
                                    # (was zig mal mehr DKAN-requests erfordert)

    # we dont write these to DKAN, they are only in the Excel file:
    HTTP_CODE = 'HTTP-Responsecode'
    HTTP_OK = 'Prüfung OK?'
    LFD_NR = 'Lfd-Nr'

    _row = {}

    def __init__(self, row):
        self._row = row


    def getUploadFilename(self):
        return hashlib.md5(str(self._row[Resource.URL]).encode('utf-8')).hexdigest() + '.csv'

    def getUniqueId(self):
        return self._row[Resource.URL]


    @staticmethod
    def create(row):

        # Check if row contains a dataset
        count_non_empty_dataset_fields = 0
        for column in get_column_config_resource():
            if column in row and row[column]:
                logging.debug(" [r] %s", column)
                count_non_empty_dataset_fields += 1
            else:
                logging.debug("  -  %s", column)

        if count_non_empty_dataset_fields < 1:
            return None

        # Check if mandatory fields are set
        if not Resource.NAME in row:
            logging.warning(_(' Resource-Felder gefunden, aber Pflichtfeld fehlt: %s'), Resource.NAME)
            return None

        logging.info(_(" Resource-Felder: %s/%s ('%s')"), count_non_empty_dataset_fields, len(get_column_config_resource()), row[Resource.NAME])
        return Resource(row)


    def set(self, field, value):
        self._row[field] = value


    def getValue(self, valueName):
        return self._row[valueName]


    def __repr__(self):
        return self._row[Resource.NAME]
    def __str__(self):
        return self._row[Resource.NAME]

    @staticmethod
    def verify():
        ''' Internal test: check if our class definition is correct '''
        members = [getattr(Resource, attr) for attr in dir(Resource) if not callable(getattr(Resource, attr)) and not attr.startswith("_")]

        known_columns = {**get_column_config_resource(), **get_column_config_resource_detailed()}
        for member in members:
            if not member in known_columns:
                raise AbortProgramError(_('Programmfehler: Resource-Objekt nutzt eine Spalte "{}" die es garnicht gibt.').format(member))
        for column in known_columns:
            if not column in members:
                raise AbortProgramError(_("DKAN-Spalte {} fehlt in Dataset class definition.").format(column))


class Dataset:
    """ Dataset """

    DATASET_ID = 'Dataset-ID'
    NODE_ID = 'Node-ID'
    NAME = 'Dataset-Name'
    TITLE = 'Titel'
    AUTHOR = 'Author'
    CONTACT_NAME = 'Contact Name'
    CONTACT_EMAIL = 'Contact Email'
    GEO_LOCATION = 'Geographical Location'
    GEO_AREA = 'Geographical Coverage Area'
    LICENSE = 'License'
    LICENSE_CUSTOM = 'Custom License'
    HOMEPAGE = 'Homepage URL'
    DESCRIPTION = 'Description'
    TEXT_FORMAT = 'Textformat'
    URL = 'URL'
    TAGS = 'Tags'
    GROUPS = 'Groups'
    FREQUENCY = 'Frequency'
    TEMPORAL_START = 'Temporal Coverage Start'
    TEMPORAL_END = 'Temporal Coverage End'
    GRANULARITY = 'Granularity'
    DATA_DICT = 'Data Dictionary'
    DATA_DICT_TYPE = 'Data Dictionary Type'
    PUBLIC_ACCESS_LEVEL = 'Public Access Level'
    DATA_STANDARD = 'Data Standard'
    LANG = 'Language'
    RELATED_CONTENT = 'Related Content'
    KEYWORDS = 'Schlagworte'
    STATE = 'State'
    DATE_CREATED = 'Created'
    DATE_MODIFIED = 'Modified'

    _row = {}

    def __init__(self, row):
        self._row = row

    @staticmethod
    def create(row):

        # Check if row contains a dataset
        count_non_empty_dataset_fields = 0
        for column in get_column_config_dataset():
            if column in row and row[column]:
                logging.debug(" [x] %s", column)
                count_non_empty_dataset_fields += 1
            else:
                logging.debug("  -  %s", column)

        for field, value in row.items():
            if field[:6] == 'Extra-':
                logging.debug(" [.] Extra-Spalte '%s': '%s'", field[6:], value)

        if count_non_empty_dataset_fields < 3:
            return None

        # Check if mandatory fields are set
        mandatory_fields = [
            Dataset.NAME,
            Dataset.TITLE
            ]
        for field in mandatory_fields:
            if not field in row:
                logging.warning(_(' Datensatz gefunden, aber Spalte wird ignoriert weil Datensatz-Pflichtfeld fehlt: %s'), field)
                return None

        new_object = Dataset(row)
        logging.info(_(" Datensatz-Felder: %s/%s ('%s')"), count_non_empty_dataset_fields, len(get_column_config_dataset()), new_object.getValue(Dataset.TITLE))

        return new_object

    @staticmethod
    def verify():
        ''' Internal test: check if our Dataset class definition is correct '''
        members = [getattr(Dataset, attr) for attr in dir(Dataset) if not callable(getattr(Dataset, attr)) and not attr.startswith("_")]
        known_columns = get_column_config_dataset()
        for member in members:
            if not member in known_columns:
                raise AbortProgramError(_('Programmierfehler: Dataset-Objekt nutzt eine Spalte "{}" die es garnicht gibt.').format(member))
        for column in known_columns:
            if not column in members:
                raise AbortProgramError(_("DKAN-Spalte {} fehlt in Dataset class definition.").format(column))


    def getRawValue(self, valueName, default=""):

        value = None
        if valueName in self._row:
            value = self._row[valueName]
        return value if value else default


    def getExtraFields(self):
        extras = {}
        for field, value in self._row.items():
            if field[:6] == 'Extra-':
                extras[field[6:]] = value
        return extras


    def getValue(self, valueName, default=""):

        if (valueName == Dataset.TAGS) or (valueName == Dataset.KEYWORDS):
            tags = self.getRawValue(valueName)
            value = re.findall(r'"[^"]*"\s+\((\d+)\)', tags)
            logging.debug(_("ID '%s' gefunden: %s"), valueName, value)

        elif valueName == Dataset.GROUPS:
            tags = self.getRawValue(valueName)
            value = re.findall(r'"([^"]*)"\s+\((\d+)\)', tags)
            logging.debug(_("Gefundene Gruppen: %s"), value)

        elif valueName == Dataset.RELATED_CONTENT:
            tags = self.getRawValue(valueName)
            value = re.findall(r'"([^"]*)"\s+\(([^"]*)\)', tags)
            logging.debug(_("Einträge '%s' gefunden: %s"), valueName, value)

        else:
            value = self.getRawValue(valueName)

        return value if value else default



    def __str__(self):
        return '{} ({})'.format(
            self._row[Dataset.TITLE] if Dataset.TITLE in self._row else 'Ohne Titel',
            self._row[Dataset.DATASET_ID] if Dataset.DATASET_ID in self._row else 'Ohne ID')


class AbortProgramError(RuntimeError):
    """ We create an own Error to catch on top level // better control of program flow """

    def __init__(self, message):
        super(AbortProgramError, self).__init__(message)
        self.message = message



def get_column_config_dataset():
    """ This contains the default configuration of a row"""

    # How to get all..
    #  - GROUPS: https://dkan.stadt.de/api/dataset/node.json?parameters[type]=group
    #  - KEYWORDS/Schlagworte/field_dataset_tags:
    #       https://dkan.stadt.de/autocomplete_deluxe/taxonomy/field_dataset_tags/%20/500?term=&synonyms=2
    #           => Problem: Useless because no IDs are returned
    #       https://dkan.stadt.de/admin/structure/taxonomy/dataset_tags
    #           => Problem: You need to be logged in to DKAN admin interface, and the response is pure HTML..

    # Some FIELDS ARE MISSING IN "current_package_list_with_resources"
    # How to get them? We have to query:
    # 1. https://opendata.stadt.de/api/dataset/node.json?parameters[uuid]=29a3d573-98e1-412c-af0c-c356a07eff7b
    #    => to get the node id
    # 2. https://opendata.stadt.de/api/dataset/node/41334.json
    #    => to get the missing details..

    # API links
    # ckan: https://opendata.stadt.de/api/3/action/package_show?id=3877be7b-5cc8-4d54-adfe-cca0f4368a13
    # dkan: https://opendata.stadt.de/api/dataset/node/40878.json

    # This config describes how the fields will be written from DKAN api response to the excel file.
    #
    # The config works like this:
    # - key = column name in excel file
    # - value is a "string" => name of this field will be read from current_package_list_with_resources
    #                       @see
    # - value is a list => this key will be read from dkan node.json
    #                       @see https://opendata.stadt.de/api/dataset/node/41334.json
    # - vaule is uppercase => check the code in excelwriter.py

    columns_config = {
        'Dataset-ID': "id",
        'Node-ID': ["nid"],
        'Dataset-Name': "name",
        'Titel': "title",
        'Author': "author",
        'Contact Name': ['field_contact_name', 'und', 0, 'value'],
        'Contact Email': "author_email",
        'Geographical Location': ['field_spatial_geographical_cover', 'und', 0, 'value'],
        'Geographical Coverage Area': ['field_spatial', 'und', 0, 'wkt'],
        'License': "license_title",
        'Custom License': ['field_license', 'und', 0, 'value'],
        'Homepage URL': ['field_landing_page', 'und', 0, 'url'],
        'Description': "notes",
        'Textformat': ["body", "und", 0, "format"],
        'URL': "url",
        'Tags': 'CATEGORIES',
        'Groups': 'COLLECT|groups.title',
        'Frequency': ['field_frequency', 'und', 0, 'value'], #example value: "R/P1Y" ?
        'Temporal Coverage Start': ['field_temporal_coverage', 'und', 0, 'value'],
        'Temporal Coverage End': ['field_temporal_coverage', 'und', 0, 'value2'],
        'Granularity': ["field_granularity", "und", 0, "value"],
        'Data Dictionary': ["field_data_dictionary", 'und', 0, 'value'],
        'Data Dictionary Type': ["field_data_dictionary_type", 'und', 0, 'value'],
        'Public Access Level': ["field_public_access_level", "und", 0, "value"],
        'Data Standard': ['field_conforms_to', "und", 0, "url"],
        'Language': ["field_language", 'und', 0, 'value'],
        'Related Content': 'RELATED',
        # [x] Additional Info => wird anders eingebunden
        # [x] Resources => wird anders eingebunden
        'Schlagworte': 'TAGS',  # field_dataset_tags
        # [x] Playground => Ein paar Felder, die anscheinend nur für Köln relevant sind
        # [x] Harvest Source => verwenden wir nicht, habe ich in der Doku erklärt

        # Versionsinformationen ?
        # Einstellungen für Kommentare (Öffnen / Geschlossen)
        # Informationen zum Autor
            # Erstellt von
            # geschrieben am
        # Veröffentlichungseinstellungen
            # Veröffentlicht
            # Auf der Startseite
            # Oben in Listen
        'State': "state",
        'Created': "metadata_created",
        'Modified': "metadata_modified"
    }
    return columns_config


def get_column_config_resource_detailed():
    detailed_columns = {
        'Sticky': ['sticky'],               # 1 = "Oben in Listen", 0 = sonst
        'Kommentare-Status': ['comment'],   # 1 = Geschlossen, 2 = Öffnen
        'Veröffentlicht?': ['status'],      # 1 = Veröffentlicht,  0 = Nicht veröffentlicht
        'Startseite': ['promote'],          # 1 = "Auf der Startseite", 0 = sonst
        'Resource-Typ-Detail': 'RTYPE_DETAILED',
    }
    return detailed_columns




def get_column_config_resource():
    """ All columns of DKAN resources in our excel file"""

    # TODO there are some more fields in the node json, do we need them?
    # e.g. https://opendata.stadt-muenster.de/api/dataset/node/41153.json
    # - field_datasetore_status
    # - field_format (numeric format-tid)
    # - more details about the resource type (  api, remote_file, upload, datastore )

    columns = {
        'Lfd-Nr': 'lfd-nr', # specific for DKAN-Downloader
        'Resource-ID': 'id',
        'Resource-Name': 'name',
        'Format': 'format',
        'Resource-Typ': 'RTYPE',
        'Resource-Url': 'url',
        'Beschreibung': 'description',
        'Prüfung OK?': 'response_ok',       # specific for DKAN-Downloader
        'HTTP-Responsecode':'response_code', # specific for DKAN-Downloader

    #       field_link_api	[]
    #       field_link_remote_file	[]
    #       field_upload
    #       field_datastore_status

    #       "URL-Alias-Einstellungen" => finden sich NICHT im API response der ressource wieder
    }

    if config.detailed_resources:
        del columns['Resource-Typ']

    return columns


# JSON Schema of the dataset entries in endpoint "current_package_list_with_resources"
datasetSchema = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "name": {"type": "string"},
        "title": {"type": "string"},
        "author": {"type": "string"},
        "author_email": {"type": "string"}, # = "contact email"
        "maintainer": {"type": "string"},           # useless
        "maintainer_email": {"type": "string"},     # useless
        "license_title": {"type": "string"},
        "notes": {"type": "string"},        # = "description"
        "url": {"type": "string"},
        "state": {"type": "string"},
        "log_message": {"type": "string"},          # ??
        "private": {"type": "boolean"},             # ??
        "revision_timestamp": {"type": "string"},
        "metadata_created": {"type": "string"},
        "metadata_modified": {"type": "string"},
        "creator_user_id": {"type": "string"},
        "type": {"type": "string"},                 # always "Dataset"
        "resources": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "revision_id": {"type": "string"},
                    "url": {"type": "string"},
                    "description": {"type": "string"},
                    "format": {"type": "string"},
                    "state": {"type": "string"},
                    "revision_timestamp": {"type": "string"},
                    "name": {"type": "string"},
                    "mimetype": {"type": "string"},
                    "size": {"type": "string"},
                    "created": {"type": "string"},
                    "resource_group_id": {"type": "string"},
                    "last_modified": {"type": "string"},
                    # these are added by the check-script (excelwriter.py)
                    "response_ok": {"type": "string"},
                    "response_code": {"type": "string"}
                },
                "required": [ "id", "revision_id", "name", "url" ]
            }
        },
        "tags": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "vocabulary_id": {"type": "string"},
                    "name": {"type": "string"}
                },
                "required": [ "id", "vocabulary_id", "name" ]
            }
        },
        "groups": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "title": {"type": "string"}, # this is the value that we want
                    "description": {"type": "string"},
                    "name": {"type": "string"}
                },
                "required": [ "name", "title", "id" ]
            }
        },
        "extras": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "key": {"type": "string"},
                    "value": {"type": "string"},
                },
                "required": [ "key", "value" ]
            }
        }
    },
    "required": [ "id", "name", "metadata_created", "type" ]
}

# JSON Schema for DKAN nodes
#   = response of dkan-api-endpoint "/api/dataset/node/{}.json" (config.api_get_node_details)
nodeSchema = {
    "type": "object",
    "properties": {
        "vid": {"type": "string"},
        "uid": {"type": "string"},
        "title": {"type": "string"},
        "status": {"type": "string"},
        "comment": {"type": "string"},
        "promote": {"type": "string"},
        "sticky": {"type": "string"},
        "vuuid": {"type": "string"},
        "nid": {"type": "string"},
        "type": {"type": "string"},
        "language": {"type": "string"},
        "created": {"type": "string"},
        "tnid": {"type": "string"},
        "translate": {"type": "string"},
        "uuid": {"type": "string"},
        "revision_timestamp": {"type": "string"},
        "revision_uid": {"type": "string"},
        "body": {"$ref": "#/definitions/dkan_structure_single_value"},
        "field_additional_info": {"$ref": "#/definitions/dkan_structure_additional_info"},
        "field_contact_email": {"$ref": "#/definitions/dkan_structure"},
        "field_contact_name": {"$ref": "#/definitions/dkan_structure"},
        "field_data_dictionary": {"$ref": "#/definitions/dkan_structure"},
        "field_frequency":  {"$ref": "#/definitions/dkan_structure_single_value"},
        "field_granularity": {"$ref": "#/definitions/dkan_structure_single_value"},
        "field_license": {"$ref": "#/definitions/dkan_structure_single_value"},
        "field_public_access_level": {"$ref": "#/definitions/dkan_structure_single_value"},
        "field_related_content": {"$ref": "#/definitions/dkan_structure_related_content"},
        "field_resources": {"$ref": "#/definitions/dkan_structure_target_ids"},
        "field_spatial": {"$ref": "#/definitions/dkan_structure_spatial"},
        "field_spatial_geographical_cover": {"$ref": "#/definitions/dkan_structure_single_value"},
        "field_tags": {"$ref": "#/definitions/dkan_structure_tids"},
        "field_temporal_coverage": {"$ref": "#/definitions/dkan_structure_single_value_or_null"},
        "og_group_ref": {"$ref": "#/definitions/dkan_structure_target_ids"},
        "field_landing_page": {"$ref": "#/definitions/dkan_structure"},
        "field_language": {"$ref": "#/definitions/dkan_structure_single_value"},
        "field_pod_theme": {"type": "array"},
        "field_rights": {"type": "array"},
        "field_playground": {"$ref": "#/definitions/dkan_structure"},
        "field_dataset_tags": {"$ref": "#/definitions/dkan_structure_tids"},
        "path": {"type": "string"},
        "cid": {"type": ["number", "string"]},
        "last_comment_timestamp": {"type": "string"},
        "last_comment_name": {"type": ["null", "string"]},
        "last_comment_uid": {"type": "string"},
        "comment_count": {"type": ["number", "string"]},
        "name": {"type": "string"},
        "picture": {"type": "string"},
        "data": {"type": ["null", "string"]},
    },
    "required": [ "vid", "uid", "title", "status", "comment", "promote", "sticky",
        "vuuid", "nid", "type", "language", "created", "changed", "tnid", "translate",
        "uuid", "revision_timestamp", "revision_uid", "body", "field_additional_info",
        "field_contact_email", "field_contact_name", "field_data_dictionary", "field_frequency",
        "og_group_ref", "field_landing_page", "field_language", "field_tags", "field_dataset_tags"
        ],
    "definitions": {
        "dkan_structure": {
            "anyOf": [
                {   "type": "object",
                    "properties": {
                        "und": {
                            "type": "array",
                            "minItems": 1
                        }
                    }
                },
                {   "type": "array",
                    "maxItems": 0
                }
            ]
        },
        "dkan_structure_single_value": {
            "anyOf": [
                {   "type": "object",
                    "properties": {
                        "und": {
                            "type": "array",
                            "minItems": 1,
                            "maxItems": 1,
                            "items": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "string"}
                                },
                                "required": ["value"]
                            }
                        }
                    }
                },
                {   "type": "array",
                    "maxItems": 0
                }
            ]
        },
        "dkan_structure_single_value_or_null": {
            "anyOf": [
                {   "type": "object",
                    "properties": {
                        "und": {
                            "type": "array",
                            "minItems": 1,
                            "maxItems": 1,
                            "items": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": ["null", "string"]}
                                },
                                "required": ["value"]
                            }
                        }
                    }
                },
                {   "type": "array",
                    "maxItems": 0
                }
            ]
        },
        "dkan_structure_related_content": {
            "anyOf": [
                {   "type": "object",
                    "properties": {
                        "und": {
                            "type": "array",
                            "minItems": 1,
                            "items": {
                                "type": "object",
                                "properties": {
                                    "url": {"type": "string"},
                                    "title": {"type": "string"},
                                    "attributes": {"type": "array"}
                                },
                                "required": ["url", "title"]
                            }
                        }
                    }
                },
                {   "type": "array",
                    "maxItems": 0
                }
            ]
        },
        "dkan_structure_tids": {
            "anyOf": [
                {   "type": "object",
                    "properties": {
                        "und": {
                            "type": "array",
                            "minItems": 1,
                            "items": {
                                "type": "object",
                                "properties": {
                                    "tid": {"type": "string"}
                                },
                                "required": ["tid"]
                            }
                        }
                    }
                },
                {   "type": "array",
                    "maxItems": 0
                }
            ]
        },
        "dkan_structure_target_ids": {
            "anyOf": [
                {   "type": "object",
                    "properties": {
                        "und": {
                            "type": "array",
                            "minItems": 1,
                            "items": {
                                "type": "object",
                                "properties": {
                                    "target_id": {"type": "string"}
                                },
                                "required": ["target_id"]
                            }
                        }
                    }
                },
                {   "type": "array",
                    "maxItems": 0
                }
            ]
        },
        "dkan_structure_additional_info": {
            "anyOf": [
                {   "type": "object",
                    "properties": {
                        "und": {
                            "type": "array",
                            "minItems": 1,
                            "items": {
                                "type": "object",
                                "properties": {
                                    "first": {"type": "string"},
                                    "second": {"type": "string"}
                                },
                                "required": ["first", "second"]
                            }
                        }
                    }
                },
                {   "type": "array",
                    "maxItems": 0
                }
            ]
        },
        "dkan_structure_spatial": {
            "anyOf": [
                {   "type": "object",
                    "properties": {
                        "und": {
                            "type": "array",
                            "minItems": 1,
                            "maxItems": 1,
                            "items": {
                                "type": "object",
                                "properties": {
                                    "wkt": {"type": "string"},
                                    "geo_type": {"type": "string"},
                                    "lat": {"type": "string"},
                                    "lon": {"type": "string"},
                                    "left": {"type": "string"},
                                    "top": {"type": "string"},
                                    "right": {"type": "string"},
                                    "bottom": {"type": "string"},

                                },
                                "required": ["wkt", "geo_type"]
                            }
                        }
                    }
                },
                {   "type": "array",
                    "maxItems": 0
                }
            ]
        }
    }
}



# DKAN data.json file format:
# ---------------------------
#                   ( wget https://dkan-url/data.json )
"""
 'dataset': [{'@type': 'dcat:Dataset',
    'accessLevel': 'public',
    'contactPoint': {'fn': 'Open Data Koordination',
                    'hasEmail': '...'},
    'description': 'Am 30. Januar 2020 wurde die neue '
                    'beschlossen. Das Wahlgebiet "Stadt Münster" für '
    'distribution': [{'@type': 'dcat:Distribution',
                    'accessURL': '...',
                    'description': 'In dieser PDF-Datei ist die '
                                    'Änderung der '
                                    '2020 visuell dargestellt.',
                    'format': 'pdf',
                    'title': 'Übersicht der geänderten '
                                'Wahlbezirke'},
                    {'@type': 'dcat:Distribution',
                    'accessURL': '...',
                    'description': 'In dieser Shape-Datei sind die '
                                    'aktuellen Kommunalwahlbezirke '
                                    'verfügbar.',
                    'format': 'shape',
                    'title': 'Aktuelle Kommunalwahlbezirke 2020'}],
    'identifier': '0e5931cf-9e8f-4ff0-afe3-54798a39d1bb',
    'issued': '2020-08-25',
    'keyword': ['Politik und Wahlen'],
    'landingPage': '....',
    'license': 'https://www.govdata.de/dl-de/by-2-0',
    'modified': '2020-08-25',
    'publisher': {'@type': 'org:Organization',
                'name': 'Stadt '},
    'spatial': 'POLYGON ((7.5290679931641 51.89293553285, '
                '52.007625513725, 7.7350616455078 51.89293553285))',
    'title': 'Änderungen der Wahlbezirke zur Kommunalwahl  '
            '2020'},
"""
