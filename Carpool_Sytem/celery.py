from __future__ import absolute_import, unicode_literals
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
    'deactivate-expired-rides-every-5-minutes': {
        'task': 'rides.tasks.deactivate_expired_rides',  # Replace with the actual path to your task
        'schedule': crontab(minute='*/5'),  # Runs every minute
    },
}

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')