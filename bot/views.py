import json
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from twilio.twiml.messaging_response import MessagingResponse

from WhatsAppBot import settings
from .models import Client, Photo
from .twilio_client import TwilioClient


class WhatsAppBotView(APIView):
    permission_classes = [AllowAny]
    welcome_template_sid = "HXca07df4d5dbc1c601f5ccb1c61380f44"
    confirmation_template_sid = "HX4f750707d8cffc465b777d0fabfad8b8"
    photo_request_template_sid = "HX0fb4fdb4d4a8d13f4ea9f61206afdfee"

    def __init__(self, *args, **kwargs):
        self.twilio_client = TwilioClient()
        super().__init__(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        from_number = request.data.get('From')
        body = request.data.get('Body', '').strip()
        media_urls = request.data.get('MediaUrl0')

        client, created = Client.objects.get_or_create(phone_number=from_number)

        state = client.state

        if state == 'INIT':
            self.send_welcome_message(from_number)
            client.state = 'WAITING_FOR_NAME_REQUEST'
            client.save()
        elif state == 'WAITING_FOR_NAME_REQUEST':
            self.send_name_request(client, body)
        elif state == 'WAITING_FOR_NAME':
            self.handle_name_input(client, body)
        elif state == 'CONFIRM_NAME':
            self.handle_name_confirmation(client, body)
        elif state == 'WAITING_FOR_PHOTOS':
            self.handle_photo_upload(client, media_urls)
        elif state == 'CONFIRM_PHOTOS':
            self.handle_photo_confirmation(client, body)

        return HttpResponse(status=200)

    def send_welcome_message(self, from_number):
        self.twilio_client.send_template_message(
            from_number,
            self.welcome_template_sid,
        )

    def send_name_request(self, client, body):
        if body:
            self.twilio_client.send_message(
                client.phone_number,
                "Bitte geben Sie Ihren Vor- und Nachnamen in folgendem Format ein 'Bernhard Schmid'."
            )
            client.state = 'WAITING_FOR_NAME'
            client.save()

    def handle_name_input(self, client, body):
        if body:
            names = body.split()
            if len(names) >= 2:
                client.first_name = names[0]
                client.last_name = names[1]
                client.save()
                full_name = f"{client.first_name} {client.last_name}"
                template_data = {"1": full_name}
                self.twilio_client.send_template_message_with_variable(
                    client.phone_number,
                    self.confirmation_template_sid,
                    json.dumps(template_data)
                )
                client.state = 'CONFIRM_NAME'
                client.save()
            else:
                self.twilio_client.send_message(
                    client.phone_number,
                    "Bitte geben Sie Ihren Vor- und Nachnamen in folgendem Format ein 'Bernhard Schmid'."
                )

    def handle_name_confirmation(self, client, body):
        message = 'Bitte laden Sie 10 bis 20 Fotos von Ihren Möbeln und Gegenständen in der Wohnung hoch'
        if body.lower() == 'ja':
            self.twilio_client.send_message(
                client.phone_number,
                message
            )
            client.state = 'WAITING_FOR_PHOTOS'
        else:
            self.twilio_client.send_message(
                client.phone_number,
                "Bitte geben Sie Ihren Vor- und Nachnamen in folgendem Format ein 'Bernhard Schmid'."
            )
            client.state = 'WAITING_FOR_NAME'
        client.save()

    def handle_photo_upload(self, client, media_urls):
        if media_urls:
            client.temp_media_urls.extend(media_urls)
            client.save()

        self.twilio_client.send_template_message(
            client.phone_number,
            self.photo_request_template_sid,
        )
        client.state = 'CONFIRM_PHOTOS'
        client.save()

    def handle_photo_confirmation(self, client, body):
        if body.lower() == 'да':
            for media_url in client.temp_media_urls:
                Photo.objects.create(client=client, photo_url=media_url)

            self.notify_managers(client)
            self.twilio_client.send_message(
                client.phone_number, "Спасибо! Ваши данные и фотографии получены."
            )
            client.state = 'INIT'
            client.temp_media_urls = []
        else:
            self.twilio_client.send_message(
                client.phone_number, "Пожалуйста, загрузите оставшиеся фотографии."
            )
            client.state = 'WAITING_FOR_PHOTOS'
        client.save()

    def notify_managers(self, client):
        managers = ['manager1_phone_number', 'manager2_phone_number']
        for manager in managers:
            message_body = f"Новый клиент: {client.first_name} {client.last_name}\nФотографии: {', '.join(photo.photo_url for photo in client.photos.all())}"
            self.twilio_client.send_message(manager, message_body)
