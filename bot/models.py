from django.db import models


class Client(models.Model):
    phone_number = models.CharField(max_length=20, unique=True)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    state = models.CharField(max_length=50, default='INIT')
    temp_media_urls = models.JSONField(default=list)

    def __str__(self):
        return f'{self.first_name} {self.last_name}'


class Photo(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='photos')
    photo_url = models.URLField(max_length=200)
