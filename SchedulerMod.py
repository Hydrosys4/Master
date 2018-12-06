
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
    'apscheduler.job_defaults.coalesce': 'true',
    'apscheduler.job_defaults.max_instances': '5',
    'apscheduler.timezone': 'UTC',
})



	
logger = logging.getLogger("hydrosys4."+__name__)




def print_job():
	global sched
	sched.print_jobs()

def start_scheduler():
	global sched
	sched.start()
	
def removealljobs():
	global sched
	for job in sched.get_jobs():
		job.remove()
	
def stop_scheduler():
	global sched	
	if sched.running:
		sched.shutdown(wait=False)
	
def get_next_run_time(jobname):
	global sched
	for job in sched.get_jobs():
		if job.name == jobname:
			return True , job.next_run_time
	return False, ""


if __name__ == '__main__':
	
	"""
	prova funzioni di scheduling
	
	"""

	
	
	
	
