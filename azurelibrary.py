# AZURE RESTFUL API ENDPOINTS Library
# Author: sguign@celestica.com
# Operator:
# Admin:
# Version: 1
# August 10, 2020

import yaml
import requests as req
import datetime
import itertools
# from google.cloud import storage


# Read in current  configurations
config_path = "azure_consumption_reporting-credentials.yaml"

# Read in current configurations
with open(config_path) as stream:
	config = yaml.safe_load(stream)

def last_day_of_month(date):
    if date.month == 12:
        return date.replace(day=31)
    return date.replace(month=date.month+1, day=1) - datetime.timedelta(days=1)


def bearerToken(tenant):
	url = config['EndPoints']['Login'] + config[tenant]['tenant_id'] + "/oauth2/token?api-version=1.0"
	head = {
		"Content-Type": "application/x-www-form-urlencoded"
	}
	data = {
		"grant_type": "client_credentials",
		"client_id": config[tenant]['client_id'],
		"client_secret": config[tenant]['client_secret'],
		"resource": config['EndPoints']['Management']
	}
	response = req.post(url, data=data, headers=head)
	print("Bearer Token Collected: {}".format(response.status_code))
	config[tenant]['OAuth2Token'] = response.json()
	return response

# Create an array of all subscriptions available to AO before pulling from each
def listSubscriptions(tenant):
	url = config['EndPoints']['Management']+"/subscriptions/?api-version=2016-06-01"
	head = {
		"Authorization": "Bearer " + config[tenant]['OAuth2Token']['access_token'],
		"Content-type": "application/json",
		"Host": "management.azure.com"
	}
	response = req.get(url, headers=head)
	config['Subscriptions'] = response.json()['value']
	return response



def usageDetails(tenant, invoice_month, subscription_id):
	subscriptionUsage = [] # Value to hold new subscription usage data
	isMore = False # Default value for pagination. True if API response contains "nextLink" URL

	startDate = datetime.datetime.strptime(invoice_month, "%Y%m") # Calculate period start date
	endDate = last_day_of_month(startDate) # Calculate period end date

	# Build API request URL
	url = config['EndPoints']['Management']+"subscriptions/{}/providers/Microsoft.Consumption/usageDetails?startDate={}&endDate={}&$top=1000&api-version=2021-10-01".format(subscription_id, startDate, endDate)
	
	# Define API hequest header
	head = {
		"Authorization": "Bearer " + config[tenant]['OAuth2Token']['access_token']
	}

	# Make cURL call to API Endpoint
	resp = req.get(url, headers=head)
	
	# if API response has any data: 
	if len(resp.json()['value'])>0:
		
		# if response contains kind "legacy" send to legacy api and overwrite initial response with legacy response
		if resp.json()['value'][0]['kind'] == "legacy":
			return list(itertools.chain.from_iterable(subscriptionUsage))
		
	# If "nexLink" in response change flip pagenation boolean.
	if "nextLink" in resp.json():
		isMore = True
	
		
	while isMore:
		# Append usage to subscription usage report
		subscriptionUsage.append(resp.json()['value'])
		
		resp = req.get(resp.json()['nextLink'], headers=head)
		# If there is there is more data to collect, set is more to True
		if "nextLink" in resp.json():
			isMore = True
			
		# Else break loop
		else:
			isMore = False
			subscriptionUsage.append(resp.json()['value'])
			break
	# return list(itertools.chain.from_iterable(subscriptionUsage))
	return list(itertools.chain.from_iterable(subscriptionUsage))

# Validate the values of tags on resource before submitting to database
def validate_tags(resource):
	# Checks workloads for legacy tags and converts them
	legacy_tags = {
		'applicationname': 'application_name', 
		'applicationowner': 'primary_owner_email',
		'applicationownercuk' : 'primary_owner_cuk',
		'costcenter': 'cost_center',
		'environment': 'environment',
		'servicetype': 'service_type',
		'applicationtype': 'application_type',
		'resourceclusterid': 'resource_cluster_id',
		'source': 'source'
	}
	
	# Check mandetory tags against list of required tags
	required_tags = [
		'application_name',
		'primary_owner_email',
		'primary_owner_cuk',
		'cost_center',
		'resource_cluster_id',
		'environment',
		'source',
		'next_validation'
	]
	
	# Perform Validation on resource tags
	validated_tags = {}
	
	# Validate tags which are not case compliant
	resource_keys = resource['tags'].keys()
	
	for resource_tag_key in resource_keys:
		if resource_tag_key.lower() in required_tags:
			validated_tags[resource_tag_key.lower()] = resource['tags'][resource_tag_key].lower()
		elif resource_tag_key.lower() in legacy_tags.keys():
			validated_tags[legacy_tags[resource_tag_key.lower()]] = resource['tags'][resource_tag_key].lower()
		elif resource_tag_key.lower() not in required_tags:
			# print("Adding custom tag to resource object")
			validated_tags[resource_tag_key.lower()] = resource['tags'][resource_tag_key].lower()
	
	# Monitor to ensure that all mandatory tags are present on resource
	for required_tag in required_tags:
		if required_tag not in resource_keys:
			validated_tags[required_tag] = ""
			resource['error'] = "Missing '"+str(required_tag)+"' in resource tags" 
			# print(resource['error'])
			#noncompliant.append(resource)
	return validated_tags



def upload_blob(source_file_name):
    """Uploads a file to the bucket."""
    # The ID of your GCS bucket
    bucket_name = "celestica-cloud-usage"
    # The path to your file to upload
    # source_file_name = "local/path/to/file"
    # The ID of your GCS object
    # destination_blob_name = "storage-object-name"

    # storage_client = storage.Client.from_service_account_json('/path/to/SA_key.json')
    # bucket = storage_client.bucket(bucket_name)
    # blob = bucket.blob(source_file_name)

    # blob.upload_from_filename(source_file_name)

    # print(
    #     f"File {source_file_name} uploaded to {source_file_name}."
    # )

def export_usage(jsonData):
	f = open("{} ({}).json".format(timestamp, invoice_month), "a")
	f.write(json.dumps(jsonData+"\n"))
	f.close()


# https://learn.microsoft.com/en-us/azure/cost-management-billing/manage/consumption-api-overview#reservation-details-api
