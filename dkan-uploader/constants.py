

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
    columns = {
        'Dataset-ID': "id",
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

    return columns


def get_column_config_resource():
    columns = {
        'Lfd-Nr': 'lfd-nr',
        'Resource-ID': 'id',
        'Resource-Name': 'name',
        'Format': 'format',
        'Externe Url': 'url',
        'Description': 'description',
        'Prüfung OK?': 'response_ok',
        'HTTP-Responsecode':'response_code'
    }

    return columns
