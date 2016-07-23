
from datetime import datetime, date
import time
import logging 
import os.path

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor

executors = {
    'default': ThreadPoolExecutor(50),
    'processpool': ProcessPoolExecutor(20)
}
job_defaults = {
    'coalesce': False,
    'max_instances': 20
}
sched = BackgroundScheduler(executors=executors, job_defaults=job_defaults)

		



def print_job():
	sched.print_jobs()

def start_scheduler():
	sched.start()
	
def removealljobs():
	for job in sched.get_jobs():
		job.remove()
	
def stop_scheduler():
	sched.shutdown()
	




if __name__ == '__main__':
	
	"""
	prova funzioni di scheduling
	
	"""

	
	
	
	
