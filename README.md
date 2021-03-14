# dkan-dataset-uploader
A tool to upload or download multiple datasets and resources from or to a DKAN open data portal instance via excel sheets.

Detailled program documentation (in german language) is provided in the folder ```docs```.

## Usage

```bash
    # Start client in interactive GUI window mode
    python3 -m DkanRemote
    # Alternative way to run it: python dkanuploader.py

    # Start client in console mode and list all command line options
    python3 -m DkanRemote -h

    # Example: Download DKAN content into filename.xlsx
    # (Additionally you need to set DKAN access credentials in config.ini)
    python3 -m DkanRemote filename.xlsx --download
```

## Setup

Install required packages:

```bash
    python3 -m venv venv # (optional: Create virtual environment)

    pip3 install -r requirements.txt

    ''' (If you get an error with installing pydkan, e.g. the following error "ModuleNotFoundError: No module named dkan", then use the install instructions from here: https://github.com/GetDKAN/pydkan) '''
```

## Configuration

 1. Copy file config.ini.dist to config.ini
 2. Add your configuration details to config.ini

**Htaccess** - If your DKAN Portal has htaccess protection, use this format for the _dkan_url_:

    dkan_url = "https://user:password@dkan-portal.url"

**Proxy** - If you are behind a proxy, change the file *site-packages/dkan/client.py*
and add the following code in the method "requests" after the line "s = requests.Session()":

    s.proxies =  {
      'http': 'http://proxy.some:8080',
      'https': 'http://proxy.other:8080',
    }

## Debug

DKAN's dataset API frequently changes. Unexpected responses are a common problem.

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