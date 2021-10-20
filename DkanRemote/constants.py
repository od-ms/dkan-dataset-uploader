import re
import os.path
import logging
from geomet import wkt
from . import dkanhelpers
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
    DESCRIPTION_FORMAT = 'Beschreibung-Format'
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


    def getUniqueId(self):
        if Resource.URL in self._row:
            uniqueId = self._row[Resource.URL]
        elif Resource.RESOURCE_ID in self._row:
            uniqueId = self._row[Resource.RESOURCE_ID]
        else:
            uniqueId = Resource.NAME
        return uniqueId


    def equals_existing_resource(self, resourceData):
        uniqueId = ''
        if ("und" in resourceData['field_link_api']) and (resourceData['field_link_api']['und'][0]['url']):
            uniqueId = resourceData['field_link_api']['und'][0]['url']
        elif ('und' in resourceData['field_link_remote_file']) and (resourceData['field_link_remote_file']['und'][0]['uri']):
            uniqueId = resourceData['field_link_remote_file']['und'][0]['uri']
        elif ('und' in resourceData['field_upload']) and (resourceData['field_upload']['und'][0]['filename']):
            uniqueId = resourceData['field_upload']['und'][0]['filename']

        if ('uuid' in resourceData) and (Resource.RESOURCE_ID in self._row):
            return self._row[Resource.RESOURCE_ID] == resourceData['uuid']
        elif uniqueId and (Resource.URL in self._row):
            return self._row[Resource.URL] == uniqueId
        elif ('title' in resourceData) and (Resource.NAME in self._row):
            return resourceData['title'] == self._row[Resource.NAME]
        else:
            logging.warning(' Ressourcen konnten nicht verglichen werden. Auch im DKAN vorhandene Ressourcen müssen mindestens den Titel ausgefüllt haben.')
            return False


    def getUploadFilePath(self):
        filename = self.getValue(Resource.URL)
        if re.search(r'(\b(https?|ftp):\/\/[-A-Z0-9+&@#\/%?=~_|!:,.;]*[-A-Z0-9+&@#\/%=~_|])', filename, re.IGNORECASE):
            return False
        file_path = os.path.join(config.download_dir, filename)
        if os.path.isfile(file_path) or os.path.islink(file_path):
            self.checkHasValidFileExtension(file_path)
            return file_path
        else:
            logging.error(_(" Achtung: URL sieht aus wie ein Dateiname, aber Datei existiert nicht:"))
            logging.error(" '%s' => %s", filename, file_path)
            return False


    def checkHasValidFileExtension(self, filename):
        match = re.search(r'\.([^.]+)$',filename)
        if match:
            file_extension = match.group(1).lower()
            valid_fileformats = dkanhelpers.HttpHelper.get_all_dkan_fileformats()
            if not file_extension in valid_fileformats:
                logging.warning(" Dateierweiterung '%s' ist in der DKAN-Instanz nicht registriert.", file_extension)
        else:
            logging.error(" Problem bei Ressource-Upload: %s", filename)
            logging.error(" Dateiname hat keine Dateierweiterung (z.B. '.csv').")


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

        # Validate text format field
        if Resource.DESCRIPTION_FORMAT in row:
            value = row[Resource.DESCRIPTION_FORMAT]
            possible = ["html", "bbcode", "plain_text", "full_html"]
            if value and (not value in possible):
                logging.error(_("Spalte '%s' hat unbekannten Wert '%s'. Ressource wird nicht korrekt angezeigt werden."), Resource.DESCRIPTION_FORMAT, value)
                logging.error(_("Erlaubte Werte: %s "), possible)

        logging.info(_(" Resource-Felder: %s/%s ('%s')"), count_non_empty_dataset_fields, len(get_column_config_resource()), row[Resource.NAME])
        return Resource(row)


    def set(self, field, value):
        self._row[field] = value


    def getValue(self, valueName):
        if (valueName == Resource.TYP) and (Resource.TYP not in self._row) and (Resource.TYP2 in self._row):
            return self._row[Resource.TYP2]
        return self._row[valueName] if valueName in self._row else ''


    def __repr__(self):
        return self._row[Resource.NAME]
    def __str__(self):
        return self._row[Resource.NAME]

    @staticmethod
    def verify():
        ''' Internal test: check if our class definition is correct '''
        members = [getattr(Resource, attr) for attr in dir(Resource) if not callable(getattr(Resource, attr)) and not attr.startswith("_")]

        known_columns = {**get_column_config_resource(True), **get_column_config_resource_detailed()}
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
    TAGS = 'Tags' # field_tags
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
    KEYWORDS = 'Schlagworte' # field_dataset_tags
    STATE = 'State'
    DATE_CREATED = 'Created'
    DATE_MODIFIED = 'Modified'
    DD_CONTRIBUTOR = 'DD Contributor'
    DD_CREATOR = 'DD Creator'
    DD_MAINTAINER = 'DD Maintainer'
    DD_ORIGINATOR = 'DD Originator'
    DD_PUBLISHER = 'DD Publisher'
    DD_GEONAMES = 'DD Geonames'
    DD_GEOCODE = 'DD Geocode'
    DD_GEOLEVEL = 'DD Geolevel'
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

        # Validate text format field
        if Dataset.TEXT_FORMAT in row:
            value = row[Dataset.TEXT_FORMAT]
            possible = ["html", "bbcode", "plain_text", "full_html"]
            if not value in possible:
                logging.error(_("Spalte '%s' hat unbekannten Wert '%s'. Datensatzbeschreibung wird nicht korrekt angezeigt werden."))
                logging.error(_("Erlaubte Werte: %s "), Dataset.TEXT_FORMAT, value, possible)

        # Validate temporal start
        if Dataset.TEMPORAL_START in row:
            value = str(row[Dataset.TEMPORAL_START])
            if value:
                match = re.search(r'^\d{4}-\d{2}-\d{2}', value)
                if not match:
                    logging.warning("Spalte 'Temporal Coverage Start' hat falsches Format: '%s'", value)
                    logging.warning("Stellen Sie bitte sicher, dass das Datum mit YYYY-MM-DD angegeben ist,")
                    logging.warning("und dass in ihrem Tabellenkalkulationsprogramm das Format des Feldes auf 'Text' gestellt ist.")
                    row[Dataset.TEMPORAL_START] = ''

        # Validate temporal end
        if Dataset.TEMPORAL_END in row:
            value = str(row[Dataset.TEMPORAL_END])
            if value:
                match = re.search(r'^\d{4}-\d{2}-\d{2}', value)
                if not match:
                    logging.warning("Spalte 'Temporal Coverage End' hat falsches Format: '%s'", value)
                    logging.warning("Stellen Sie bitte sicher, dass das Datum mit YYYY-MM-DD angegeben ist,")
                    logging.warning("und dass in ihrem Tabellenkalkulationsprogramm das Format des Feldes auf 'Text' gestellt ist.")
                    row[Dataset.TEMPORAL_END] = ''

        # Validate spatial
        if Dataset.GEO_AREA in row:
            try:
                ls_json = wkt.loads(row[Dataset.GEO_AREA])
                logging.debug(_("Geo-Daten: %s"), ls_json)
            except ValueError as err:
                logging.error("Geo-Daten Fehler: %s", repr(err))
                logging.warning("Geo-Coverage-Angabe wird ignoriert, da sie nicht WKT-kompatibel ist.")
                row[Dataset.GEO_AREA] = ''

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

        known_columns = get_column_config_dataset()
        column_key = known_columns[valueName]

        if (valueName == Dataset.TAGS) or (valueName == Dataset.KEYWORDS):
            tags = self.getRawValue(valueName)
            tags_in_dataset = re.findall(r'[“"]([^“"”]+)[”"]', tags)
            ids_in_dataset = re.findall(r'\((\d+)\)', tags)
            if tags_in_dataset:
                logging.debug(_("'%s': %s"), valueName, tags_in_dataset)
            if ids_in_dataset:
                logging.debug(_("'%s' IDs: %s"), valueName, ids_in_dataset)

            has_error = False
            if tags and not (tags_in_dataset or ids_in_dataset):
                has_error = True
                logging.error(_('Problem bei "%s". Wert wurde nicht erkannt: %s'), valueName, tags)

            if valueName == Dataset.KEYWORDS:
                all_tags_in_dkan = dkanhelpers.HttpHelper.get_all_dkan_tags()
            else:
                all_tags_in_dkan = dkanhelpers.HttpHelper.get_all_dkan_categories()

            # TODOs we completely ignore ids_in_dataset .. do we need that at all?
            has_error = False
            value = []
            for tag_name in tags_in_dataset:
                found = ''
                for tkey, tval in all_tags_in_dkan.items():
                    if tval.lower() == tag_name.lower():
                        found = tkey
                        logging.debug("%s gefunden: %s '%s'", valueName, tkey, tag_name)
                if not found:
                    logging.error("'%s' unbekannt: '%s' wird verworfen", valueName, tag_name)
                    has_error = True
                else:
                    value.append(found)
            if has_error:
                logging.error(_('Problem bei "%s". Mögliche Lösung:'), valueName)
                logging.error(_('a) Bitte schreiben Sie %s immer in Anführungszeichen, z.B.: "Statistik", "API"'), valueName)
                logging.error(_('b) Sie können nur %s verwenden, die im DKAN Administrationsbereich angelegt wurden.'), valueName)
                logging.error(_('Mögliche Werte für "%s" sind:'), valueName)
                logging.error(_('%s'), all_tags_in_dkan.values())
            logging.debug("Gefundene tags: %s", value)

        elif valueName == Dataset.GROUPS:
            tags = self.getRawValue(valueName)
            value = re.findall(r'"([^"]*)"\s+\((\d+)\)', tags)
            logging.debug(_("Gefundene Gruppen: %s"), value)

        elif column_key[:7] == "RELATED":
            tags = self.getRawValue(valueName)
            value = re.findall(r'"([^"]*)"\s+\(([^"]*)\)', tags)
            logging.debug(_("Einträge '%s' gefunden: %s"), valueName, value)

        else:
            value = self.getRawValue(valueName)

        return value if value else default

    def getTitleUrlAttributes(self, valueName):
        relatedcontent = self.getValue(valueName)
        column_config = get_column_config_dataset()
        field_name_raw = column_config[valueName]
        field_name = field_name_raw[8:]
        logging.debug(_("gTUA '%s' gefunden: %s"), valueName, field_name)

        related_list = []
        for related_entry in relatedcontent:
            related_list.append({
                "title": related_entry[0],
                "url": related_entry[1],
                "attributes": []
                })
        return field_name, related_list

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
        'Titel': "title",
        'Groups': 'COLLECT|groups.title',
        'Tags': 'CATEGORIES', # field_tags
        'Description': "notes",
        'Textformat': ["body", "und", 0, "format"],
        'Homepage URL': ['field_landing_page', 'und', 0, 'url'],
        'Dataset-Name': "name",
        'URL': "url",
        'Author': "author",
        'Contact Name': ['field_contact_name', 'und', 0, 'value'],
        'Contact Email': "author_email",
        'Geographical Location': ['field_spatial_geographical_cover', 'und', 0, 'value'],
        'Geographical Coverage Area': ['field_spatial', 'und', 0, 'wkt'],
        'License': "license_title",
        'Custom License': ['field_license', 'und', 0, 'value'],
        'Frequency': ['field_frequency', 'und', 0, 'value'], #example value: "R/P1Y" ?
        'Temporal Coverage Start': ['field_temporal_coverage', 'und', 0, 'value'],
        'Temporal Coverage End': ['field_temporal_coverage', 'und', 0, 'value2'],
        'Granularity': ["field_granularity", "und", 0, "value"],
        'Data Dictionary': ["field_data_dictionary", 'und', 0, 'value'],
        'Data Dictionary Type': ["field_data_dictionary_type", 'und', 0, 'value'],
        'Public Access Level': ["field_public_access_level", "und", 0, "value"],
        'Data Standard': ['field_conforms_to', "und", 0, "url"],
        'Language': ["field_language", 'und', 0, 'value'],
        'Related Content': 'RELATED|field_related_content',
        # [x] Additional Info => wird anders eingebunden
        # [x] Resources => wird anders eingebunden
        # [x] Playground => Ein paar Felder, die anscheinend nur für Köln relevant sind
        # [x] Harvest Source => verwenden wir nicht, habe ich in der Doku erklärt

        ##      Fields for dcat-ap.de      ##
        'DD Contributor': 'RELATED|field_dcatapde_contributor',
        'DD Creator': 'RELATED|field_dcatapde_creator',
        'DD Maintainer': 'RELATED|field_dcatapde_maintainer',
        'DD Originator': 'RELATED|field_dcatapde_originator',
        'DD Publisher': 'RELATED|field_dcatapde_publisher',
        'DD Geonames': 'RELATED|field_dcatapde_spatialgeonames',

        ##      Format: "TID_REF|$node_json_field_name|$taxonomy_name"
        'DD Geocode': 'TID_REF|field_dcatapde_geocode|dcat_geocoding',
        'DD Geolevel': 'TID_REF|field_dcatapde_geolevel|dcat_geocoding_level',

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
        'Modified': "metadata_modified",
        'Schlagworte': 'TAGS'  # field_dataset_tags
    }
    return columns_config


def get_column_config_resource_detailed():
    detailed_columns = {
        'Sticky': ['sticky'],               # 1 = "Oben in Listen", 0 = sonst
        'Kommentare-Status': ['comment'],   # 1 = Geschlossen, 2 = Öffnen
        'Veröffentlicht?': ['status'],      # 1 = Veröffentlicht,  0 = Nicht veröffentlicht
        'Startseite': ['promote'],          # 1 = "Auf der Startseite", 0 = sonst
        'Beschreibung-Format': ["body", "und", 0, "format"],
        'Resource-Typ-Detail': 'RTYPE_DETAILED',
    }
    return detailed_columns




def get_column_config_resource(get_all=False):
    """ All columns of DKAN resources in our excel file"""

    # TODO there are some more fields in the node json, do we need them?
    # e.g. https://opendata.stadt-muenster.de/api/dataset/node/41153.json
    # - field_datasetore_status
    # - field_format (numeric format-tid)
    # - more details about the resource type (  api, remote_file, upload, datastore )

    columns = {
        'Lfd-Nr': 'lfd-nr',     # specific for DKAN-Downloader
        'Resource-ID': 'id',    # this is ckan package_id (uuid), e.g. a07c5d85-ff34-4093-8613-76a86de7a7a9
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

    if config.detailed_resources and not get_all:
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
        "field_related_content": {"$ref": "#/definitions/dkan_structure_url_title_attributes"},
        "field_resources": {"$ref": "#/definitions/dkan_structure_target_ids"},
        "field_spatial": {"$ref": "#/definitions/dkan_structure_spatial"},
        "field_spatial_geographical_cover": {"$ref": "#/definitions/dkan_structure_single_value"},
        "field_tags": {"$ref": "#/definitions/dkan_structure_tids"},
        "field_temporal_coverage": {"$ref": "#/definitions/dkan_structure_single_value_or_null"},
        "og_group_ref": {"$ref": "#/definitions/dkan_structure_target_ids"},
        "field_landing_page": {"$ref": "#/definitions/dkan_structure"},
        "field_language": {"$ref": "#/definitions/dkan_structure_multi_value"},
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

        ###############################
        ##   fields for dcat-ap-de   ##
        ###############################
        "field_dcatapde_contributor": {"$ref": "#/definitions/dkan_structure_url_title_attributes"},
        "field_dcatapde_creator": {"$ref": "#/definitions/dkan_structure_url_title_attributes"},
        "field_dcatapde_geocode": {"$ref": "#/definitions/dkan_structure_tids"},
        # "field_dcatapde_geodesc": [],
        "field_dcatapde_geolevel": {"$ref": "#/definitions/dkan_structure_tids"},
        #"field_dcatapde_granularity": {"$ref": "#/definitions/dkan_structure_tids"},
        #"field_dcatapde_language": {"$ref": "#/definitions/dkan_structure_tids"},
        # "field_dcatapde_legalbase": [],
        "field_dcatapde_maintainer": {"$ref": "#/definitions/dkan_structure_url_title_attributes"},
        "field_dcatapde_originator": {"$ref": "#/definitions/dkan_structure_url_title_attributes"},
        # "field_dcatapde_otherid": [],
        # "field_dcatapde_provenance": [],
        "field_dcatapde_publisher": {"$ref": "#/definitions/dkan_structure_url_title_attributes"},
        # "field_dcatapde_qualityprocess": [],
        # "field_dcatapde_relation": [],
        # "field_dcatapde_sample": [],
        # "field_dcatapde_source": [],
        "field_dcatapde_spatialgeonames": {"$ref": "#/definitions/dkan_structure_url_title_attributes_optional"},
        #"field_dcatapde_spatialplace": {"$ref": "#/definitions/dkan_structure_tids"},
        # "field_dcatapde_temporal": [],
        #"field_dcatapde_theme": {"$ref": "#/definitions/dkan_structure_tids"}

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
        "dkan_structure_multi_value": {
            "anyOf": [
                {   "type": "object",
                    "properties": {
                        "und": {
                            "type": "array",
                            "minItems": 1,
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
        "dkan_structure_url_title_attributes": {
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
        "dkan_structure_url_title_attributes_optional": {
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
                                    "title": {"type": ["null", "string"]},
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
