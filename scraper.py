
import json, os, scrapy, smtplib
from dateutil.parser import parse
from scrapy.crawler import CrawlerProcess
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


jobs_file = 'jobs.json'
results_file = 'results.json'
config_file = 'email.config'

class RedHatJobsSpider(scrapy.Spider):
	name = 'Red Hat Jobs Spider'
	start_urls = ['https://careers-redhat.icims.com/jobs/search?ss=1&in_iframe=1&searchLocation=12873--Melbourne']

	def __init__(self, *args, **kwargs):
		super(RedHatJobsSpider, self).__init__(*args, **kwargs)
		self.jobs = []

	def parse(self, response):
		"""
		Extract the information that we need from the web pages; namely, a list of new jobs from Red Hat.
		A job contains:
		- a job title
		- a URL to view more information about the job
		- the date it was posted
		- a job category
		- a job's physical location
		- a unique ID

		Args:
			response: a Scrapy object containing the parsed web page.
		"""

		# Get each job listing
		table = response.selector.xpath("//*[contains(@class, 'iCIMS_JobsTable')]")

		if not table:
			return

		# Extract all the information into a set of lists.
		job_locations = table.xpath("//div[@class='col-xs-6 header left']/span/text()").extract()[1::2]
		job_dates = table.xpath("//div[@class='col-xs-6 header right']/span/@title").extract()
		job_titles = table.xpath("//div[@class='col-xs-12 title']/a/span/text()").extract()[1::2]
		job_urls = table.xpath("//div[@class='col-xs-12 title']/a/@href").extract()
		job_info = table.xpath("//div[@class='col-xs-12 additionalFields']/div/dl/dd/span/text()").extract()

		# Format to '21st Dec 2017'
		job_dates = [parse(date).strftime('%d %b %Y, %-H:%-M %p') for date in job_dates]

		# category = even items, id = odd items
		job_categories = job_info[::2]
		job_ids = job_info[1::2]
		print (job_dates)
		# Combine the lists into a dictionary which represents a job
		for i in range(len(job_titles)):
			job = {
				'location':job_locations[i].strip(),
				'date':job_dates[i].strip(),
				'title':job_titles[i].strip(),
				'category':job_categories[i].strip(),
				'id':job_ids[i].strip(),
				'url':job_urls[i].strip()
			}
			self.jobs.append(job)

		return self.jobs


def parse_config(filename):
    """A custom config parser that reads key/value pairs in the form of:
        KEY1 = VALUE1
        KEY2 = VALUE2
    It also allows comments by prepending # to the line.
    This saves us from having to import 'configparser' in an effort to
    reduce total size of the imported libraries.

    Args:
        filename: the config file to parse.

    Returns:
        a dictionary containing the parsed config
    """
    COMMENT_CHAR = '#'
    SEPARATOR_CHAR = '='
    options = {}

    with open(filename) as fh:
        for line in fh.readlines():
            if COMMENT_CHAR in line:
                line, comment = line.split(COMMENT_CHAR, 1)

            if SEPARATOR_CHAR in line:
                option, value = line.split(SEPARATOR_CHAR, 1)
                option = option.strip()
                value = value.strip()
                options[option] = value

    return options


def send_jobs_via_email(jobs, email_address, email_password, email_server, email_port):
	"""Send a list of new jobs via email.

	Args:
		jobs: a list of dictionaries containing the jobs to email
	"""
	from_address = email_address
	to_addresses = [email_address]

	body = ''
	for job in sorted(jobs, key=lambda k: parse(k['date']), reverse=True):	# Sort by date
		body += '<b><a href="%s">%s</a></b> in %s<br>Posted on %s<br>Category: %s<br>Job ID: %s<br><br>' % (job['url'], job['title'], job['location'], job['date'], job['category'], job['id'])

	body = '<html><body>' + body + '</body></html>'

	# Create the message and send it
	msg = MIMEMultipart('alternative')
	msg['From'] = from_address

	if len(jobs) == 1:
		msg['Subject'] = '%d new job from Red Hat' % len(jobs)
	else:
		msg['Subject'] = '%d new jobs from Red Hat' % len(jobs)

	msg.attach(MIMEText(body, 'html'))

	# Connect to Outlook's server
	print ("Connecting to Outlook's server...")
	server = smtplib.SMTP(host=email_server, port=email_port)
	server.starttls()
	server.login(email_address, email_password)

	for address in to_addresses:
		print ("Sending email to %s..." % address)
		msg['To'] = address
		server.send_message(msg)

	server.quit()

def get_new_jobs():
	"""Check if any of the scraped jobs are new by comparing them to the previously scraped jobs.
	"""
	new_jobs = []
	jobs = []

	with open(results_file) as fh:
		results = json.load(fh)	# Output of the scraper

	if not os.path.exists(jobs_file):
		f = open(jobs_file, 'w')
		f.write('[]')
	else:
		with open(jobs_file) as fh:
			jobs = json.load(fh)	# Previously scraped jobs

	for result in results:
		for job in jobs:
			if result['id'] == job['id']:
				break
		else:
			new_jobs.append(result)

	return new_jobs


def save_new_jobs(new_jobs):
	"""Write the new jobs to the file containing the previously scraped jobs.

	Args:
		new_jobs: a list of dictionaries containing the new jobs to save.
	"""
	with open(jobs_file) as fh:
		jobs = json.load(fh)	# Previously scraped jobs

	all_jobs = jobs + new_jobs

	with open(jobs_file, 'w') as fh:
		fh.write(json.dumps(all_jobs))


def main(event, context):
	"""Scrape any jobs from the site and save them as a JSON file.

	Args:
		event: arguments to this function sent from "aws_cloudwatch_event_target"
		context: ?
	"""
	config = parse_config(config_file)

	# We have to remove the results file first, else Scrapy will keep appending the output.
	if os.path.exists(results_file):
		os.remove(results_file)

	process = CrawlerProcess({
		'USER_AGENT': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1)',
		'FEED_FORMAT': 'json',
		'FEED_URI': results_file,
		'LOG_LEVEL':'WARNING'
	})
	process.crawl(RedHatJobsSpider)
	process.start()

	new_jobs = get_new_jobs()
	if new_jobs:
		print ("Found %d new jobs!" % len(new_jobs))
		send_jobs_via_email(new_jobs, config['EMAIL_ADDRESS'], config['EMAIL_PASSWORD'], config['EMAIL_SERVER_HOST'], config['EMAIL_SERVER_PORT'])
	else:
		print ("Found no new jobs.")

	save_new_jobs(new_jobs)

main(None,None)
