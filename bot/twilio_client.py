from twilio.rest import Client
from django.conf import settings


class TwilioClient:
    def __init__(self):
        self.client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        self.phone_number = settings.TWILIO_PHONE_NUMBER

    def send_template_message_with_variable(self, to, template_sid, template_data):
        message = self.client.messages.create(
            from_=self.phone_number,
            to=to,
            content_sid=template_sid,
            content_variables=template_data
        )
        return message

    def send_template_message(self, to, template_sid):
        message = self.client.messages.create(
            from_=self.phone_number,
            to=to,
            content_sid=template_sid,
        )
        return message

    def send_message(self, to, body):
        message = self.client.messages.create(
            from_=self.phone_number,
            to=to,
            body=body
        )
        return message
