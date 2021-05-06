# DKAN Dataset Uploader

Dieses Repository enthält den Quellcode der Software "DKAN-Uploader" sowie ausführbare Binärdateien für Windows.

Mit **DKAN-Uploader** können Sie die Dateien und Metadaten  einer Instanz der Open-Data-Portal-Software DKAN (https://getdkan.org/) verwalten (z.B. exportieren und importieren).


---

🇬🇧 Information about this repository in english language is provided in the file ["README.en.md"](README.en.md)

---

## Programmfunktionen

* Alle Metadaten der Datensätze und Ressourcen aus den DKAN-Open-Data-Portal in eine Excel-Datei exportieren.
* Die (externen) Links aller Ressourcen überprüfen.
* Die Metadaten verschiedener Datensätze gleichzeitig bearbeiten indem Sie diese aus einer lokalen Excel-Datei überschreiben.
* Neue Datensätze anlegen anhand der Informationen aus einer lokalen Excel-Datei.

Es handelt sich um eine in der Programmiersprache Python entwickelte Anwendung. Diese kann über eine grafische Windows- oder Linux-Benutzeroberfläche bedient werden. Ebenso wird eine Ausführung über die Kommandozeile unterstützt.

# Dokumentation
Eine detaillierte Dokumentation der grafischen Benutzeroberfläche sowie Details zu der vom Programm erzeugten Excel-Datei finden Sie im Ordner [docs](docs/index.md).


# Installation

## Installation unter Windows

1. Laden Sie die aktuelle Binärversion unter aus Github-Repository herunter:
https://github.com/od-ms/dkan-dataset-uploader/releases

2. Verschieben Sie die heruntergeladene Datei an einen Ort Ihrer Wahl (z.B. Desktop)

3. Führen Sie die Datei aus durch einen Doppelklick. Es öffnet sich die grafische Benutzeroberfläche.

**Hinweis:**\
Die Datei wurde mit Python2Exe erstellt. Leider gibt es einige bekannte Probleme damit, u.A. dass Windows die heruntergeladene Exe-Datei für schädlich hält.
Sie müssen daher nach dem Herunterladen und nach dem Doppelklicken auf die Datei in verschiedenen Windows-Dialogen bestätigen, dass Sie das Programm für sicher halten. Das müssen Sie zum Glück nur beim ersten Start tun.

Falls Ihnen das zu risikoreich erscheint, können Sie statt der Binärdatei auch den Programm-Quellcode mit einem Python-Interpreter ausführen. Dazu benötigen Sie Python auf Ihrem System. Informationen zur Installation erhalten sie hier: https://docs.python.org/3/using/windows.html

Sobald  Python auf Ihrem Windows-System verfügbar ist, gehen Sie zum Installieren und Starten von DKAN-Uploader wie unter Linux vor. Das wird im Folgenden beschrieben.

## Installation unter Linux

Vorausgesetzt wird eine bestehende Installation von python3 in der Version ab python3.5, sowie von "git".

Führen Sie die folgenden Befehle aus zum Herunterladen des Git-Repositories und zum Installieren der benötigten Python-Pakete in ein virtuelles environment:

```bash
  git clone https://github.com/od-ms/dkan-dataset-uploader.git
  cd dkan-dataset-uploader

  # Optional: Erstellen Sie ein virtuelles environment
  python3 -m venv venv

  pip3 install -r requirements.txt

  # Hinweis: Falls ein Fehler beim Installieren von pydkan auftritt,
  # installieren Sie pydkan bitte nach der folgenden Installationsanleitung:
  # https://github.com/GetDKAN/pydkan
```

### Start unter Linux
Wechseln Sie in das Anwendungsverzeichnis und führen Sie folgende Befehle aus:

**Starten der grafischen Benutzeroberfläche**
```bash
    # Optional: aktivieren Sie das virtuelle environment
    source venv/bin/activate

    python3 -m dkan-uploader
```

**Starten der Kommandozeilenversion**
```bash
    # Anwendung im Konsolen-Modus ausführen
    # und die verfügbaren Befehle anzeigen
    python3 -m dkan-uploader -h

    # Beispiel: Die Metadaten der DKAN-Instanz auslesen in die Datei "filename.xlsx"
    # (Die DKAN-Zugangsdaten DKAN access credentials in config.ini)
    python3 -m dkan-uploader filename.xlsx --download
```


## Konfiguration


### Konfiguration über die GUI
Sie können die Konfiguration der notwendigen Einstellungen des Programms über die grafische Benutzeroberfläche durchführen. Tragen Sie dort Ihre DKAN-Zugangdaten und URLs ein. Beim Beenden wird die Konfiguration automatisch in der Datei "config.ini" gespeichert. Diese Konfiguration wird dann bei jedem weiteren Programmstart verwendet, sowohl in der grafischen Benutzeroberfläche als auch beim Start über die Kommandozeile.

### Manuelles Erstellen der Konfigurationsdatei

 1. Kopieren Sie die Datei *config.ini.dist* und benennen Sie die Kopie *config.ini*
 2. Füllen Sie mindestens die folgenden Konfigurationsinformationen in der *config.ini* aus:

```yaml
dkan_url = URL zum DKAN, z.B. https://opendata.port.al
username = Benutzernamne für Dkan
password = Passwort zum Benutzernamen
```

#### Erweiterte Konfiguration
**Htaccess** - Falls das DKAN Portal einen htaccess-Schutz hat, nutzen Sie das folgende Format für _dkan_url_:
[Konfigurationsdatei](config.ini.dist)

    dkan_url = "https://user:password@dkan-portal.url"

**Proxy** - If you are behind a proxy, change the file *site-packages/dkan/client.py*
and add the following code in the method "requests" after the line "s = requests.Session()":

    s.proxies =  {
      'http': 'http://proxy.some:8080',
      'https': 'http://proxy.other:8080',
    }

## Debug

DKAN's dataset API changes frequently. Unexpected responses are a common problem.

1. Enable debug option of pydkan: Set last prameter of pydkan instantiation to true (see dkanhandler->function "connect")
2. Check the log output for the last HTTP request that pydkan sent to DKAN API (probably a POST or PUT request)
3. Use your favorite browser extension to manually send the same request
4. remove fields from json POST BODY content one by one until response is OK
5. Now you identified the json content that produced the error. Fix it by trial and error


## Python learning resources

* **Python cheat sheet** https://www.pythoncheatsheet.org/
* **Python example project setup** https://github.com/navdeep-G/samplemod
* **Github actions for python**: https://docs.github.com/en/actions/language-and-framework-guides/using-python-with-github-actions
* **Create a windows executable file with pyinstaller**: https://realpython.com/pyinstaller-python/