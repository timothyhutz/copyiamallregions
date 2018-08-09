import boto3, logging, os, json

log = logging.getLogger()
loglevel = os.environ['LOG_LEVEL']
if loglevel == 'info':
	log.setLevel(logging.INFO)
elif loglevel == 'debug':
	log.setLevel(logging.DEBUG)
else:
	log.setLevel(logging.ERROR)


class ebsimage(object):
	def __init__(self, ami=None, account=None):
		self.ami = ami
		self.account = account
		image_data = boto3.client('ec2', region_name='us-east-1').describe_images(ImageIds=[self.ami])
		if 'Tags' in image_data['Images'][0]:
			self.tags = image_data['Images'][0]['Tags']
			self.tags.append({'Key': 'parent-ami-id', 'Value': self.ami})
		self.temp_creds = boto3.client('sts').assume_role(
			RoleArn=f'arn:aws:iam::{self.account}:role/goldenAMICrossAccountRole',
			RoleSessionName='Goldami_session'
		)

	def main(self, region=None):
		client = boto3.Session(
			aws_access_key_id=self.temp_creds['Credentials']['AccessKeyId'],
			aws_secret_access_key=self.temp_creds['Credentials']['SecretAccessKey'],
			aws_session_token=self.temp_creds['Credentials']['SessionToken']
		).client('ec2', region_name=region)
		response = client.copy_image(
			Encrypted=True,
			Name='GoldAMI-demo',
			SourceImageId=self.ami,
			SourceRegion='us-east-1'

		)
		client.create_tags(
			Resources=[response['ImageId']],
			Tags=self.tags
		)
		return {"region": region, "ami": response['ImageId'], "account": self.account}


def lambda_handler(event, context):
	global ami
	global account
	for record in event['Records']:
		log.debug(record)
		data = json.loads(record['body'])
		ami = data['ami_id']
		account = data['account_id']
		log.debug(ami + account)
		ebs = ebsimage(ami=ami,account=account)
		ec2_region_list = []
		for region_each in boto3.client('ec2').describe_regions()['Regions']:
			ec2_region_list.append(region_each['RegionName'])
		log.debug(ec2_region_list)
		new_ami_ids = list()
		for region in ec2_region_list:
			new_ami_ids.append(ebs.main(region=region))
		log.info(new_ami_ids)
		sqs_client = boto3.client('sqs')
		sqs_client.send_message(
			QueueUrl='',
			MessageBody='',
		)

