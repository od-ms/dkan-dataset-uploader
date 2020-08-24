import random
from tkinter import Tk, Label, Button, Entry, StringVar, DISABLED, NORMAL, END, N, S, W, E
from tkinter import ttk


class GuessingGame:
    def __init__(self, window):
        master = ttk.Frame(window, padding=(3,3,12,12))
        master.grid(column=0, row=0, sticky=(N, S, E, W))

        self.master = master
        window.title("DKAN Uploader")

        # -- Main layout --

        # Headline
        headline_label = Label(master, text="DKAN Uploader", font=("Arial Bold", 30))
        headline_label.grid(row=0, columnspan=3)

        # Url input
        vcmd = master.register(self.validate) # we have to wrap the command
        self.url_input = Entry(master, validate="key", validatecommand=(vcmd, '%P'))
        self.url_input.grid(row=1, column=1, columnspan=2, sticky=W+E)
        self.url_label = Label(master, text="DKAN-Url:")
        self.url_label.grid(row=1, column=0, sticky=W+E)

        # #filename input
        vcmd = master.register(self.validate) # we have to wrap the command
        self.url_input = Entry(master, validate="key", validatecommand=(vcmd, '%P'))
        self.url_input.grid(row=1, column=1, columnspan=2, sticky=W+E)
        self.url_label = Label(master, text="DKAN-Url:")
        self.url_label.grid(row=1, column=0, sticky=W+E)

        #credentials

        # logoutput

        
        # DKAN 

        # Log File field

        # Last row (Buttons)
        aktion_label = Label(master, text="Aktion:")
        aktion_label.grid(row=2, column=0)
        self.upload_button = Button(master, text="Excel -> DKAN", command=self.action_upload)
        self.upload_button.grid(row=2, column=1, sticky=W+E)
        self.download_button = Button(master, text="DKAN -> Excel", command=self.action_download, state=DISABLED)
        self.download_button.grid(row=2, column=2, sticky=W+E)



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
        self.secret_number = random.randint(1, 100)
        self.guess = 0
        self.num_guesses = 0

        self.message = "Guess a number from 1 to 100"
        # self.label_text.set(self.message)

        self.download_button.configure(state=NORMAL)
        self.upload_button.configure(state=DISABLED)

root = Tk()
my_gui = GuessingGame(root)
root.mainloop()