import os
import sys
import subprocess
import logging
import threading
import markdown
from tkinter import scrolledtext, Tk, Frame, Label, Checkbutton, Button, Entry, StringVar, Text, IntVar, PhotoImage ,\
    HORIZONTAL, DISABLED, SUNKEN, RIDGE, INSERT, NORMAL, END, N, S, W, E, OptionMenu
from tkinter import ttk
from tkinter import messagebox
from datetime import datetime
from . import config
from . import excelreader
from . import excelwriter
from . import confighandler
from . import dkanhandler
from . import dkan_api_test
from .constants import AbortProgramError

def launchExternal(program):
    """launch(program)
    Run program as if it had been double-clicked in Finder, Explorer,
    Nautilus, etc. On OS X, the program should be a .app bundle, not a
    UNIX executable. When used with a URL, a non-executable file, etc.,
    the behavior is implementation-defined.

    Returns something false (0 or None) on success; returns something
    True (e.g., an error code from open or xdg-open) or throws on failure.
    However, note that in some cases the command may succeed without
    actually launching the targeted program."""

    if sys.platform == 'darwin':
        ret = subprocess.call(['open', program])
    elif sys.platform.startswith('win'):
        ret = os.startfile(os.path.normpath(program))
    else:
        ret = subprocess.call(['xdg-open', program])
    return ret


def isWritable(directory):
    try:
        tmp_prefix = "delete_me"
        count = 0
        filename = os.path.join(directory, tmp_prefix)
        while(os.path.exists(filename)):
            filename = "{}.{}".format(os.path.join(directory, tmp_prefix),count)
            count = count + 1
        f = open(filename,"w")
        f.close()
        os.remove(filename)
        return True
    except Exception as e:
        logging.error("Fehler beim Verzeichniszugriff: %s", repr(e))
        return False

def compileDocs():
    with open("docs/index.md", "r", encoding="utf-8") as input_file:
        text = input_file.read()
        html = markdown.markdown(text)
        html = '<html><head><style type="text/css">\
            body {background-color:white;font-family:Verdana, Geneva, Tahoma, sans-serif;margin: 0 auto;\
            max-width: 60em;padding: 40px;margin: 2em auto 9em;background: #fff;color: #333; position: relative;box-shadow: 0 0.3em 1em #000;}\
            p {text-align: justify;}\
            html {background-color:lightsteelblue}\
            code {font-weight: bold;padding: 0 5px;background-color: #eee;border-radius: 4px;white-space: pre-line;}\
            </style></head><body>' + html

        with open("docs/index.html", "w", encoding="utf-8", errors="xmlcharrefreplace") as output_file:
            output_file.write(html)


class LoggingTextHandler(logging.Handler):
    """This class allows you to log to a Tkinter Text or ScrolledText widget"""

    def __init__(self, widget):
        # run the regular Handler __init__
        logging.Handler.__init__(self)
        self.setLevel(logging.DEBUG)

        # Store a reference to the Text it will log to
        self.widget = widget
        self.widget.config(state='normal')
        self.widget.tag_config("INFO", foreground="black")
        self.widget.tag_config("DEBUG", foreground="grey")
        self.widget.tag_config("WARNING", foreground="orange")
        self.widget.tag_config("ERROR", foreground="red")
        self.widget.tag_config("CRITICAL", foreground="red", underline=1)

    def emit(self, record):
        msg = self.format(record)

        #self.widget.configure(state='normal')
        self.widget.insert(END, msg + '\n', record.levelname)
        #self.widget.configure(state='disabled')
        # Autoscroll to the bottom
        self.widget.yview(END)
        self.widget.update()


class MainGui(Frame):
    """Display the Main GUI Window"""

    wwindow = None
    thrd_name = ''
    thrd = None

    def __init__(self, window):

        self.wwindow = window

        # Create two top level frames
        Frame.__init__( self, window )
        top = window.winfo_toplevel()
        top.rowconfigure( 0, weight=1 )
        top.columnconfigure( 0, weight=1 )
        top.columnconfigure( 1, weight=3 )

        # Setting icon of master window
        p1 = PhotoImage(file = 'app-icon.gif')
        window.iconphoto(False, p1)

        # Create left frame with 3 form columns
        master = ttk.Frame(window, padding=(20, 30, 12, 12), borderwidth=10)
        master.grid(column=0, row=0, sticky=(N, S, E, W))
        master.columnconfigure( 0, weight=4 )
        master.columnconfigure( 1, weight=10 )
        master.columnconfigure( 2, weight=10 )

        # Create right frame with logging-info-textbox
        self.master = master
        self.init_logging_textarea(window)

        window.title("DKAN Uploader")
        logging.info("DKAN Uploader v0.12 (2020-12-18)")
        logging.info("================================")
        self.message_with_time('Programmstart')

        # -- Main layout --
        currentRow = 0
        y_spacing = 10
        headline_font = ("Arial", 11, "bold")

        # Headline
        headline_label = Label(master, text="DKAN Uploader", foreground='navy', font=("Helvetica", 20, "bold"))
        headline_label.grid(row=0, column=0, columnspan=3)

        # Show App Icon in Header
        #p2 = p1.zoom(2)
        #labelWuerfel = Label(master, image=p2)
        #labelWuerfel.image=p2 # keep reference to image so garbe collection doesnt remove it..
        #labelWuerfel.grid(row=0, column=0, sticky=W)

        # Show help icon in header
        currentRow += 1
        help_button = Button(master, text="?", command=self.action_help)
        help_button.grid(row=0, column=0, sticky=W)


        # Config headline
        currentRow += 1
        config_label = Label(master, text=_("Konfiguration"), font=headline_font)
        config_label.grid(row=currentRow, column=1, columnspan=2, sticky=W, pady=(10, 0))

        # Filename inputs
        currentRow += 1
        vcmd = master.register(self.validate)   # we have to wrap the command
        self.download_dir = Entry(master, validate="key", validatecommand=(vcmd, '%P'))
        self.download_dir.delete(0, END)
        self.download_dir.insert(0, config.download_dir)
        self.download_dir.grid(row=currentRow, column=1, columnspan=2, sticky=W+E, pady=(y_spacing, 0))
        self.download_label = Label(master, text=_("Ressourcen-Verzeichnis:"))
        self.download_label.grid(row=currentRow, column=0, sticky=E, pady=(y_spacing, 0))
        currentRow += 1
        self.filename_input = Entry(master, validate="key", validatecommand=(vcmd, '%P'))
        self.filename_input.delete(0, END)
        self.filename_input.insert(0, config.excel_filename)
        self.filename_input.grid(row=currentRow, column=1, columnspan=2, sticky=W+E)
        self.filename_label = Label(master, text=_("Excel-Dateiname:"))
        self.filename_label.grid(row=currentRow, column=0, sticky=E)
        currentRow += 1

        # Excel file action buttons
        bb = Button(master, text=_("Dateipfade prüfen"), command=self.action_check_excel)
        bb.grid(row=currentRow, column=1, sticky=W+E, pady=(y_spacing, y_spacing))
        bb2 = Button(master, text=_("Excel-Datei öffnen"), command=self.action_open)
        bb2.grid(row=currentRow, column=2, sticky=W+E, pady=(y_spacing, y_spacing))

        # DKAN Url
        currentRow += 1
        self.url_input = Entry(master, validate="key", validatecommand=(vcmd, '%P'))
        self.url_input.delete(0, END)
        self.url_input.insert(0, config.dkan_url)
        self.url_input.grid(row=currentRow, column=1, columnspan=2, sticky=W+E)
        self.url_label = Label(master, text=_("DKAN-Url:"))
        self.url_label.grid(row=currentRow, column=0, sticky=E)

        # DKAN credentials
        currentRow += 1
        self.user_input = Entry(master)
        self.user_input.delete(0, END)
        self.user_input.insert(0, config.dkan_username)
        self.user_input.grid(row=currentRow, column=1,  sticky=W+E)

        self.password_input = Entry(master, show="*")
        self.password_input.delete(0, END)
        self.password_input.insert(0, config.dkan_password)
        self.password_input.grid(row=currentRow, column=2, sticky=W+E)

        self.cred_label = Label(master, text=_("User/Password:"))
        self.cred_label.grid(row=currentRow, column=0, sticky=E)

        # Test & Status button
        currentRow += 1
        self.status_button = Button(master, text=_("Verbindungstest & Status"), command=self.action_status)
        self.status_button.grid(row=currentRow, column=1, sticky=W+E, pady=(y_spacing, 0))
        self.test_button = Button(master, text=_("DKAN API Schreibtest"), command=self.action_test)
        self.test_button.grid(row=currentRow, column=2, sticky=W+E, pady=(y_spacing, 0))

        ## -- Dataset settings section --
        currentRow += 1
        ttk.Separator(master, orient=HORIZONTAL).grid(column=0, row=currentRow, columnspan=3, sticky='we', pady=(20, 0))
        currentRow += 1
        aktion_label = Label(master, text=_("Einstellungen"), font=headline_font)
        aktion_label.grid(row=currentRow, column=1, columnspan=2, sticky=W, pady=(10, 0))

        # Input field for Dataset Query/Limit
        currentRow += 1
        validate_query = master.register(self.validate_query)   # we have to wrap the command
        self.query_input = Entry(master, validate="key", validatecommand=(validate_query, '%P'))
        self.query_input.delete(0, END)
        self.query_input.insert(0, str(config.dataset_ids))
        self.query_input.grid(row=currentRow, column=1, columnspan=2, sticky=W+E, pady=(10, 0))
        self.query_label = Label(master, text=_("Datensatz-Beschränkung:"))
        self.query_label.grid(row=currentRow, column=0, sticky=E, pady=(10, 0))

        # Debug Mode Dropdown
        currentRow += 1
        OptionList = ["Debug","Normal"]
        self.message_level = StringVar(master)
        self.message_level.set(config.message_level if config.message_level else OptionList[0])
        self.debug_opt=OptionMenu(master, self.message_level, *OptionList)
        self.debug_opt.grid(row=currentRow, column=1, columnspan=2, sticky=W, pady=(y_spacing, y_spacing))
        self.query_label = Label(master, text=_("Info-Level:"))
        self.query_label.grid(row=currentRow, column=0, sticky=E, pady=(y_spacing, y_spacing))

        ## -- Download section --
        currentRow += 1
        ttk.Separator(master, orient=HORIZONTAL).grid(column=0, row=currentRow, columnspan=3, sticky='we', pady=(20, 0))
        currentRow += 1
        aktion_label = Label(master, text=_("Lese Daten aus DKAN"), font=headline_font)
        aktion_label.grid(row=currentRow, column=1, columnspan=2, sticky=W, pady=(10, 0))

        currentRow +=1
        Label(master, text=_("Optionen:")).grid(row=currentRow, column=0, sticky=E, pady=(y_spacing, 0))
        self.skip_resources = IntVar(value=(1 if config.skip_resources else 0))
        Checkbutton(master, text = _("Nur Datensätze, keine Ressourcen"),variable = self.skip_resources).grid(row=currentRow, column=1, columnspan=2,  sticky=W)

        currentRow +=1
        self.check_resources = IntVar(value=(1 if config.check_resources else 0))
        Checkbutton(master, text = _("Ressourcen-URLs überprüfen"),variable = self.check_resources).grid(row=currentRow, column=1, columnspan=2,  sticky=W)

        currentRow +=1
        self.detailed_resources = IntVar(value=(1 if config.detailed_resources else 0))
        Checkbutton(master, text = _("Detaillierte Ressourcendaten (langsamer)"),variable = self.detailed_resources).grid(row=currentRow, column=1, columnspan=2,  sticky=W)

        currentRow +=1
        self.resources_download = IntVar(value=(1 if config.resources_download else 0))
        Checkbutton(master, text = _("Ressourcen-Dateien herunterladen"),variable = self.resources_download).grid(row=currentRow, column=1, columnspan=2,  sticky=W)

        currentRow += 1
        self.download_button = Button(master, text="DKAN -> Excel", command=self.action_download)
        self.download_button.grid(row=currentRow, column=1, sticky=W+E, pady=(y_spacing, 0))

        ## -- Upload section --
        currentRow += 1
        ttk.Separator(master, orient=HORIZONTAL).grid(column=0, row=currentRow, columnspan=3, sticky='we', pady=(20, 0))
        currentRow += 1
        aktion_label = Label(master, text=_("Schreibe Daten zum DKAN"), font=headline_font)
        aktion_label.grid(row=currentRow, column=1, columnspan=2, sticky=W, pady=(10, 0))

        currentRow += 1
        self.upload_button = Button(master, text=_("Excel -> DKAN"), command=self.action_upload)
        self.upload_button.grid(row=currentRow, column=1, sticky=W+E, pady=(y_spacing, 0))


        # Give all weight to an empty row at the bottom, so it will take all the space on window resize by user
        currentRow +=1
        self.empty_space = Label(master, text="")
        self.empty_space.grid(row=currentRow, column=0, sticky=E, pady=(y_spacing, 0))
        master.rowconfigure( currentRow, weight=1 )


    def init_logging_textarea(self, window):
        # Textarea for Log File display
        self.master_right = ttk.Frame(window, padding=(3, 3, 12, 12))
        self.master_right.grid(column=1, row=0, sticky=(N, S, E, W))
        self.master_right.rowconfigure( 0, weight=1 )
        self.master_right.columnconfigure( 0, weight=1 )

        self.info_box = scrolledtext.ScrolledText(self.master_right, state='normal', wrap='none', relief=RIDGE)
        self.info_box.configure(font='TkFixedFont')
        self.info_box.grid(row=0, column=0, sticky=(N, S, E, W))

        # Progressbar
        self.progress_text = StringVar(self.master_right)
        self.progress_text.set('')
        self.progress_label = Label(self.master_right, textvariable=self.progress_text)
        self.progress_label.grid(row=1, column=0, sticky=W+E)
        self.progress = ttk.Progressbar(self.master_right, orient = HORIZONTAL, length = 100, mode = 'indeterminate')
        self.progress.configure(mode='determinate',value=0)
        self.progress.grid(row=2, column=0, sticky=(N, S, E, W))

        # Create textLogger
        self.log_textwindow_handler = LoggingTextHandler(self.info_box)

        # Add the handler to logger
        logger = logging.getLogger()
        logger.addHandler(self.log_textwindow_handler)


    def update_config(self):
        config.dkan_url = self.url_input.get()
        config.dkan_username = self.user_input.get()
        config.dkan_password = self.password_input.get()
        config.excel_filename = self.filename_input.get()
        config.download_dir = self.download_dir.get()
        config.check_resources = self.check_resources.get()
        config.skip_resources = self.skip_resources.get()
        config.detailed_resources = self.detailed_resources.get()
        config.resources_download = self.resources_download.get()
        config.dataset_ids = self.query_input.get()
        config.message_level = self.message_level.get()

        logging.debug("Log level: %s", config.message_level)
        self.log_textwindow_handler.setLevel(logging.INFO if config.message_level == 'Normal' else logging.DEBUG)
        has_changed = confighandler.write_config_file()
        if has_changed:
            logging.debug(_("Konfiguration wurde geändert."))
            dkanhandler.disconnect()
            self.clear_temp_dir()


    def clear_temp_dir(self):
        tempdir = config.x_temp_dir
        logging.debug(_("Cacheverzeichnis wird geleert: %s"), tempdir)
        for filename in os.listdir(tempdir):
            file_path = os.path.join(tempdir, filename)
            try:
                if (os.path.isfile(file_path) or os.path.islink(file_path)) and file_path.endswith('.json'):
                    logging.debug(_("Lösche Datei '%s'"), file_path)
                    os.unlink(file_path)
            except Exception as e:
                logging.warning('Löschen fehlgeschlagen: %s. Grund: %s', file_path, e)


    def validate(self, new_text):
        # logging.debug("There could be a validation here")
        return True


    def validate_query(self, dataset_query):
        return True


    def action_open(self):
        ''' Open external file "with a double click" '''
        filename = self.filename_input.get()
        if not os.path.isfile(filename):
            logging.error(_("Die Datei '%s' existiert nicht."), filename)
        else:
            launchExternal(filename)


    def action_help(self):
        compileDocs()
        launchExternal('docs/index.html')

    def action_check_excel(self):
        self.show_progressbar(_('Dateipfade prüfen'))
        self.update_config()
        excelwriter.test_excel_file(False)

        logging.info("")
        logging.info(_("#######  Informationen zum Up-/Download-Verzeichnis  #######"))

        check_dir = os.path.normpath(config.download_dir)
        logging.info("Prüfe Up-/Download-Verzeichnis: %s", check_dir)
        logging.info("Absoluter Pfad: %s", os.path.abspath(config.download_dir))
        if os.path.isdir(check_dir):
            logging.info(_("Verzeichnis existiert."))
        else:
            logging.warning(_("Verzeichnis existiert nicht. Uploads können nicht durchgeführt werden."))
            logging.error("Bitte legen Sie das Up-/Download Verzeichnis an und stellen Sie sicher, dass es beschreibbar ist.")

        if isWritable(check_dir):
            logging.info(_("Verzeichnis ist beschreibbar."))
        else:
            logging.warning(_("Verzeichnis ist nicht beschreibbar. Downloads können nicht durchgeführt werden."))

        self.cleanup_progressbar()


    def check_thread(self):
        if not self.thrd.is_alive():
            self.cleanup_progressbar()
            return
        self.wwindow.after(500, self.check_thread)


    def cleanup_progressbar(self):
        self.message_with_time(_('Aktion fertig: {}').format(self.thrd_name))
        self.progress_text.set('')
        self.progress.stop()
        self.progress.configure(mode='determinate',value=0)
        self.set_all_widget_state("normal")

    def show_progressbar(self, thread_name):
        self.message_headline(_('Aktion: {}').format(thread_name))
        self.progress_text.set(_('Vorgang läuft: {}'.format(thread_name)))
        self.thrd_name = thread_name
        self.progress.configure(mode='indeterminate')
        self.progress.start()
        self.set_all_widget_state("disabled")

    def set_all_widget_state(self, wstate):
        for widget in self.master.winfo_children():
            wtype = str(widget.winfo_class())
            if wtype == 'Button' or wtype == 'Entry' or wtype == 'Checkbutton' or wtype == 'Menubutton':
                widget.configure(state=wstate)


    def execute_thread(self, fn, thread_name):
        self.show_progressbar(thread_name)
        self.thrd = threading.Thread(target=fn)
        self.thrd.daemon = True
        self.thrd.start()
        self.check_thread()


    def action_status(self):
        self.update_config()
        self.execute_thread(lambda: excelwriter.test_and_status(False), 'Systemtest & Status')


    def action_test(self):
        self.update_config()
        self.execute_thread(dkan_api_test.test, 'DKAN-API Schreibtest')


    def action_download(self):
        self.update_config()
        self.execute_thread(lambda: excelwriter.write(False), 'DKAN auslesen')


    def action_upload(self):
        result = messagebox.askokcancel(
            _("In DKAN-Instanz schreiben"),
            _("Die Datensätze aus der Excel-Datei werden nun ins DKAN geschrieben.\n\nWirklich fortfahren?"))
        if result:
            self.update_config()
            self.show_progressbar(_('DKAN schreiben'))
            self.clear_temp_dir()
            try:
                excelreader.read(False)
            except AbortProgramError as err:
                logging.error(err.message)

            self.clear_temp_dir()
            self.cleanup_progressbar()


    def message_headline(self, message):
        self.message_with_time('Button-Interaktion')
        size=30
        logging.info("")
        logging.info("#" * (size+4))
        logging.info(_("# %s #"), message.center(size, ' '))
        logging.info("#" * (size+4))
        logging.info("")

    def message_with_time(self, message):
        now = datetime.now()
        dt_string = now.strftime("%d.%m.%Y %H:%M:%S")
        logging.info("")
        logging.info("%s - %s", dt_string, message)




def show():
    root = Tk()

    mm = MainGui(root)

    def on_closing():
        mm.update_config()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)

    root.mainloop()
