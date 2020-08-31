"""Main source file for DKAN REMOTE CONTROL
"""

import argparse
import textwrap
import logging

from . import excelreader
from . import main_gui

logging.basicConfig(level=logging.DEBUG, format='<%(asctime)s %(levelname)s> %(message)s')

class DkanUploader:
    """Main file DKAN REMOTE CONTROL"""

    @staticmethod
    def run():
        """ERROR: Too many docstrings required"""

        logging.info('Start of program')

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

        if args.download:
            excelreader.read()
        else:
            main_gui.show()
