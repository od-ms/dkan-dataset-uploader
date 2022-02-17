"""Main source file for global config
"""

dkan_url = ""
dkan_username = ""
dkan_password = ""
excel_filename = ""
download_dir = ""

# features
skip_resources = False
check_resources = False
detailed_resources = False
resources_download = False

# endpoint is used to fetch single packages by id
api_package_details = "/api/3/action/package_show?id="
# endpoint is used to fetch list of (all) packages
api_resource_list = "/api/3/action/current_package_list_with_resources?limit=10000"
api_encoding = "utf-8"

# command line options
overwrite_rows = False
dataset_ids = ""
message_level = "Debug"
force_resource_update = False

# ------------------------------------------------------------------------
# Internal settings, only change below here if you know what you are doing
# ------------------------------------------------------------------------

x_api_find_node_id = "/api/dataset/node.json?parameters[uuid]={}"
x_api_get_node_details = "/api/dataset/node/{}.json?cachebuster={}"

x_download_extended_dataset_infos = True
x_temp_dir = 'temp/'
x_log_dir = 'logs/'

# these paths will be used to detect resource types "datastore" and "uploaded_file" in fast mode
x_uploaded_resource_path = '/sites/default/files/'
x_uploaded_datastore_path = '/api/action/datastore/'

x_dataset_ids_temp = ""