from celery import shared_task
from django.utils import timezone

from bot.models import Client, Photo
from bot.twilio_client import TwilioClient


@shared_task
def send_delayed_message(client_id):
    client = Client.objects.get(id=client_id)

    last_photo_time = Photo.objects.filter(client=client).latest('created_at').created_at
    if (last_photo_time and client.state == "WAITING_FOR_PHOTOS"
            and (timezone.now() - last_photo_time) >= timezone.timedelta(seconds=5)):
        TwilioClient().send_template_message(
            client.phone_number,
            "HX0fb4fdb4d4a8d13f4ea9f61206afdfee"
        )
        client.state = 'CONFIRM_PHOTOS'
        client.save()


