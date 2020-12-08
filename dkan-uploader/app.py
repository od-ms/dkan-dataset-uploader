"""Main source file for DKAN REMOTE CONTROL
"""

import argparse
import textwrap
import logging
import configparser
from . import excelwriter
from . import main_gui
from . import config
from . import confighandler

logging.basicConfig(level=logging.DEBUG, format='<%(asctime)s %(levelname)s> %(message)s')


class DkanUploader:
    """Main file DKAN REMOTE CONTROL"""

    @staticmethod
    def run():
        logging.debug('Start of program')

        confighandler.read_config_file()

        args = DkanUploader.get_commandline_args()

        config.overwrite_rows = True if args.overwrite else False
        config.dataset_ids = args.ids

        if args.download:
            excelwriter.write(args.filename)
        else:
            print("")
            print("Starting in GUI mode. To print available command line options, start with --help.")
            print("")
            main_gui.show()

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
        parser.add_argument('-or', '--overwrite-rows', action='store_true', dest='overwrite',
            help='If datasets already exist in the excel file, overwrite the row content. (Default: no)')
        parser.add_argument('-n', '--ids', action='store_true', dest='ids',
            help='Comma separated list of dataset IDs. Limits action to these dataset IDs (upload or download)')

        args = parser.parse_args()
        logging.info("Command line arguments: %s", args)

        return args
