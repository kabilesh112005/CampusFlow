import qrcode
from io import BytesIO
from django.core.files import File
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import EventRegistration


@receiver(post_save, sender=EventRegistration)
def generate_qr_code(sender, instance, created, **kwargs):

    if created and not instance.qr_code:

        qr_data = str(instance.qr_token)

        qr = qrcode.make(qr_data)

        buffer = BytesIO()
        qr.save(buffer, format='PNG')

        file_name = f'qr_{instance.id}.png'

        instance.qr_code.save(file_name, File(buffer), save=False)
        instance.save(update_fields=['qr_code'])