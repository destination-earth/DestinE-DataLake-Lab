import os

print("##### test5_script_inject.py #####")
print("Hello from Kubernetes Python pod!")

##########################################################
#### Get DESP Credentials                  ###############
##########################################################

username = os.environ.get("DESP_USERNAME")
print("DESP_USERNAME:", username)
