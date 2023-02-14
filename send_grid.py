# using SendGrid's Python Library
# https://github.com/sendgrid/sendgrid-python
import os
import base64
import yaml
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import (Mail, Attachment, FileContent, FileName, FileType, Disposition)

# READ-ONLY
# IMPROVEMENTS: Get from Vault/ SQL Datbase 
config = dict()
config['operators'] = ["sguign@celestica.com"]
config['admin'] = ["sguign@celestica.com"]
config['apikey'] = os.getenv("sendgrid_api_key")


# Send test email to operators
def test():
	message = Mail(
		from_email="noreply@celestica.com",
		to_emails=config['operators'],
		subject="Sendgrid Services are working correctly",
		html_content="The Cloud Reporting Engine emailing services are working working.")
	try:
		sg = SendGridAPIClient(config['apikey'])
		response = sg.send(message)
		print(response.status_code)
		print(response.body)
		print(response.headers)
	except Exception as e:
		print(e.message)


# Send email to admin with subject and content
def email_admin(SUBJECT, CONTENT):
	message = Mail(
		from_email="noreply@celestica.com",
		to_emails=config['admin'],
		subject=SUBJECT,
		html_content=CONTENT)
	try:
		sg = SendGridAPIClient(config['apikey'])
		response = sg.send(message)
		print(response.status_code)
		print(response.body)
		print(response.headers)
	except Exception as e:
		print(e.message)


# Send email to operators with subject and content
def email_operators(SUBJECT, CONTENT):
	message = Mail(
		from_email="noreply@celestica.com",
		to_emails=config['operators'],
		subject=SUBJECT,
		html_content=CONTENT)
	try:
		sg = SendGridAPIClient(config['apikey'])
		response = sg.send(message)
		print(response.status_code)
		print(response.body)
		print(response.headers)
	except Exception as e:
		print(e.message)


# Send email to users by email, subject, and content
def email_user(EMAIL, SUBJECT, CONTENT):
	message = Mail(
		from_email="cloud-reporting-cls@celestica.com",
		to_emails = [EMAIL, "cloud-reporting-cls@celestica.com"],
		subject = SUBJECT,
		html_content = CONTENT)
		
	try:
		sg = SendGridAPIClient(config['apikey'])
		response = sg.send(message)
		print(response.status_code)
		print(response.body)
		print(response.headers)
	except Exception as e:
		print(e.message)

def email_owners(EMAIL, SUBJECT, BODY):
	message = Mail(
		from_email="cloud-reporting-cls@celestica.com",
		to_emails = [EMAIL, "cloud-reporting-cls@celestica.com"],
		subject = SUBJECT,
		html_content = BODY)
		
	try:
		sg = SendGridAPIClient(config['apikey'])
		response = sg.send(message)
		print(response.status_code)
		print(response.body)
		print(response.headers)
	except Exception as e:
		print(e.message)
	



def sendEmailWithAttachment(SUBJECT, CONTENT, FILENAME):
	message = Mail(
		from_email=config['admin'],
		to_emails=config['operators'],
		subject=SUBJECT,
		html_content=CONTENT)
	if FILENAME:	
		with open(FILENAME, 'rb') as f:
			data = f.read()
			f.close()
		encoded_file = base64.b64encode(data).decode()

		attachedFile = Attachment(
			FileContent(encoded_file),
			FileName(FILENAME),
			FileType('text/json'),
			Disposition('attachment')
		)
		message.attachment = attachedFile
	
	try:
		sg = SendGridAPIClient(config['apikey'])
		response = sg.send(message)
		print(response.status_code)
		print(response.body)
		print(response.headers)
	except Exception as e:
		print(e.message)
