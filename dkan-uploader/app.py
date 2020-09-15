"""Main source file for DKAN REMOTE CONTROL
"""

import argparse
import textwrap
import logging
import configparser
from . import excelwriter
from . import main_gui
from . import config

logging.basicConfig(level=logging.DEBUG, format='<%(asctime)s %(levelname)s> %(message)s')


class DkanUploader:
    """Main file DKAN REMOTE CONTROL"""

    @staticmethod
    def run():
        logging.debug('Start of program')

        DkanUploader.read_config_file()
        args = DkanUploader.get_commandline_args()

        if args.download:
            excelwriter.write()
        else:
            print("")
            print("Starting in GUI mode. To print available command line options, start with --help.")
            print("")
            main_gui.show()

    @staticmethod
    def read_config_file():
        """Read config.ini and store content in global config module"""

        config_ini = configparser.ConfigParser()
        config_ini.read('config.ini')
        if 'dkan' not in config_ini:
            logging.warning('Config file not found (or wrong sections..?)')
            logging.warning('Starting with empty config')
        else:
            logging.debug('config sections: %s', config_ini.sections())

            config.dkan_url = config_ini['dkan']['dkan_url']
            config.dkan_username = config_ini['dkan']['username']
            config.dkan_password = config_ini['dkan']['password']
            config.excel_filename = config_ini['excel']['filename']

    @staticmethod
    def get_commandline_args():
        """Read command line args or show help text"""

        # Print usage instructions
        parser = argparse.ArgumentParser(
            prog='dkan-uploader',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=textwrap.dedent('''\
        DKAN remote control - instructions
        ==================================

        Run this file without any command line arguments to use the interactive GUI window mode.

        If you want want to automate the up- or download of data to a DKAN instance, then use the command line switches as described above.
        '''))

        # Parse command line arguments
        parser.add_argument('filename', type=str, nargs='?', help='Filename of excel file with data that should be transfered to the DKAN instance')
        parser.add_argument('-d', '--download', action='store_true',
            help='Run in DOWNLOAD mode: The excel file will be overwritten! It will be filled with data from the DKAN instance')

        args = parser.parse_args()
        logging.info("Command line arguments: %s", args)

        return args
