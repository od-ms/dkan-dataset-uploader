#! /usr/bin/python

import os
import re
import sys
import json
import logging
import hashlib
import traceback
from jsonschema import validate
from jsonschema.exceptions import ValidationError
import xlrd
import xlsxwriter
import httplib2
from . import config
from . import constants
from . import dkanhelpers
from . import dkanhandler
from .constants import AbortProgramError

class ExcelResultFile:
    """ Handle creation of Excel content """

    # startup values
    filename = ''
    extra_columns = {}

    # runtime config
    workbook = ''
    worksheet = ''
    bold = None
    small_font = None
    current_row = 0
    current_dataset_nr = 0
    existing_dataset_ids = {}
    dataset_tag_names=  {}
    column_mapping = []

    def __init__(self, filename, extra_columns):
        self.filename = filename
        self.extra_columns = extra_columns
        self.current_row = 0

    def initialize_new_excel_file_with_existing_content(self):
        """ Read the extisting excel and save ALL content to "old_excel_content",
            so we can then write it to a "new" file (=to continue from where we left off)
            Also return all dataset_ids as dict, so we can skip them
        """
        logging.info(_("Öffne Excel-Datei: %s"), self.filename)
        loc = (self.filename)
        self.existing_dataset_ids = {}
        old_excel_content = []

        try:
            wb = xlrd.open_workbook(loc)
            sheet = wb.sheet_by_index(0)
            self.column_mapping = []

            # check if columns of excel file are same as our config
            all_dkan_rows = self.get_column_config()
            for i in range(sheet.ncols):
                column_header = sheet.cell_value(0, i)
                self.column_mapping.append(column_header)
                if column_header not in all_dkan_rows:
                    logging.warning(_("Unbekannte Spalte wird ignoriert: {}").format(column_header))
                else:
                    all_dkan_rows.remove(column_header)

            if all_dkan_rows:
                logging.error(_("Fehler #6000: Es wurde mindestens ein DKAN-Feld bzw. eine benötigte Spalte nicht in der Excel-Datei gefunden."))
                logging.error(_("Fehlende Spalten in der Excel-Datei:"))
                logging.error(_("%s"), all_dkan_rows)
                raise AbortProgramError(_("Fügen Sie bitte die fehlenden(n) Spalte(n) zur Excel-Datei hinzu (s.o.). "))

            for j in range(1, sheet.nrows):
                excelrow = []
                for i in range(sheet.ncols):
                    excelrow.append(sheet.cell_value(j, i))

                old_excel_content.append(excelrow)

                # save all package_data ids for later use (=lookup of existing ids)
                index_of_dataset_id = self.column_mapping.index(constants.Dataset.DATASET_ID)
                dataset_id = excelrow[index_of_dataset_id]
                if dataset_id:
                    self.existing_dataset_ids[dataset_id] = True

            self.initialize_new_excel_file(True)

        except FileNotFoundError:
            logging.info(_("Excel-Datei existiert noch nicht und wird erstellt."))
            self.column_mapping = self.get_column_config()
            self.initialize_new_excel_file(False)

        for row in old_excel_content:
            self.add_plain_row(row)

        self.current_dataset_nr = len(self.existing_dataset_ids)


    def get_existing_dataset_ids(self):
        logging.debug(_("Existierende IDs: %s"), self.existing_dataset_ids)
        return self.existing_dataset_ids


    def initialize_new_excel_file(self, is_existing_excel_file):
        if is_existing_excel_file:
            first_row = self.get_column_config()
        else:
            first_row = self.column_mapping

        # Init workbook objects
        self.workbook = xlsxwriter.Workbook(self.filename)
        self.worksheet = self.workbook.add_worksheet()
        self.bold = self.workbook.add_format({'bold': True})
        self.small_font = self.workbook.add_format({'font_size': 8})

        # Set column widths
        self.worksheet.set_column('A:A', 15)
        self.worksheet.set_column('C:C', 20)
        self.worksheet.set_column(first_col=0, last_col=0, cell_format=self.small_font)

        # Add group ("level: 1") to some columns so that they are "einklappbar"
        self.worksheet.set_column('D:E', 16, None, {'level': 1})            # Tags, Groups
        self.worksheet.set_column('F:F', 30, self.small_font, {'level': 1}) # Description
        self.worksheet.set_column('G:G', 10, None, {'level': 1})            # Text_format

        # Homepage bekommt kein Level weil das ist der Gruppen-Trenner
        # (zwischen zwei Gruppen muss immer ein Feld sein, das keine Gruppe hat)
        self.worksheet.set_column('H:H', 20, self.small_font)               # Homepage

        # Große Gruppe mit den diversen sonstigen Feldern
        self.worksheet.set_column('J:AD', None, None, {'level': 1})
        self.set_extra_columns_group(first_row)

        # write header row
        self.worksheet.write_row('A1', first_row, self.bold)


    def set_extra_columns_group(self, first_row):
        ''' find "extra"-columns start & end to make them retractable in the excel '''
        extra_start = 0
        extra_end = 0
        column_nr = 0
        for column_title in first_row:
            if column_title[:6] == 'Extra-':
                if not extra_start:
                    extra_start = column_nr
            elif extra_start and not extra_end:
                extra_end = column_nr
            column_nr += 1
        if extra_start: # adjust group end
            if not extra_end:
                extra_end = len(first_row)-1
            elif extra_end and (extra_end > extra_start+1):
                extra_end -= 1
            elif extra_end and (extra_end <= extra_start+1):
                extra_end = 0 # dont create group if only 1 extra
        if extra_start and extra_end:
            self.worksheet.set_column(extra_start, extra_end, None, None, {'level': 1})


    def get_column_config(self):
        columns = list(self.get_column_config_dataset().keys())
        if not config.skip_resources:
            columns.extend(constants.get_column_config_resource().keys())
        if config.detailed_resources:
            columns.extend(constants.get_column_config_resource_detailed().keys())
        return columns


    def add_plain_row(self, column_contents):
        logging.debug(_("Zeileninhalt: %s"), column_contents)
        self.current_row += 1
        self.worksheet.write_row(self.current_row, 0, column_contents)


    def get_nested_json_value(self, target_dict, keys):
        node_value = None
        try:
            if len(keys) == 4:
                node_value = target_dict[keys[0]][keys[1]][keys[2]][keys[3]]
            elif len(keys) == 3:
                node_value = target_dict[keys[0]][keys[1]][keys[2]]
            elif len(keys) == 1:
                node_value = target_dict[keys[0]]
            else:
                raise Exception("get_nested_json_value() not implemented for {} keys in: {}".format(len(keys), keys))


        except (TypeError, KeyError, IndexError):
            if not (len(keys)>2 and isinstance(keys[2], int) and keys[2]>0):
                logging.debug(_(" [ ] %s"), keys[0])

        return node_value


    def get_column_config_dataset(self):
        """ This contains the default configuration of a row"""

        # Some FIELDS ARE MISSING IN "current_package_list_with_resources"
        # How to get them? We have to query:
        # 1. https://opendata.stadt-muenster.de/api/package_data/node.json?parameters[uuid]=29a3d573-98e1-412c-af0c-c356a07eff7b
        #    => to get the node id
        # 2. https://opendata.stadt-muenster.de/api/package_data/node/41334.json
        #    => to get the missing details..

        columns = constants.get_column_config_dataset()

        for col in self.extra_columns:
            columns["Extra-" + col] = "EXTRA|" + col

        return columns


    def get_column_config_resource(self):
        return constants.get_column_config_resource()


    def get_dataset_tag_name(self, t_id):
        ''' Helper function that returns a dataset_tag name for a ID, with data fetching & caching '''
        if not self.dataset_tag_names:
            self.dataset_tag_names = dkanhelpers.HttpHelper.get_all_dkan_tags()

        if t_id in self.dataset_tag_names:
            return self.dataset_tag_names[t_id]

        return '?'


    def convert_dkan_data_to_excel_row_hash(self, package_data, dkan_node, skip_resources):
        #logging.debug("package_data %s", package_data)
        #logging.debug("dkan_node %s", dkan_node)

        # get the config of which excel columns are mapped to which dkan json keys
        columns = {}
        for column_name, column_key in self.get_column_config_dataset().items():
            value = None
            if isinstance(column_key, list):
                value = self.get_nested_json_value(dkan_node, column_key)
            elif (column_key[:6] == "EXTRA|") and ("extras" in package_data):
                extra_key = column_key[6:]
                #logging.debug("searching extra key %s", extra_key)
                extra_obj = [x for x in package_data["extras"] if x["key"] == extra_key]
                value = extra_obj[0]["value"] if extra_obj else None

            elif column_key[:8] == "COLLECT|":
                extra_key = column_key[8:]
                if 'groups' in package_data:
                    groups = []
                    t_index = 0
                    for group in package_data['groups']: # luckily groups are in same order in both api endpoints
                        g_id = self.get_nested_json_value(dkan_node, ["og_group_ref", 'und', t_index, 'target_id'])
                        groups.append('"{}" ({})'.format(group['title'].replace('"', "'"), g_id))
                        t_index += 1
                    value = ", ".join(groups)

            elif column_key[:7] == "RELATED":
                related_content = []
                active_field = column_key[8:]
                logging.debug("     RELATED: %s => %s", column_key, active_field)
                for t_index in range(0,10):
                    rel = self.get_nested_json_value(dkan_node, [active_field, 'und', t_index])
                    if rel:
                        related_content.append('"{}" ({})'.format(rel['title'].replace('"', "'"), rel['url']))
                    value = ", ".join(related_content)

            elif column_key[:10] == "CATEGORIES":
                if 'tags' in package_data:
                    c_index = 0
                    categories = []
                    # read category name from ckan_data and read category id from dkan_node, they are in same order
                    for category in package_data['tags']:
                        c_id = self.get_nested_json_value(dkan_node, ["field_tags", 'und', c_index, 'tid'])
                        categories.append('"{}" ({})'.format(category['name'].replace('"', "'"), c_id))
                        c_index += 1
                    value = ", ".join(categories)

            elif column_key[:4] == "TAGS":
                # Because of weird DKAN api, we can only get the tag ID, but not the tag name ...
                tags = []
                for t_index in range(0,10):
                    t_id = self.get_nested_json_value(dkan_node, ["field_dataset_tags", 'und', t_index, 'tid'])
                    if t_id:
                        t_name = self.get_dataset_tag_name(t_id)
                        tags.append('"{}" ({})'.format(t_name, t_id))
                    value = ", ".join(tags)

            else:
                if column_key in package_data:
                    value = package_data[column_key]
                    logging.debug(" [x] %s => %s", column_key, value)
                else:
                    value = None

            columns[column_name] = value

        # write package_data row without resources
        if (skip_resources) or ('resources' not in package_data):
            return [columns]

        # write resource rows
        else:
            all_the_rows = []
            for resource_number, resource in enumerate(package_data['resources']):
                resource_package_id = resource['id']
                resource_row = {}
                lfd_nr = '{0:03d}'.format(self.current_dataset_nr) + '-' + '{0:02d}'.format(resource_number+1)

                if (config.resources_download) and ("url" in resource):
                    dkanhelpers.HttpHelper.download_resource(resource['url'], lfd_nr)

                # get all resource fields according to resource column config
                for column_name, rc_key in constants.get_column_config_resource().items():
                    rc_value = ""
                    if rc_key == 'lfd-nr':
                        rc_value = lfd_nr

                    elif rc_key == 'RTYPE':
                        rc_value = constants.ResourceType.TYPE_URL
                        url_keyname = constants.get_column_config_resource()[constants.Resource.URL]
                        if isinstance(url_keyname, list):
                            raise AbortProgramError(_('Unerwarteter Knotentyp "Liste".'))
                        if url_keyname in resource:
                            if resource[url_keyname].find(config.x_uploaded_resource_path) != -1:
                                rc_value = constants.ResourceType.TYPE_UPLOAD
                            elif resource[url_keyname].find(config.x_uploaded_datastore_path) != -1:
                                rc_value = constants.ResourceType.TYPE_DATASTORE

                    else:
                        try:
                            rc_value = resource[rc_key]
                        except KeyError:
                            logging.error(_('Resource Key "%s" nicht gefunden: %s'), rc_key, resource)

                    resource_row[column_name] = rc_value

                if config.detailed_resources:
                    resource_node_id = DkanApiAccess.get_node_id_for_package_id(resource_package_id)
                    resource_node = dkanhelpers.HttpHelper.read_dkan_node(resource_node_id)
                    for column_name, rc_key in constants.get_column_config_resource_detailed().items():
                        rc_value = ""
                        if isinstance(rc_key, list):
                            rc_value = self.get_nested_json_value(resource_node, rc_key)
                        elif rc_key == 'RTYPE_DETAILED':
                            if self.get_nested_json_value(resource_node, ["field_link_api", 'und', 0, 'url']):
                                rc_value = constants.ResourceType.TYPE_URL
                            elif self.get_nested_json_value(resource_node, ["field_link_remote_file", 'und', 0, 'uri']):
                                rc_value = constants.ResourceType.TYPE_REMOTE_FILE
                            elif self.get_nested_json_value(resource_node, ["field_upload", 'und', 0, 'filename']):
                                rc_value = constants.ResourceType.TYPE_UPLOAD
                            elif self.get_nested_json_value(resource_node, ["field_datastore_status", 'und', 0, 'filename']):
                                rc_value = constants.ResourceType.TYPE_DATASTORE
                        else:
                            try:
                                rc_value = resource_node[rc_key]
                            except KeyError:
                                logging.error(_('Detailled Key "%s" nicht gefunden: %s'), rc_key, resource)

                        resource_row[column_name] = rc_value


                logging.debug(_(
                    "Ressource %s: %s %s"),
                    resource_row[constants.Resource.TYP] if constants.Resource.TYP in resource_row else resource_row[constants.Resource.TYP2],
                    resource_row[constants.Resource.FORMAT],
                    resource_row[constants.Resource.NAME])

                if resource_number == 0:    # first row also has the dataset_fields
                    resource_row = {**columns, **resource_row}

                all_the_rows.append(resource_row)

            return all_the_rows


    def add_dataset(self, package_data, dkan_node):
        self.current_dataset_nr += 1
        rows = self.convert_dkan_data_to_excel_row_hash(package_data, dkan_node, config.skip_resources)
        if rows:
            row = rows[0]
            logging.info(
                _('Datensatz %s hinzufügen: "%s"'),
                self.current_dataset_nr,
                row[constants.Dataset.TITLE] if constants.Dataset.TITLE in row else 'Kein Titel')

        for row in rows:
            excel_row = []
            for key in self.column_mapping:
                excel_row.append(row[key] if key in row else '')

            self.add_plain_row(excel_row)


    def finish(self):
        self.workbook.close()


class DkanApiAccess:
    """Check status of a resource"""

    @staticmethod
    def get_node_id_for_package_id(package_id):
        node_search = dkanhelpers.HttpHelper.read_remote_json_with_cache(config.x_api_find_node_id.format(package_id), '{}.json'.format(package_id))
        if node_search[0]['nid']:
            return node_search[0]['nid']
        return None


    def get_resource_http_status(self, url):
        try:
            htl = httplib2.Http(".cache", disable_ssl_certificate_validation=True)
            resp = htl.request(url, 'HEAD')
        except:
            e = sys.exc_info()
            logging.exception("Error during resource load")
            return (False, str(e[0]) + " " + str(e[1]))

        return (int(resp[0]['status']) < 400), resp[0]['status']


    def validateJson(self, jsonData, check_schema):
        try:
            validate(instance=jsonData, schema=check_schema)
        except ValidationError as err:
            logging.error("Fehler #5002: Ungültiges JSON Format: %s in %s / %s", err.message, err.schema_path, err.absolute_schema_path)
            return False
        return True


    def readDatasetNodeJson(self, package_id, node_id):
        if not (node_id or package_id):
            raise AbortProgramError(_('Node-ID oder Package-ID muss angegeben werden.').format(package_id))

        node_data = None

        if not node_id:
            node_id = DkanApiAccess.get_node_id_for_package_id(package_id)

        if not node_id:
            raise AbortProgramError(_('Node-ID zu Package-ID {} fehlt oder konnte nicht gefunden werden.').format(package_id))

        node_data = dkanhelpers.HttpHelper.read_dkan_node(node_id)
        isValid = self.validateJson(node_data, constants.nodeSchema)
        if not isValid:
            print(json.dumps(node_data, indent=2))
            raise ValueError('Dataset format is not valid. Scroll up, see detailed error above')

        return node_data


    def read_remote_json_with_cache(self, remote_url, temp_file):
        return dkanhelpers.HttpHelper.read_remote_json_with_cache(remote_url, temp_file)


    def add_extras_from_package(self, extras, package_data):
        if "extras" in package_data:
            for extra in package_data["extras"]:
                keyName = extra["key"]
                if keyName in extras:
                    extras[keyName] = extras[keyName] + 1
                else:
                    extras[keyName] = 0


    def read_single_package(self, package_id):
        result = self.read_remote_json_with_cache(
            config.api_package_details + package_id,
            'package_details_{}.json'.format( package_id )
            )
        return result["result"][0]


    def read_package_list_with_resources(self):
        """Read all datasets and resources from DKAN portal
            Or from local cache file if it exists
        """
        return self.read_remote_json_with_cache(
            config.api_resource_list,
            'current_package_list_with_resources{}.json'.format( hashlib.md5(config.api_resource_list.encode()).hexdigest()
            )
        )


class Dkan2Excel:
    ''' Read from DKAN, write to excel file '''

    def showConfigVars(self):
        ''' print all config variables '''
        for item in dir(config):
            if not item.startswith("__"):
                logging.debug("CONFIG %s", "{}: {}".format(item, getattr(config,item)))


    def read_all_extra_fields_from_dkan(self, dkanApi, data):
        extras = {}
        for package_data in data['result'][0]:
            dkanApi.add_extras_from_package(extras, package_data)

        logging.debug(_("Alle 'Additional-Info'-Felder der DKAN-Instanz: %s"), extras)
        return extras


    def run(self, command_line_excel_filename):
        try:
            excel_filename = command_line_excel_filename if command_line_excel_filename else config.excel_filename

            self.showConfigVars()

            dkanApi = DkanApiAccess()
            data = dkanApi.read_package_list_with_resources()
            number_of_datasets = len(data['result'][0])
            logging.info("Anzahl Datensätze im DKAN: %s", number_of_datasets)

            extra_columns = self.read_all_extra_fields_from_dkan(dkanApi, data)

            excel_file = ExcelResultFile(excel_filename, extra_columns)
            excel_file.initialize_new_excel_file_with_existing_content()

            existing_dataset_ids = excel_file.get_existing_dataset_ids()
            nr_of_changes = 0

            limit = 100000
            dataset_query = config.dataset_ids
            match = re.search(r'[-\w]*limit\s*=\s*(\d+)[\w,]*',dataset_query,flags = re.S|re.M)
            if match:
                limit = int(match.group(1))
                logging.info(_("Beschränkung per 'Limit'-Query auf %s Datensätze."), limit)
                dataset_query = dataset_query.replace(match.group(0), '')

            # write all datasets and resources to excel file
            for package_data in data['result'][0]:

                isValid = dkanApi.validateJson(package_data, constants.datasetSchema)
                if not isValid:
                    raise ValueError('Dataset format is not valid. Scroll up, see detailed error above')

                dataset_id = package_data['id']
                if dataset_query and (dataset_query.find(dataset_id) == -1):
                    logging.debug(_("%s nicht in %s"), dataset_id, dataset_query)
                    continue
                elif dataset_query:
                    logging.info(_("Datensatz gefunden: %s"), dataset_id)

                if (not config.overwrite_rows) and (dataset_id in existing_dataset_ids):
                    logging.info(_("Bereits im Excel. Überspringe %s"), dataset_id)
                    continue

                if package_data['type'] != 'Dataset':
                    logging.debug(_("Objekt ist kein 'Dataset'. Überspringe %s"), dataset_id)
                    continue

                node_data = None
                # Sadly all the api endpoints with a list of datasets have missing data
                # That is why we have to make two extra calls per package_data.  .. maybe there is another way..?
                if config.x_download_extended_dataset_infos:
                    node_data = dkanApi.readDatasetNodeJson(dataset_id, None)

                # http-check package_data resources and add check result into nested resource list
                if (not config.skip_resources) and ('resources' in package_data):
                    for index, resource in enumerate(package_data['resources']):
                        if config.check_resources:
                            logging.debug("Check: %s", resource['url'])
                            (ok, response_code) = dkanApi.get_resource_http_status(resource['url'])
                            logging.debug("Response: %s %s", ok, response_code)
                        else:
                            ok = response_code = None
                        package_data['resources'][index]['response_ok'] = ok
                        package_data['resources'][index]['response_code'] = response_code

                excel_file.add_dataset(package_data, node_data)
                nr_of_changes += 1
                if nr_of_changes >= limit:
                    logging.info(_("Limit von %s erreicht"), limit)
                    break


            excel_file.finish()
            logging.info("")
            logging.info(_('Vorgang abgeschlossen, %s Datensätze nach Excel geschrieben.'), nr_of_changes)

        except AbortProgramError as err:
            logging.error(err.message)

        except Exception as e:
            logging.error(_("Fehler #23: %s"), repr(e))
            logging.error(traceback.format_exc())


def write(command_line_excel_filename):
    main = Dkan2Excel()
    main.run(command_line_excel_filename)



def validate_single_dataset_row(source_row, source_node_id):
    logging.debug(_("Prüfung des Datensatzes %s beginnt."), source_node_id)
    dkanApi = DkanApiAccess()

    node_data = dkanApi.readDatasetNodeJson(None, source_node_id)
    package_id = node_data['uuid']
    logging.info(_("Prüfen der Package-ID %s"), package_id)
    package_data = dkanApi.read_single_package(package_id)

    extra_columns = {}
    dkanApi.add_extras_from_package(extra_columns, package_data)

    logging.info(_(" == Package-Daten == "))
    print(json.dumps(package_data, indent=2))

    excel_file = ExcelResultFile("dummy.xlsx", extra_columns)
    result_rows = excel_file.convert_dkan_data_to_excel_row_hash(package_data, node_data, False)
    result_row = result_rows[0]

    error_fields = {}

    logging.debug(_(" == Quell-Zeile == "))
    logging.debug(json.dumps(source_row, indent=2))

    logging.info(_(" == Ergebnis-Zeile == "))
    logging.debug(json.dumps(result_row, indent=2))

    change_ok = [
        constants.Dataset.NAME, constants.Dataset.URL, constants.Dataset.DATE_CREATED, constants.Dataset.DATE_MODIFIED,
        constants.Resource.RESOURCE_ID, constants.Resource.LFD_NR
    ]

    dkan_fields = {**constants.get_column_config_dataset(), **constants.get_column_config_resource(), **constants.get_column_config_resource_detailed()}

    for key, value in source_row.items():
        if key in dkan_fields:
            del dkan_fields[key]

        if not key in result_row:
            if key[:6] == "Extra-":
                logging.info(_(' o "%s" OK, leer'), key)
            else:
                error_fields[key] = 'fehlt'
                logging.warning(_(' - "%s" fehlt'), key)
        elif result_row[key] != value:
            if key in change_ok:
                logging.info(_(' O "%s" Abweichung OK: "%s"'), key, value)
            else:
                error_fields[key] = 'Abweichung'
                logging.warning(_(' x "%s" erwartet "%s", bekommen "%s"'), key, value, result_row[key])
        else:
            logging.info(_(' o "%s" OK'), key)

    for key in dkan_fields.keys():
        logging.info(_(' - "%s" nicht getestet'), key)


    return error_fields

def test_excel_file(command_line_excel_filename):
    # print excel file infos
    print_excel_status(command_line_excel_filename)


def test_and_status(command_line_excel_filename):
    '''
        A bunch of tests are performed to check if
        the dkan instance is compatible to this version of dkan uploader
    '''
    # print all config variables
    logging.info("")
    logging.info(_("#######   Aktuelle Konfigurationseinstellungen  #######"))
    for item in dir(config):
        if not (item.startswith("__") or item.startswith("x_")):
            if "password" in item:
                logging.info(" - %s: ...", item)
            else:
                logging.info(" - %s: %s", item, getattr(config,item))

    # iterate all datasets once to find all defined extras
    dkanApi = DkanApiAccess()
    data = dkanApi.read_package_list_with_resources()
    nr_datasets = 0
    first_dataset = None
    extras = {}
    for package_data in data['result'][0]:
        if package_data['type'] != 'Dataset':
            continue
        nr_datasets += 1
        if not first_dataset:
            first_dataset = package_data
        dkanApi.add_extras_from_package(extras, package_data)

    logging.info("")
    logging.info(_("#######  Informationen zur DKAN-Instanz  #######"))
    logging.info(_(" - Anzahl Datensätze: %s"), nr_datasets)
    logging.info(_(" - Folgende 'additional-info'-Felder werden genutzt:"))
    if extras:
        for key, value in extras.items():
            logging.info(_('     "%s" (%s mal)'), key, value)
    else:
        logging.info("     - keine - ")

    if not first_dataset:
        logging.error(_(" - Kein Dataset zum Testen gefunden! Statustest Abbruch."))
    else:
        dataset_id = first_dataset['id']
        logging.info(_(" - Die folgende Tests werden ausgeführt mit Datensatz '%s' (%s)."), first_dataset['title'], dataset_id)

        # check the ckan-package-json response
        isValid1 = dkanApi.validateJson(first_dataset, constants.datasetSchema)
        if not isValid1:
            logging.warning(_(" - Unerwartete API-Response bei 'current_package_list_with_resources'"))
        else:
            logging.info(_(" - Keine Probleme bei API-Response 'current_package_list_with_resources'"))

        # check the node.json response
        isValid2 = False
        try:
            dkanApi.readDatasetNodeJson(dataset_id, None)
            logging.info(_(" - Keine Probleme bei API-Response 'node.json'"))
            isValid2 = True
        except ValueError:
            logging.warning(_(" - Unerwartete API-Response bei 'node.json'"))

        if isValid1 and isValid2:
            logging.info(_(" - DKAN Instanz scheint kompatibel zu sein"))
        else:
            logging.error(_(" - Fehler #5003 - Die DKAN Instanz ist nicht kompatibel zu DKAN-Uploader!"))

    logging.info(_(" - Test der DKAN-Login-URL und -Benutzerdaten:"))
    errormessage = dkanhandler.connect()
    if errormessage:
        logging.error(_('    Login fehlgeschlagen!'))
        logging.error('    %s', errormessage)
        logging.error(_('    Ist der DKAN-Server erreichbar?'))
        logging.error(_('    Bitte prüfen Sie DKAN-URL, Benutzername und Password. %s, ...'), config.dkan_username)
    else:
        logging.info(_('    - Login erfogreich. - '))

    logging.info("")
    logging.info(_('Tests abgeschlossen.'))



def print_excel_status(command_line_excel_filename):
    excel_filename = command_line_excel_filename if command_line_excel_filename else config.excel_filename

    logging.info("")
    logging.info(_("#######  Informationen zur Excel-Datei  #######"))

    dkan_dataset_fields = constants.get_column_config_dataset()
    dkan_resource_fields = constants.get_column_config_resource()
    dkan_resource_detailed = constants.get_column_config_resource_detailed()
    dkan_fields = {**dkan_dataset_fields, **dkan_resource_fields, **dkan_resource_detailed}

    logging.info(_(" Dateiname: %s"), excel_filename)
    logging.info(_(" Absoluter Pfad: %s"), os.path.abspath(excel_filename))
    loc = (excel_filename)

    try:
        wb = xlrd.open_workbook(loc)
    except FileNotFoundError:
        logging.warning(" Datei existiert noch nicht, es können keine Informationen zur Excel-Datei ausgegben werden.")
        return

    sheet = wb.sheet_by_index(0)
    sheet.cell_value(0, 0)

    used_fields = {}
    columns = []
    logging.info(_(" Datei hat %s Zeilen."), sheet.nrows)
    logging.info(_(" Gefundene Spaltenüberschriften der Excel-Datei:"))
    for i in range(sheet.ncols):

        column_name = sheet.cell_value(0, i)
        columns.append(column_name)

        if column_name in dkan_fields:
            used_fields[column_name] = 1
            logging.info(" o %s", column_name)
        elif column_name[:6] == "Extra-":
            logging.info(_(" o %s => Zusätzliches Info-Feld"), column_name)
        else:
            logging.warning(_(" X %s => Kein passendes DKAN-Feld gefunden"), column_name)

    for field in dkan_fields:
        if not field in used_fields:
            if field in dkan_resource_detailed:
                logging.info(_(" - %s => Optionales Feld ist nicht in Excel"), field)
            else:
                logging.warning(_(" > %s => DKAN Feld fehlt in Excel-Datei"), field)
