"""Main source file for DKAN REMOTE CONTROL
"""

import argparse
import textwrap
import logging
import os.path
from datetime import datetime
from . import config
from . import main_gui
from . import excelwriter
from . import excelreader
from . import confighandler
from . import dkan_api_test

logging.basicConfig(level=logging.DEBUG, format='<%(asctime)s %(levelname)s> %(message)s')
logging.getLogger("requests").setLevel(logging.WARNING)


# Setup additional logger that reports everything into one file per program run -- at "debug"-level, no matter what loglevel was set in the gui
log_now = datetime.now() # current date and time
log_filename = log_now.strftime("%Y-%m-%d_%H%M%S.log")
log_file = os.path.normpath(config.x_log_dir + log_filename)
log_handler = logging.FileHandler(log_file, mode='a')
log_formatter = logging.Formatter('%(asctime)s %(levelname)s\t%(message)s'), datefmt='%I:%M:%S')
log_handler.setFormatter(log_formatter)
log_handler.setLevel(logging.DEBUG)
logger = logging.getLogger()
logger.addHandler(log_handler)


class DkanUploader:
    """Main file DKAN REMOTE CONTROL"""

    @staticmethod
    def run():
        logging.debug('Start of program')

        confighandler.read_config_file()

        args = DkanUploader.get_commandline_args()

        # copy command line arguments into config
        config.overwrite_rows = True if args.overwrite else False
        if args.ids:
            config.dataset_ids = args.ids

        if args.download:
            excelwriter.write(args.filename)
        elif args.upload:
            excelreader.read(args.filename)
        elif args.testwrite:
            dkan_api_test.analyze()
        elif args.node_id:
            dkan_api_test.validate(args.node_id)

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
            formatter_class=argparse.RawTextHelpFormatter,
            epilog=textwrap.dedent('''\
        DKAN remote control - instructions
        ==================================

        Running this without any command line arguments will start the interactive GUI window mode.
        If you want want to automate the up- or download of data to a DKAN instance, then use the command line switches as described above.
        '''))

        # Command line arguments for DOWNLOAD
        parser.add_argument('filename', type=str, nargs='?', help='Filename of excel file with data that should be transfered to the DKAN instance')
        parser.add_argument('-n', '--ids', action='store', dest='ids',
            help='Comma separated list of dataset IDs. Limits action to these dataset IDs (upload or download)\n\n')


        parser.add_argument('-d', '--download', action='store_true',
            help='Run in DOWNLOAD mode: The excel file will be overwritten! It will be filled with data from the DKAN instance')
        parser.add_argument('-or', '--overwrite', action='store_true', dest='overwrite',
            help='If datasets already exist in the excel file, overwrite the row content. (Default: no)\n\n')

        # Command line arguments for UPLOAD
        parser.add_argument('-u', '--upload', action='store_true',
            help='Run in UPLOAD mode: The DKAN content will be overwritten with data from the excel file\n\ndkan api debugging:')

        parser.add_argument('-wt', '--write-test', action='store_true', dest='testwrite',
            help='Try to write a test-dataset to DKAN instance')
        parser.add_argument('-vn', '--validate-node-id', action='store', dest='node_id',
            help='Validate node with the given ID')


        args = parser.parse_args()
        logging.info("Command line arguments: %s", args)

        return args
