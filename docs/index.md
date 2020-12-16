# Dokumentation der Software "DKAN-Uploader"

Mit *DKAN-Uploader* können Sie die Metadaten in einer Instanz der Open-Data-Portal-Software "DKAN" (https://getdkan.org/) verwalten.

Programmfunktionen:
* Alle Metadaten der Datensätze und Ressourcen aus den DKAN-Open-Data-Portal in eine Excel-Datei exportieren
* Die (externen) Links aller Ressourcen überprüfen
* Die Metadaten verschiedener Datensätze gleichzeitig bearbeiten indem Sie diese aus einer lokalen Excel-Datei überschreiben
* Neue Datensätze anlegen anhand der Informationen aus einer lokalen Excel-Datei

Es handelt sich um eine in der Programmiersprache Python entwickelte Anwendung. Diese kann über eine grafische Windows- oder Linux-Benutzeroberfläche bedient werden. Ebenso wird eine Ausführung über die Kommandozeile unterstützt.



# Programmstart der grafischen Benutzeroberfläche

**Unter Linux**

Führen Sie zum Starten der grafischen Bedienoberfläche folgende Befehle aus:

```
git clone https://github.com/od-ms/dkan-dataset-uploader.git
cd dkan-dataset-uploader
pip3 install -r requirements.txt
python3 -m dkan-uploader
```

## Aufbau der grafischen Benutzeroberfläche

Die grafische Benutzeroberfläche ist folgendermaßen aufgebaut:

**Fenster für Logmeldungen**\
Auf der rechten Seite des Anwendungsfensters sehen sie ein großes Textfeld, in dem Logmeldungen angezeigt werden. Während der Bedienung der Anwendung erscheinen darin Informationen zu den letzten ausgeführten Aktionen und zu eventuell aufgetretenen Fehlern.

**Aktionsflächen**\
Auf der linken Seite des Anwendungsfensters befinden sich Input-Felder für verschiedene Konfigurationseinstellungen, sowie Radioboxen und Buttons zum Ausführen der Programmfunktionen.

## Bedienung der Benutzeroberfläche

**Vor dem ersten Start**\
Tragen Sie die URL des DKAN-Portals sowie Benutzernamen und Passwort in die entsprechenden Felder ein auf der linken Seite des Anwendungsfensters ein.

Diese Konfiguration wird beim Aufruf einer Aktion automatisch in einer Datei *config.ini* im Anwendungsverzeichnis gespeichert und steht beim nächsten Start der Anwendung wieder zur Verfügung.

### Export von Datensatz- und Ressourcen-Informationen aus dem DKAN in eine Excel-Datei

Um alle Daten aus dem DKAN in eine Excel-Datei zu exportieren, klicken Sie auf den Button **"DKAN->Excel"**.

Außerdem können Sie folgende Optionen einstellen:
 * Checkbox *"Nur Datensätze, keine Ressourcen"*: Wenn diese Checkbox ausgewählt ist, werden nur die Metainformationen der Datensätze, nicht aber die Informationen zu den zugehörigen Ressourcen ausgelesen
 * Checkbox *"Ressourcen beim Download überprüfen"*: Wenn dies angehakt ist, werden alle externen Ressourcen-Urls ihres Open-Data-Portals geprüft, und das Ergebnis wird in der Excel-Datei vermerkt. Somit können Sie sehen, ob die Links auf externe Ressourcen-Dateien noch funktionieren. Ihr Computer wird dann versuchen, jede Ressourcen-URL per HTTP-HEAD-Request abzurufen, um festzustellen, ob der Link noch funktioniert. Der Abruf der Daten dauert dadurch deutlich länger.

### Aufbau der Excel-Datei

Die erzeugte Excel-Datei hat den folgenden Aufbau:

 * Jede Spalte entspricht einem Datenfeld aus dem DKAN. Z.B. gibt es Spalten für "Datensatz-Titel", "Autor", "Kategorie", etc.
 * Die Spalten-Titel geben an, um welches Datenfeld es sich handelt. Unbekannte Spalten-Titel werden vom
 * DKAN-Uploader ignoriert.
 * Die ersten Spalten enthalten Informationen zu den Datensätzen. Das sind ungefähr die Spalten A-AF (abhängig davon, wie viele individuelle "Extra"-Felder sie im DKAN angelegt haben)
 * In den hinteren Spalten ab der Spalte "Resource-ID" stehen die Datenfelder von Ressourcen. Ressourcen sind die zu Datensätzen hinterlegten Dateien oder Links. Ein Datensatz kann immer mehrere Ressourcen haben, und Ressourcen müssen immer zu genau einem Datensatz gehören.
 * Jede Zeile, in der die ersten Spalten ausgefüllt sind, entspricht einem Datensatz
 * Jede Zeile, in denen die hinteren Spalten ab "Resource-ID" ausgefüllt sind, entsprechen einer Ressource.
 * In einer Zeile kann auch beides enthalten sein, das ist meist in der ersten Zeile eines Datensatzes der Fall.
 * Es werden in der Excel-Datei automatisch Spalten-"Gruppen" erzeugt, so dass man unbenötigte Spalten ausblenden kann und die Übersichtlichkeit gewahrt bleibt. Um Spalten ein- und auszuklappen klicken Sie in Ihrem Office-Programm (z.B. Excel oder LibreOffice) auf das entsprechende Plus- bzw. Minus-Zeichen über der ersten Zeile. Beim schreiben aus einer Excel-Datei in ein DKAN-Portal werden immer alle Spalten geschrieben, egal ob sie im Excel eingeklappt sind oder nicht.

### Schreiben von Daten in die DKAN-Instanz

💣Achtung! Mit dieser Funktion werden Daten in der DKAN-Instanz überschrieben. Sie können alle Metadaten in Ihrem Open-Data-Portal verändern und bei falscher Bedienung alle Datensätze überschreiben.💣

**Start**\
Klicken Sie dazu auf den Button **"Excel->DKAN"**.

Dann werden alle Einträge aus der Excel-Datei Zeile für Zeile abgearbeitet und in das DKAN-Portal übertragen.

Dabei gelten folgende Regeln:

* Jede Zeile der Excel-Datei erzeugt im DKAN-Portal einen Datensatz oder eine Ressource.
* Eine Zeile mit einer Datensatz-ID in der ersten Spalte überschreibt den entsprechenden Datensatz im DKAN-Portal. Wird kein Datensatz mit der ID gefunden, wird eine Warnung ausgegeben und mit der nächsten Zeile wird fortgefahren.

# Bedienung der Software über die Kommandozeile

Mit folgendem Befehl können Sie die Software im Kommandozeilen-Modus starten:
```
python3 -m dkan-uploader -h
```

Die Bedienungsanleitung für den Kommandozeilenmodus und die unterschiedlichen verfügbaren Kommandozeilenparameter werden dann über die Kommandozeile ausgegeben.

# Hilfe bei Problemen

## Liste der Fehlermeldungen

* ```Fehler 5001```: Die DKAN-API hat nicht im JSON-Format geantwortet.\
Häufig hat das einen der folgenden Gründe:
  * Ein Eingabeparameter für die DKAN-API hat nicht das erwartete Format. \
  *Lösung:* Wenn dies beim Upload auftritt, sind eventuell  in der Excel-Datei nicht alle benötigten Spalten korrekt ausgefüllt. Füllen Sie alle Spalten aus.
  * Das API-Format hat sich geändert. Tritt z.B. auf, wenn Sie eine zu dieser Software inkompatible DKAN-Version nutzen. \
  *Lösung:* Prüfen Sie die Version der von Ihnen verwendete DKAN-Version und gleichen Sie diese mit der vom Programm unterstützten Version ab. Wenn die Versionen inkompatibel sind, lassen Sie diese Software auf die neuere DKAN-Version anpassen, oder passen Sie selbst den Programmcode an, der die API anspricht.

## Nicht unterstützte Datenfelder

 Folgende Felder von DKAN-Datensätzen werden nicht vom DKAN-Uploader unterstützt, d.h. sie können nicht ausgelesen oder geschrieben werden:
 * Harvest Source
 * Alle "Playground"-Felder

## Bekannte, aber derzeit ungelöste Probleme

* **Stichworte**: Es scheint über die DKAN-API für die "Stichworte" ("dataset_tags") **keine** Möglichkeit zu geben, eine Zuordnung zwischen IDs und Namen herauszufinden. Mit folgendem Link kann man zwar eine Liste der Stichworte bekommen, aber ohne IDs: https://opendata.stadt-muenster.de/autocomplete_deluxe/taxonomy/field_dataset_tags/%20/500?term=&synonyms=2 Da die API aber nur Stichwort-IDs zurück gibt, ist die Folge, dass man Stichworte in der Excel-Datei nur über IDs angeben kann.
