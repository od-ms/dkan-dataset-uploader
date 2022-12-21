#! /usr/bin/python

import re
import sys
import logging
import xlrd
import httplib2
from . import config
from . import constants

def check_links(command_line_excel_filename):
    er = LinkChecker()
    er.checkAllLinksInExcelFile(command_line_excel_filename if command_line_excel_filename else config.excel_filename)


class LinkChecker:

    def getHttpStatus(self, url):
        try:
            htl = httplib2.Http(".cache", disable_ssl_certificate_validation=True)
            resp = htl.request(url, 'HEAD')
        except:
            e = sys.exc_info()
            logging.exception("Error during resource load")
            return (False, str(e[0]) + " " + str(e[1]))

        return (int(resp[0]['status']) < 400), resp[0]['status']


    def checkAllLinksInExcelFile(self, excel_filename):

        logging.info(_("Excel Datei wird eingelesen: %s"), excel_filename)
        loc = (excel_filename)

        wb = xlrd.open_workbook(loc)
        sheet = wb.sheet_by_index(0)
        sheet.cell_value(0, 0)

        URL_REGEX = re.compile(r"((http|https)\:\/\/[a-zA-Z0-9\.\/\?\:@\-_=#]+\.([a-zA-Z]){2,6}([a-zA-Z0-9\.\&\/\?\:@\-_=#])*)", re.MULTILINE|re.UNICODE)

        for row_nr in range(1, sheet.nrows):

            for i in range(sheet.ncols):
                column_name = sheet.cell_value(0, i)
                if column_name == "Resource-Url" or column_name == "Resource-Path":
                    continue
                column_value = str(sheet.cell_value(row_nr, i))
                if not column_value:
                    continue

                try:
                    url_match = URL_REGEX.findall(column_value)
                except:
                    e = sys.exc_info()
                    logging.error("Error with value: %s - %s-%s", column_value, row_name, column_name)
                    logging.exception("Error message: %s", str(e[0]) + " " + str(e[1]))
                    continue

                if (url_match):
                    row_name = sheet.cell_value(row_nr, 1)

                    for m in url_match:
                      check_url = m[0]
                      (ok, response_code) = self.getHttpStatus(check_url)

                      logging.log(
                        logging.INFO if ok else logging.ERROR,
                        "[%s|%s] Zeile %s, %s-%s: %s", ok, response_code, row_nr, row_name, column_name, check_url
                        )
