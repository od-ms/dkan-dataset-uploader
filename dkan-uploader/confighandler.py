"""Handle data transfer between config.ini and config.py
"""
import json
import textwrap
import logging
import configparser
from . import config

CONFIG_FILENAME = 'config.ini'


def read_config_file():
    """Read config.ini and store content in global config module"""

    config_ini = configparser.ConfigParser()
    config_ini.read(CONFIG_FILENAME)
    if 'dkan' not in config_ini:
        logging.warning('Config file not found (or wrong sections..?)')
        logging.warning('Starting with empty config')
    else:
        for section in config_ini.sections():
            config_debug = dict(config_ini[section])
            if 'password' in config_debug:
                config_debug['password'] = '...'
            if 'username' in config_debug:
                config_debug['username'] = '{}...'.format(config_debug['username'][:5])
            logging.debug('config: %s %s', section, config_debug)
        try:
            config.dkan_url = config_ini['dkan']['dkan_url']
            config.dkan_username = config_ini['dkan']['username']
            config.dkan_password = config_ini['dkan']['password']
            config.excel_filename = config_ini['excel']['filename']
            config.download_dir = config_ini['excel']['download_dir']
            config.skip_resources = config_ini.getboolean('features', 'skip_resources')
            config.check_resources = config_ini.getboolean('features', 'check_resources')
            config.detailed_resources = config_ini.getboolean('features', 'detailed_resources')
            config.resources_download = config_ini.getboolean('features', 'resources_download')
            config.dataset_ids = config_ini['features']['dataset_ids']
            config.message_level = config_ini['features']['message_level']
        except:
            logging.error("Beim Lesen der Config-Datei ist ein Fehler aufgetreten. Es wird mit der Standard-Config fortgefahren.")


    if 'api' in config_ini:
        if ('package_details' in config_ini['api']) and config_ini['api']['package_details']:
            config.api_package_details = config_ini['api']['package_details']
        else:
            logging.warning('Config-Variable "api.package_details" wurde nicht gefunden, nutze Defaultwert.')

        if ('resource_list' in config_ini['api']) and config_ini['api']['resource_list']:
            config.api_resource_list = config_ini['api']['resource_list']
        else:
            logging.warning('Config-Variable "api.resource_list" wurde nicht gefunden, nutze Defaultwert.')


def write_config_file():
    """Write back values to config.ini

        !! We only need to handle the fields of the GUI here !!
        !! Because the other values cannot have changed      !!
    """

    config_ini = configparser.ConfigParser()
    config_ini.read(CONFIG_FILENAME)

    config_old = {s:dict(config_ini.items(s)) for s in config_ini.sections()}

    config_ini.set('dkan', 'dkan_url', config.dkan_url)
    config_ini.set('dkan', 'username', config.dkan_username)
    config_ini.set('dkan', 'password', config.dkan_password)
    config_ini.set('excel', 'filename', config.excel_filename)
    config_ini.set('excel', 'download_dir', config.download_dir)
    config_ini.set('features', 'skip_resources', 'Yes' if config.skip_resources else 'No')
    config_ini.set('features', 'check_resources', 'Yes' if config.check_resources else 'No')
    config_ini.set('features', 'detailed_resources', 'Yes' if config.detailed_resources else 'No')
    config_ini.set('features', 'resources_download', 'Yes' if config.resources_download else 'No')
    config_ini.set('features', 'dataset_ids', config.dataset_ids)
    config_ini.set('features', 'message_level', config.message_level)

    config_new = {s:dict(config_ini.items(s)) for s in config_ini.sections()}

    if config_new == config_old:
        logging.debug("Config values are unchanged. Not saving config.")
        return False

    else:
        logging.debug('New configuration: %s', config_ini.sections())
        logging.debug('Writing config file: %s', CONFIG_FILENAME)

        with open(CONFIG_FILENAME, 'w') as configfile:
            config_ini.write(configfile)
        return True
