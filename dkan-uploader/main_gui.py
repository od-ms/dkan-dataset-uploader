import random
from tkinter import Tk, Label, Button, Entry, StringVar, Text, DISABLED, INSERT, NORMAL, END, N, S, W, E
from tkinter import ttk
from . import excelreader

class MainGui:
    def __init__(self, window):
        master = ttk.Frame(window, padding=(20,30,12,12))
        master.grid(column=0, row=0, sticky=(N, S, E, W))

        self.master = master
        window.title("DKAN Uploader")

        # -- Main layout --

        currentRow = 0
        y_spacing = 10

        print("row" )

        # Headline
        headline_label = Label(master, text="DKAN Uploader", font=("Arial Bold", 30))
        headline_label.grid(row=0, columnspan=3)

        # Filename input
        currentRow += 1
        vcmd = master.register(self.validate) # we have to wrap the command
        self.filename_input = Entry(master, validate="key", validatecommand=(vcmd, '%P'))
        self.filename_input.grid(row=currentRow, column=1, columnspan=2, sticky=W+E, pady=(y_spacing, y_spacing))
        self.filename_label = Label(master, text="Excel-Filename:")
        self.filename_label.grid(row=currentRow, column=0, sticky=E, pady=(y_spacing, y_spacing))


        currentRow += 1
        self.url_input = Entry(master, validate="key", validatecommand=(vcmd, '%P'))
        self.url_input.grid(row=currentRow, column=1, columnspan=2, sticky=W+E)
        self.url_label = Label(master, text="DKAN-Url:")
        self.url_label.grid(row=currentRow, column=0, sticky=E)

        # cDKAN redentials
        currentRow += 1
        self.user_input = Entry(master)
        self.user_input.grid(row=currentRow, column=1,  sticky=W+E)
        self.user_input = Entry(master, show="*")
        self.user_input.grid(row=currentRow, column=2, sticky=W+E)
        self.cred_label = Label(master, text="User/Password:")
        self.cred_label.grid(row=currentRow, column=0, sticky=E)

        # Last row (Buttons)
        currentRow += 1

        aktion_label = Label(master, text="Aktion:")
        aktion_label.grid(row=currentRow, column=0, sticky=E, pady=(y_spacing, 0))
        self.upload_button = Button(master, text="Excel -> DKAN", command=self.action_upload)
        self.upload_button.grid(row=currentRow, column=1, sticky=W+E, pady=(y_spacing, 0))
        self.download_button = Button(master, text="DKAN -> Excel", command=self.action_download, state=DISABLED)
        self.download_button.grid(row=currentRow, column=2, sticky=W+E, pady=(y_spacing, 0))

        # Log File field
        master_right = ttk.Frame(window, padding=(3, 3, 12, 12))
        master_right.grid(column=1, row=0, sticky=(N, S, E, W))
        self.info_box = Text(master_right)
        self.info_box.insert(INSERT, "Logfenster mit Logausgaben\n")
        self.info_box.insert(INSERT, "==========================\n\n")
        self.info_box.insert(END, "Hello!\n")
        self.info_box.config(state=DISABLED)
        self.info_box.grid(row=0, column=0, sticky=(N, S, E, W))

        # Add something to log field
        self.info_box.config(state=NORMAL)
        #self.info_box.delete(1.0, END)
        self.info_box.insert(END, "Bye bye! ..... ... \n")
        self.info_box.config(state=DISABLED)



    def validate(self, new_text):
        if not new_text: # the field is being cleared
            self.guess = None
            return True

        try:
            guess = int(new_text)
            if 1 <= guess <= 100:
                self.guess = guess
                return True
            else:
                return False
        except ValueError:
            return False

    def action_download(self):
        self.num_guesses += 1

        if self.guess is None:
            self.message = "Guess a number from 1 to 100"

        elif self.guess == self.secret_number:
            suffix = '' if self.num_guesses == 1 else 'es'
            self.message = "Congratulations! You guessed the number after %d guess%s." % (self.num_guesses, suffix)
            self.download_button.configure(state=DISABLED)
            self.upload_button.configure(state=NORMAL)

        elif self.guess < self.secret_number:
            self.message = "Too low! Guess again!"
        else:
            self.message = "Too high! Guess again!"

        # self.label_text.set(self.message)

    def action_upload(self):
        # self.entry.delete(0, END)

        excelreader.read()

        self.download_button.configure(state=NORMAL)
        self.upload_button.configure(state=DISABLED)

def show():
    root = Tk()
    my_gui = MainGui(root)
    root.mainloop()