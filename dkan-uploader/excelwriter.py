#! /usr/bin/python

import sys
import json
import logging
import hashlib
import os.path
from timeit import default_timer as timer
import requests
from jsonschema import validate
from jsonschema.exceptions import ValidationError
import xlrd
import xlsxwriter
import httplib2
from . import config
from . import constants
from . import dkanhelpers
from . import dkanhandler

class AbortProgramError(RuntimeError):
    """ We create an own Error to catch on top level // better control of program flow """

    def __init__(self, message):
        super(AbortProgramError, self).__init__(message)
        self.message = message


class ExcelResultFile:
    """ Handle creation of Excel content """

    # startup values
    filename = ''
    extra_columns = {}

    # runtime config
    workbook = ''
    worksheet = ''
    bold = None
    current_row = 0
    current_dataset_nr = 0
    existing_dataset_ids = {}

    def __init__(self, filename, extra_columns):
        self.filename = filename
        self.extra_columns = extra_columns
        self.current_row = 0

    def initialize_new_excel_file_with_existing_content(self):
        """ Read the extisting excel and save ALL content to "old_excel_content",
            so we can then write it to a "new" file (=to continue from where we left off)
            Also return all dataset_ids as dict, so we can skip them
        """
        logging.info("Reading excel file: %s", self.filename)
        loc = (self.filename)
        self.existing_dataset_ids = {}
        old_excel_content = []

        try:
            wb = xlrd.open_workbook(loc)
            sheet = wb.sheet_by_index(0)

            # check if columns of excel file are same as our config
            headline_row = self.get_column_config()
            for i in range(sheet.ncols):
                column_header = sheet.cell_value(0, i)
                if i >= len(headline_row):
                    logging.warning(_("Folgende Spalte wird ignoriert: {}").format(column_header))
                elif column_header != headline_row[i]:
                    logging.warning(_("Different fields in DKAN and Excel file: {} != {}").format(column_header, headline_row[i]))
                    raise AbortProgramError(
                        _("Die bereits existierende Excel-Datei hat einen falschen Spalten-Aufbau.\n"
                            + "Problem in Spalte {}: Erwartet war '{}', aber gefunden wurde '{}'\n"
                            + "Laden Sie den DKAN Inhalt am besten in eine andere Excel-Datei"
                            + " (z.B. geben Sie einen Dateinamen an, der noch nicht existiert, und vergleichen Sie dann die Spalten der beiden Dateien)")
                        .format(i, headline_row[i], column_header)
                        )



            for j in range(1, sheet.nrows):
                excelrow = []
                for i in range(sheet.ncols):
                    excelrow.append(sheet.cell_value(j, i))

                old_excel_content.append(excelrow)

                # save all package_data ids for later use (=lookup of existing ids)
                dataset_id = excelrow[0]
                if dataset_id:
                    self.existing_dataset_ids[dataset_id] = True

        except FileNotFoundError:
            pass

        self.initialize_new_excel_file()

        for row in old_excel_content:
            self.add_plain_row(row)

    def get_existing_dataset_ids(self):
        logging.debug("Existing ids: %s", self.existing_dataset_ids)
        return self.existing_dataset_ids


    def initialize_new_excel_file(self):

        # init workbook objects
        self.workbook = xlsxwriter.Workbook(self.filename)
        self.worksheet = self.workbook.add_worksheet()
        self.bold = self.workbook.add_format({'bold': True})
        self.worksheet.set_column('A:A', 15)
        self.worksheet.set_column('C:C', 20)

        # Add group ("level: 1") to some columns so that they are "einklappbar"
        self.worksheet.set_column('D:Y', None, None, {'level': 1})

        # write header row
        self.worksheet.write_row('A1', self.get_column_config(), self.bold)


    def get_column_config(self):
        columns = list(self.get_column_config_dataset().keys())
        if not config.skip_resources:
            columns.extend(self.get_column_config_resource().keys())
        return columns


    def add_plain_row(self, column_contents):
        # logging.debug("Writing row %s", column_contents)
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

            logging.debug("Nested dkan-value: %s => %s", keys[0], node_value)

        except (TypeError, KeyError, IndexError):
            logging.debug("Empty key: %s", keys)

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


    def convert_dkan_data_to_excel_row(self, package_data, dkan_node):
        self.current_dataset_nr += 1
        # get the config of which excel columns are mapped to which dkan json keys
        columns_json_keys = self.get_column_config_dataset().values()
        columns = []
        for column_key in columns_json_keys:
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
                for t_index in range(0,10):
                    rel = self.get_nested_json_value(dkan_node, ["field_related_content", 'und', t_index])
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
                        tags.append('"?" ({})'.format(t_id))
                    value = ", ".join(tags)

            else:
                value = package_data[column_key] if column_key in package_data else None
            columns.append(value)

        # write package_data row without resources
        if (config.skip_resources) or ('resources' not in package_data):
            return columns

        # write resource rows
        else:
            for resource_number, resource in enumerate(package_data['resources']):
                resource_row = []
                if resource_number == 0:
                    resource_row = columns.copy()
                else:
                    resource_row = [''] * len(columns)

                # get all resource fields according to resource column config
                rcolumns_config = self.get_column_config_resource().values()
                for rc_key in rcolumns_config:
                    rc_value = ""
                    if isinstance(rc_key, list):
                        raise AbortProgramError(_('Anruf von Resource-Node-Daten ist noch nicht implementiert.'))

                    if rc_key == 'lfd-nr':
                        rc_value = str(self.current_dataset_nr) + '-' + str(resource_number+1)

                    elif rc_key == 'RTYPE':
                        rc_value = 'url'
                        url_keyname = self.get_column_config_resource()[constants.Resource.URL]
                        if isinstance(url_keyname, list):
                            raise AbortProgramError(_('Anruf von Resource-Node-Daten ist noch nicht implementiert.'))
                        if (url_keyname in resource):
                            if resource[url_keyname].find(config.x_uploaded_resource_path) != -1:
                                rc_value = 'uploaded'
                            elif resource[url_keyname].find(config.x_uploaded_datastore_path) != -1:
                                rc_value = 'datastore'

                    else:
                        try:
                            rc_value = resource[rc_key]
                        except KeyError:
                            logging.error('Key "%s" not found: %s', rc_key, resource)

                    resource_row.extend([rc_value])

            return resource_row


    def add_dataset(self, package_data, dkan_node):
        row = self.convert_dkan_data_to_excel_row(package_data, dkan_node)
        self.add_plain_row(row)


    def convert_dkan_data_to_excel_row_hash(self, package_data, dkan_node):
        ''' Create a dictionary with all the package_data information '''
        resource_row = self.convert_dkan_data_to_excel_row(package_data, dkan_node)
        resultarray = {}
        count = 0
        cols = {**self.get_column_config_dataset(), **self.get_column_config_resource()}
        try:
            for kk in cols:
                resultarray[kk] = resource_row[count]
                count += 1
        except IndexError as ie:
            logging.error("Resource row does not have a column %s (%s)", count, kk)
        return resultarray


    def finish(self):
        self.workbook.close()


class DkanApiAccess:
    """Check status of a resource"""

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
            node_search = self.read_remote_json_with_cache(config.x_api_find_node_id.format(package_id), '{}.json'.format(package_id))
            if node_search[0]['nid']:
                node_id = node_search[0]['nid']

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

        logging.info("All 'additional-info'-fields of DKAN response: %s", extras)
        return extras


    def run(self, command_line_excel_filename):
        excel_filename = command_line_excel_filename if command_line_excel_filename else config.excel_filename

        self.showConfigVars()

        dkanApi = DkanApiAccess()
        data = dkanApi.read_package_list_with_resources()
        extra_columns = self.read_all_extra_fields_from_dkan(dkanApi, data)

        excel_file = ExcelResultFile(excel_filename, extra_columns)
        excel_file.initialize_new_excel_file_with_existing_content()

        existing_dataset_ids = excel_file.get_existing_dataset_ids()

        # write all datasets and resources to excel file
        number = 0
        for package_data in data['result'][0]:

            isValid = dkanApi.validateJson(package_data, constants.datasetSchema)
            if not isValid:
                raise ValueError('Dataset format is not valid. Scroll up, see detailed error above')

            dataset_id = package_data['id']
            if config.dataset_ids and (config.dataset_ids.find(dataset_id) == -1):
                logging.debug("%s not in %s", dataset_id, config.dataset_ids)
                continue

            if (not config.overwrite_rows) and (dataset_id in existing_dataset_ids):
                logging.debug("Already in Excel. Skipping %s", dataset_id)
                continue

            if package_data['type'] != 'Dataset':
                logging.debug("Item is not of type 'Dataset'. Skipping %s", dataset_id)
                continue

            # TODO: this should be removed
            number += 1
            if number == 3:
                logging.debug("Stopping now")
                break

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

        excel_file.finish()



def write(command_line_excel_filename):
    try:
        main = Dkan2Excel()
        main.run(command_line_excel_filename)

    except AbortProgramError as err:
        logging.error(err.message)


def validate_single_dataset_row(source_row, source_node_id):
    logging.debug("validate single dataset row")
    dkanApi = DkanApiAccess()

    node_data = dkanApi.readDatasetNodeJson(None, source_node_id)
    package_id = node_data['uuid']
    logging.info("Checking package id %s", package_id)
    package_data = dkanApi.read_single_package(package_id)

    extra_columns = {}
    dkanApi.add_extras_from_package(extra_columns, package_data)

    logging.info(" == Package data == ")
    print(json.dumps(package_data, indent=2))

    excel_file = ExcelResultFile("dummy.xlsx", extra_columns)
    result_row = excel_file.convert_dkan_data_to_excel_row_hash(package_data, node_data)

    error_fields = {}

    logging.info(" == Source row == ")
    print(json.dumps(source_row, indent=2))
    logging.info(" == Result row == ")
    print(json.dumps(result_row, indent=2))


    for key, value in source_row.items():
        if not key in result_row:
            error_fields[key] = 'fehlt'
            logging.warning(' - "%s" fehlt', key)
        elif result_row[key] != value:
            error_fields[key] = 'Abweichung'
            logging.warning(' x "%s" erwartet "%s", bekommen "%s"', key, value, result_row[key])
        else:
            logging.info(' o "%s" OK', key)

    return error_fields



def test_and_status(command_line_excel_filename):
    '''
        A bunch of tests are performed to check if
        - the dkan instance
        - and the currently used file
        are compatible to this version of dkan uploader
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

    # print excel file infos
    print_excel_status(command_line_excel_filename)

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
    errormessage = dkanhandler.connect(config)
    if errormessage:
        logging.error(_('    Login fehlgeschlagen!'))
        logging.error('    %s', errormessage)
        logging.error(_('    Ist der DKAN-Server erreichbar?'))
        logging.error(_('    Bitte prüfen Sie DKAN-URL, Benutzername und Password. %s, ...'), config.dkan_username)
    else:
        logging.info(_('    - Login erfogreich. - '))




def print_excel_status(command_line_excel_filename):
    excel_filename = command_line_excel_filename if command_line_excel_filename else config.excel_filename

    logging.info("")
    logging.info(_("#######  Informationen zur Excel-Datei  #######"))

    dkan_dataset_fields = constants.get_column_config_dataset()
    dkan_resource_fields = constants.get_column_config_resource()
    dkan_fields = {**dkan_dataset_fields, **dkan_resource_fields}

    logging.info(_(" Dateiname: %s"), excel_filename)
    loc = (excel_filename)

    try:
        wb = xlrd.open_workbook(loc)
    except FileNotFoundError:
        logging.info(" Datei existiert noch nicht. ")
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
            logging.warning(_(" > %s => DKAN Feld fehlt in Excel-Datei"), field)
