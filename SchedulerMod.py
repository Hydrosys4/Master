
from datetime import datetime, date
import time
import logging 
import os.path
import apscheduler

from apscheduler.schedulers.background import BackgroundScheduler


# The "apscheduler." prefix is hard coded
sched = BackgroundScheduler({
    'apscheduler.executors.default': {
        'class': 'apscheduler.executors.pool:ThreadPoolExecutor',
        'max_workers': '25'
    },
    'apscheduler.executors.processpool': {
        'type': 'processpool',
        'max_workers': '10'
    },
    'apscheduler.job_defaults.coalesce': 'false',
    'apscheduler.job_defaults.max_instances': '5',
    'apscheduler.timezone': 'UTC',
})



	
logger = logging.getLogger("hydrosys4."+__name__)




def print_job():
	sched.print_jobs()

def start_scheduler():
	sched.start()
	
def removealljobs():
	for job in sched.get_jobs():
		job.remove()
	
def stop_scheduler():
	sched.shutdown()
	
def get_next_run_time(jobname):
	for job in sched.get_jobs():
		if job.name == jobname:
			return True , job.next_run_time
	return False, ""


if __name__ == '__main__':
	
	"""
	prova funzioni di scheduling
	
	"""

	
	
	
	
