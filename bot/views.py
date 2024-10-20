import json
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from twilio.twiml.messaging_response import MessagingResponse


from .models import Client, Photo
from bot.twilio_client import TwilioClient
from bot.tasks import send_delayed_message


class WhatsAppBotView(APIView):
    permission_classes = [AllowAny]
    welcome_template_sid = "HXca07df4d5dbc1c601f5ccb1c61380f44"
    confirmation_template_sid = "HX4f750707d8cffc465b777d0fabfad8b8"
    photo_request_template_sid = "HX0fb4fdb4d4a8d13f4ea9f61206afdfee"
    ask_anfrage_formular_sid = "HX565a986c2d40a5be32edd052cdfbbb34"
    visit_anfrage_formular = "HX68b22df274fc078132cea73a117ca96b"

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
        elif state == 'ANFRAGE_FORMULAR':
            self.handle_anfrage_formular(client, body)

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
                    "Bitte geben Sie Ihren Vor- und Nachnamen in folgendem Format ein 'Bernhard Schmid'.")

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
                "Bitte geben Sie Ihren Vor - und Nachnamen in folgendem Format ein 'Bernhard Schmid'."
            )
            client.state = 'WAITING_FOR_NAME'
        client.save()

    def handle_photo_upload(self, client, media_urls):

        if media_urls:
            Photo.objects.create(client=client, photo_url=media_urls)

            send_delayed_message.apply_async((client.id,), countdown=5)

        return HttpResponse(status=200)

    def handle_photo_confirmation(self, client, body):
        if body.lower() == 'ja':

            self.notify_managers(client)
            self.twilio_client.send_template_message(
                client.phone_number,
                template_sid=self.ask_anfrage_formular_sid
            )
            client.state = 'ANFRAGE_FORMULAR'
        else:
            self.twilio_client.send_message(
                client.phone_number, "Bitte laden Sie die restlichen Fotos hoch."
            )
            client.state = 'WAITING_FOR_PHOTOS'
        client.save()

    def handle_anfrage_formular(self, client, body):
        if body.lower() == 'ja':

            self.twilio_client.send_message(
                client.phone_number,
                "Wir haben Ihre Angaben erhalten, Sie werden in Kürze ein Angebot per Post erhalten."
            )
            client.state = 'INIT'
        else:
            self.twilio_client.send_template_message(
                client.phone_number,
                self.visit_anfrage_formular
            )
            client.state = 'INIT'
        client.save()

    def notify_managers(self, client):
        managers = "whatsapp:+380634429319"
        photo_urls = [photo.photo_url for photo in client.photos.all()]

        if photo_urls:
            message_body = (f"Новый клиент: {client.first_name} {client.last_name}\n"
                            f"Фотографии: {', '.join(photo_urls)}")
        else:
            message_body = (f"Новый клиент: {client.first_name} {client.last_name}\n"
                            f"Фотографии не загружены.")


            try:
                self.twilio_client.send_message(managers, message_body)
                print(f"Сообщение успешно отправлено менеджеру: {managers}")
            except Exception as e:
                print(f"Ошибка при отправке сообщения менеджеру {managers}: {e}")
