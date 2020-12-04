"""Main source file for global config
"""

dkan_url = ""
dkan_username = ""
dkan_password = ""
excel_filename = ""

skip_resources = False
check_resources = False

api_package_details = "" ## TODO: DO WE NEED THIS? WE USE api_node_details INSTEAD, woll?
api_resource_list = ""
api_encoding = "utf-8"

# ------------------------------------------------------------------------
# Internal settings, only change below here if you know what you are doing
# ------------------------------------------------------------------------

api_find_node_id = "/api/dataset/node.json?parameters[uuid]={}"
api_get_node_details = "/api/dataset/node/{}.json"

download_extended_dataset_infos = True
