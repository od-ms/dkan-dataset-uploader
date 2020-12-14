"""Main source file for global config
"""

dkan_url = ""
dkan_username = ""
dkan_password = ""
excel_filename = ""

# features
skip_resources = False
check_resources = False

# endpoint is used to fetch single packages by id
api_package_details = "/api/3/action/package_show?id=" 
# endpoint is used to fetch list of (all) packages
api_resource_list = "/api/3/action/current_package_list_with_resources?limit=10"  
api_encoding = "utf-8"

# command line options
overwrite_rows = False
dataset_ids = ""

# ------------------------------------------------------------------------
# Internal settings, only change below here if you know what you are doing
# ------------------------------------------------------------------------

api_find_node_id = "/api/dataset/node.json?parameters[uuid]={}"
api_get_node_details = "/api/dataset/node/{}.json"

download_extended_dataset_infos = True
