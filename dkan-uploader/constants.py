import logging

class Resource:
    """ Resource """

    RESOURCE_ID = 'Resource-ID'
    NAME = 'Resource-Name'
    FORMAT = 'Format'
    DESCRIPTION = 'Description'
    URL = 'Externe Url'

    _row = {}

    def __init__(self, row):
        self._row = row

    @staticmethod
    def create(row):

        # Check if row contains a dataset
        count_non_empty_dataset_fields = 0
        for column in get_column_config_resource():
            if column in row and row[column]:
                count_non_empty_dataset_fields += 1
        logging.info(_("Gefundende Felder: %s"), count_non_empty_dataset_fields)
        if count_non_empty_dataset_fields < 2:
            return None

        # Check if mandatory fields are set
        if not Resource.NAME in row:
            logging.warning(_('PflichtFeld fehlt: %s'), Resource.NAME)
            return None

        return Resource(row)

    @staticmethod
    def verify():
        ''' Internal test: check if our Dataset class definition is correct '''
        logging.warning("hier ist noch nichts programmiert")

    def getValue(self, valueName):
        return self._row[valueName]

    def __repr__(self):
        return self._row[Resource.NAME]
    def __str__(self):
        return self._row[Resource.NAME]


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
                logging.debug("found col: %s", column)
                count_non_empty_dataset_fields += 1
        logging.info(_("Gefundende Datensatz-Felder: %s"), count_non_empty_dataset_fields)
        if count_non_empty_dataset_fields < 3:
            return None

        # Check if mandatory fields are set
        mandatory_fields = [
            Dataset.NAME,
            Dataset.TITLE
            ]
        for field in mandatory_fields:
            if not field in row:
                logging.warning(_('Datensatz-PflichtFeld fehlt: %s'), field)
                return None

        new_object = Dataset(row)
        return new_object

    @staticmethod
    def verify():
        ''' Internal test: check if our Dataset class definition is correct '''
        members = [getattr(Dataset, attr) for attr in dir(Dataset) if not callable(getattr(Dataset, attr)) and not attr.startswith("_")]
        known_columns = get_column_config_dataset()
        for member in members:
            if not member in known_columns:
                raise RuntimeError(_('Programmierfehler: Dataset-Objekt nutzt eine Spalte "{}" die es garnicht gibt.').format(member))
        for column in known_columns:
            if not column in members:
                raise RuntimeError(_("DKAN-Spalte {} fehlt in Dataset class definition.").format(column))


    def getValue(self, valueName):
        return self._row[valueName]

    def __str__(self):
        return self._row[Dataset.TITLE]



def get_column_config_dataset():
    """ This contains the default configuration of a row"""


    # Some FIELDS ARE MISSING IN "current_package_list_with_resources"
    # How to get them? We have to query:
    # 1. https://opendata.stadt-muenster.de/api/dataset/node.json?parameters[uuid]=29a3d573-98e1-412c-af0c-c356a07eff7b
    #    => to get the node id
    # 2. https://opendata.stadt-muenster.de/api/dataset/node/41334.json
    #    => to get the missing details..

    #   TODO: Der Testdatensatz - da wurden alle Felder mit Daten gefüllt, aber nur teilweise sinnvoll.
    #           "bevölkerungsindikatoren-soziales" - 3877be7b-5cc8-4d54-adfe-cca0f4368a13
    #                                            ^ den nachher wieder richtig einstellen!

    columns_config = {
        'Dataset-ID': "id",
        'Node-ID': ["nid"],
        'Dataset-Name': "name",
        'Titel': "title",
        'Author': "author",
        'Contact Name': ['field_contact_name', 'und', 0, 'value'],
        'Contact Email': "author_email",
        'Geographical Location': ['field_spatial_geographical_cover', 'und', 0, 'value'],
        'Geographical Coverage Area': ['field_spatial_geographical_cover', 'und', 0, 'wkt'],
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
        'Schlagworte': 'TAGS',
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


def get_column_config_resource():
    columns = {
        'Lfd-Nr': 'lfd-nr',
        'Resource-ID': 'id',
        'Resource-Name': 'name',
        'Format': 'format',
        'Externe Url': 'url',
        'Beschreibung': 'description',
        'Prüfung OK?': 'response_ok',
        'HTTP-Responsecode':'response_code'
    }

    return columns
