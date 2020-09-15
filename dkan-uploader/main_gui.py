import logging
from tkinter import scrolledtext, Tk, Label, Button, Entry, StringVar, Text, DISABLED, INSERT, NORMAL, END, N, S, W, E
from tkinter import ttk
from . import config
from . import excelreader
from . import excelwriter


class LoggingTextHandler(logging.Handler):
    """This class allows you to log to a Tkinter Text or ScrolledText widget"""

    def __init__(self, widget):
        # run the regular Handler __init__
        logging.Handler.__init__(self)
        self.setLevel(logging.DEBUG)

        # Store a reference to the Text it will log to
        self.widget = widget
        self.widget.config(state='disabled')
        self.widget.tag_config("INFO", foreground="black")
        self.widget.tag_config("DEBUG", foreground="grey")
        self.widget.tag_config("WARNING", foreground="orange")
        self.widget.tag_config("ERROR", foreground="red")
        self.widget.tag_config("CRITICAL", foreground="red", underline=1)

    def emit(self, record):
        msg = self.format(record)

        def append():
            self.widget.configure(state='normal')
            self.widget.insert(END, msg + '\n', record.levelname)
            self.widget.configure(state='disabled')
            # Autoscroll to the bottom
            self.widget.yview(END)

        # This is necessary because we can't modify the Text from other threads
        self.widget.after(0, append)


class MainGui:
    """Display the Main GUI Window"""

    def init_logging_textarea(self, window):
        # Textarea for Log File display
        master_right = ttk.Frame(window, padding=(3, 3, 12, 12))
        master_right.grid(column=1, row=0, sticky=(N, S, E, W))
        self.info_box = scrolledtext.ScrolledText(master_right, state='disabled')
        self.info_box.configure(font='TkFixedFont')
        self.info_box.grid(row=0, column=0, sticky=(N, S, E, W))

        # Create textLogger
        text_handler = LoggingTextHandler(self.info_box)

        # Add the handler to logger
        logger = logging.getLogger()
        logger.addHandler(text_handler)

    def __init__(self, window):
        master = ttk.Frame(window, padding=(20, 30, 12, 12), borderwidth=10)
        master.grid(column=0, row=0, sticky=(N, S, E, W))

        self.master = master
        window.title("DKAN Uploader")

        self.init_logging_textarea(window)

        logging.info("DKAN Uploader v0.1")
        logging.info("==================")
        logging.debug("Filename %s", config.excel_filename)

        # -- Main layout --
        currentRow = 0
        y_spacing = 10

        # Headline
        headline_label = Label(master, text="DKAN Uploader", font=("Arial Bold", 30))
        headline_label.grid(row=0, columnspan=3)

        # Filename input
        currentRow += 1
        vcmd = master.register(self.validate)   # we have to wrap the command
        self.filename_input = Entry(master, validate="key", validatecommand=(vcmd, '%P'))
        self.filename_input.delete(0, END)
        self.filename_input.insert(0, config.excel_filename)
        self.filename_input.grid(row=currentRow, column=1, columnspan=2, sticky=W+E, pady=(y_spacing, y_spacing))
        self.filename_label = Label(master, text="Excel-Filename:")
        self.filename_label.grid(row=currentRow, column=0, sticky=E, pady=(y_spacing, y_spacing))

        currentRow += 1
        self.url_input = Entry(master, validate="key", validatecommand=(vcmd, '%P'))
        self.url_input.delete(0, END)
        self.url_input.insert(0, config.dkan_url)
        self.url_input.grid(row=currentRow, column=1, columnspan=2, sticky=W+E)
        self.url_label = Label(master, text="DKAN-Url:")
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

        self.cred_label = Label(master, text="User/Password:")
        self.cred_label.grid(row=currentRow, column=0, sticky=E)

        # Last row (Buttons)
        currentRow += 1

        aktion_label = Label(master, text="Aktion:")
        aktion_label.grid(row=currentRow, column=0, sticky=E, pady=(y_spacing, 0))
        self.upload_button = Button(master, text="Excel -> DKAN", command=self.action_upload)
        self.upload_button.grid(row=currentRow, column=1, sticky=W+E, pady=(y_spacing, 0))
        self.download_button = Button(master, text="DKAN -> Excel", command=self.action_download)
        self.download_button.grid(row=currentRow, column=2, sticky=W+E, pady=(y_spacing, 0))

    def update_config(self):
        config.dkan_url = self.url_input.get()
        config.dkan_username = self.user_input.get()
        config.dkan_password = self.password_input.get()
        config.excel_filename = self.filename_input.get()

    def validate(self, new_text):
        logging.debug("There could be a validation here")
        return True

    def action_download(self):
        self.update_config()
        logging.debug("Starting Excelwriter module")
        self.download_button.configure(state=DISABLED)
        excelwriter.write()
        self.download_button.configure(state=NORMAL)

    def action_upload(self):
        self.update_config()
        logging.debug("Starting Excelreader module")
        self.upload_button.configure(state=DISABLED)
        excelreader.read()
        self.upload_button.configure(state=NORMAL)


def show():
    root = Tk()
    MainGui(root)
    root.mainloop()
