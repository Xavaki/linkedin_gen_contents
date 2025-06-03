#!/usr/bin/env python
# coding: utf-8

# In[26]:


from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv
import os
import json


# In[4]:


load_dotenv('./CLOUD_PIPELINE/.env')


# In[5]:


connection_string = os.getenv('STORAGE_ACCOUNT_CONNECTION_STRING')
blob_service_client = BlobServiceClient.from_connection_string(connection_string)


# In[ ]:


# for x in os.listdir('LOCAL_PIPELINE/local_tests_data/'):
#     if x == 'azure_openai_batch_processing_files':
#         continue

#     if x == 'sources':
#         continue

#     if x == 'past_posts':
#         continue

#     if x != 'source_raw_content':
#         continue

#     container_name = x.replace("_", "-")
#     container = blob_service_client.get_container_client(container_name)
#     assert container.exists(), f"Container {container_name} does not exist."

#     for xx in os.listdir(f'LOCAL_PIPELINE/local_tests_data/{x}'):

#         runid  = xx

#         runid_data = []

#         for xxx in os.listdir(f'LOCAL_PIPELINE/local_tests_data/{x}/{xx}'):
#             print(xxx)

#             with open(f'LOCAL_PIPELINE/local_tests_data/{x}/{xx}/{xxx}', 'r') as file:
#                 data = json.load(file)
#                 runid_data.append(data)

#         upload_blob_name = f"{runid}--{x}.json"
#         blob_client = container.get_blob_client(upload_blob_name)
#         blob_client.upload_blob(json.dumps(runid_data, indent=4), overwrite=True)


# In[ ]:




