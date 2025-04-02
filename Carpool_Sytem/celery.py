import os

from celery import Celery
from celery.schedules import schedule, crontab
# Set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Carpool_Sytem.settings")

app = Celery('Carpool_Sytem')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()


# Celery Beat Configuration 
app.conf.beat_schedule = {
    # 'add-every-minute': {
    #     'task': 'myapp.tasks.add',  # Replace with the actual path to your task
    #     'schedule': crontab(minute='*/1'),  # Runs every minute
    #     'args': (10, 5),
    # },
    # 'send-report-daily': {
    #     'task': 'myapp.tasks.send_report_task',  # Replace with the actual path to your task
    #     'schedule': crontab(hour=8, minute=0),  # Runs daily at 8:00 AM
    #     'kwargs': {'report_type': 'summary'},
    # },
    # 'cleanup-database-weekly': {
    #     'task': 'myapp.tasks.cleanup_old_data',  # Replace with the actual path to your task
    #     'schedule': crontab(day_of_week='sunday', hour=2, minute=30),  # Runs every Sunday at 2:30 AM
    # },
    # 'run-every-ten-seconds': {
    #     'task': 'myapp.tasks.some_other_task',  # Replace with the actual path to your task
    #     'schedule': schedule(run_every=10.0),  # Runs every 10 seconds
    # },
}

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')