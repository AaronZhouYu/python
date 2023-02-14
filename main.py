# Start StopWatch
import time
start = time.perf_counter() # start timer


# Import System Libraries
from datetime import datetime
import json
import yaml
import sys
from dateutil.relativedelta import relativedelta

# Import Custom Libraries
import azurelibrary as azure_api
import send_grid
import db


# Define variables
timestamp = str(datetime.now().strftime("%Y-%m-%d"))
invoice_month = str(datetime.now().strftime("%Y%m"))
# invoice_month = "202209"
tenants = ['celestica', 'Viper']

CanSendEmails = True
attempts = 3

# Authenticate into Azure via Azure Reporting Bearer Token
# Each token provides access to specific Tenants
# Therefore, they will be named accordingly


for tenant in tenants:
	# Global Variables (Refreshed for each Tenant)
	TOKEN = ""
	RESOURCES = []


	# Collect bearer token from Azure Tenant
	try:	
		TOKEN = azure_api.bearerToken(tenant)
		print("Tenant '{}': {}".format(tenant, TOKEN.status_code))
	except Exception as e:
		print("Tenant Error '{}': {}".format(tenant, e))
		break
	
	# Retrieve list of all subscriptions available in AO
	print("Retrieve list of Subscriptions in {}".format(tenant))
	try: 
		subs = azure_api.listSubscriptions(tenant)
		subscriptions_list = subs.json()['value']
		print("{} Subscriptions for {}: {}".format(len(subscriptions_list), tenant, subs.status_code))

	except Exception as e:
		print("Subscriptions for {}: {}".format(tenant, e))


	# Get usage for all subscriptions in each Tenant
	print("Get all usage details for billing period {} ".format(invoice_month))

	# Collect usage from subscription(sub) in subscriptions list
	for sub in subscriptions_list:

		# values array buffer to store resource usage data before inserting into Mysql Database
		values=[] 
		index = 0

		# Retrieve the most recent usage details from Azure
		print("\nDownloading usage from "+ sub['displayName'] + ": "+sub['subscriptionId'])
		for attempt in range(attempts):
			try:

				# Collect resource data from Azure Subscription Account
				RESOURCES = azure_api.usageDetails(tenant, invoice_month, sub['subscriptionId'])
				
				# If data is not empty, log data collected and move onto next subscription
				if len(RESOURCES) != 0:
					print("Collected "+str(len(RESOURCES))+" resources from "+ sub['subscriptionId'] + " successfully")
					# Write resources to NDJSON file before submitting to GCP storage bucket
					
					break # from "attempts" for loop
				else:
					print("No resources consumption data found, politely asking them to check again {}/{}".format(attempt+1, attempts))
					continue # into appempts loop again
			except KeyError as msg:
				print("Missing or invalid tag key: " +str(msg))
				continue

		# Iterate through data collected and normalize data, validate tags, etc...
		for resource in RESOURCES:
			
			# Search resource for a key property called 'tags', if it doesn't exist create attribute for normalization of resource object
			props = resource['properties']
			if "resourceGroup" not in props: resource['properties']['resourceGroup'] = "unknown" # Resource Group
			if "subscriptionName" not in props: resource['properties']['subscriptionName'] = "unknown" # Billing Group
			if "consumedService" not in props: resource['properties']['consumedService'] = "unknown" # Type
			if "billingCurrency" not in props: resource['properties']['billingCurrencyCode'] = "unknown" # Currency
			if 'tags' not in resource or resource['tags'] is None:
				resource['tags'] = {
					'application_name': 'unclassified',
					'primary_owner_email': 'unclassified',
					'primary_owner_cuk': 'unclassified',
					'cost_center': 'unclassified',
					'resource_cluster_id': 'unclassified',
					'environment': 'unclassified',
					'source': 'unclassified',
					'next_validation': 'unclassified'
				}

			# Over write existing resource tags with validated ones
			resource['tags'] = azure_api.validate_tags(resource)
			

			# Append each resource to a file
			# azure_api.export_usage(resource)
			
			# Append a list of all resources to values array before performing an insert with multiple values
			try:
				if "costInBillingCurrency" in resource['properties']:
					# Defines last_modified
					last_modified = resource['properties']['date'].split("T")[0]

					# Append usage details to values array 
					values.append("""('{id}', 
						'{usage_date}', 
						'{invoice_month}', 
						'{resource_cluster_id}', 
						'{cloud_source_id}', 
						'{subscriptionName}', 
						'{resourceGroup}',  
						'{amount}',
						'{currency}',
						'{type}')""".format(
						id = resource['id']+"-"+last_modified, 
						usage_date = last_modified, 
						invoice_month = invoice_month,
						resource_cluster_id = resource['tags']['resource_cluster_id'],
						cloud_source_id = "8",
						subscriptionName = resource['properties']['subscriptionName'],
						resourceGroup = resource['properties']['resourceGroup'],
						amount = resource['properties']['costInBillingCurrency'],
						currency = resource['properties']['billingCurrencyCode'],
						type = resource['properties']['consumedService']
						)
					)
				else:
					# If "costInBillingCurrency" not in properties, append these values to array
					# 	This compensates for legacy api data that used to be returned when data was collected from EA and CSP
					values.append("""('{id}', 
						'{usage_date}', 
						'{invoice_month}',  
						'{resource_cluster_id}', 
						'{cloud_source_id}', 
						'{subscriptionName}', 
						'{resourceGroup}',
						'{amount}',
						'{currency}', 
						'{type}')""".format(
						id = resource['id']+"-"+last_modified,
						usage_date = last_modified, 
						invoice_month = invoice_month,
						resource_cluster_id = resource['tags']['resource_cluster_id'], 
						cloud_source_id = "8",
						subscriptionName = resource['properties']['subscriptionName'],
						resourceGroup = resource['properties']['resourceGroup'],
						amount = resource['properties']['cost'], 
						currency = resource['properties']['billingCurrency'],
						type = resource['properties']['consumedService']
						)
					)

					
			except KeyError as e:		
				print("There was a problem appending {} from the resource ".format(e))
					
			except Exception as e:
				print("ERROR: "+e)

			


			# Buffer the number of resources to submit to MySQL database in one transaction to 50K row chunks
			if len(values) < 50000 and (index + len(values)) != len(RESOURCES):	
				continue
			else: 			
				allValues = ",".join(values)
				try:
					azure_usage_db = db.open()
					conn = azure_usage_db.cursor()
					print("Open DB Connection: {}".format(azure_usage_db))

					query = """
					INSERT INTO workload_registry_v2.data_usage (
						id,
						usage_date,
						invoice_month,
						resource_cluster_id,
						cloud_source_id,
						billing_group,
						resource_group,
						amount,
						currency,
						type
						)
						values {} on duplicate key update amount = values(amount) + amount; 
						""".format(allValues)
						
					conn.execute(query)
					azure_usage_db.commit()
					# Print out summary
					print("Submitting {} - {} of {} data points".format(index, len(values)+index, len(RESOURCES)))
					# Clear buffer
					index = len(values)
					values = []
				
				except Exception as e:
					print(allValues[0:1000]+"...") 
					print("There was a problem submitting azure usage to the database: {}".format(e))
					break
				
				# Close Database connection
				db.close(azure_usage_db)
				print("Closed connection {}".format(azure_usage_db))
		
	print("Finished updated Azure Cloud Usage")


# Stop Stopwatch
end = time.perf_counter()
print("Execution Time: {} mins".format((end-start)/60))
