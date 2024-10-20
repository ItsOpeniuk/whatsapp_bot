from django.db.models.signals import post_save
from django.dispatch import receiver
from bot.models import Photo
from bot.tasks import send_delayed_message

@receiver(post_save, sender=Photo)
def photo_saved_handler(sender, instance, created, **kwargs):
    if created:
        send_delayed_message.apply_async((instance.client.id,), countdown=5)
