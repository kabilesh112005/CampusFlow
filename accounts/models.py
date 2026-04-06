from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
import uuid
import qrcode
from io import BytesIO
from django.core.files import File


# 🔥 COLLEGE MODEL
class College(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, unique=True)
    location = models.CharField(max_length=255)

    # 🔥 Email domain validation
    email_domain = models.CharField(max_length=100, default="@example.com")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


# 🔥 USER MODEL
class User(AbstractUser):

    STUDENT = 'student'
    CLUB_ADMIN = 'club_admin'
    COLLEGE_ADMIN = 'college_admin'

    ROLE_CHOICES = [
        (STUDENT, 'Student'),
        (CLUB_ADMIN, 'Club Admin'),
        (COLLEGE_ADMIN, 'College Admin'),
    ]

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=STUDENT,
    )

    college = models.ForeignKey(
        College,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    @property
    def is_student(self):
        return self.role == self.STUDENT

    @property
    def is_club_admin(self):
        return self.role == self.CLUB_ADMIN

    @property
    def is_college_admin(self):
        return self.role == self.COLLEGE_ADMIN


# 🔥 CLUB MODEL
class Club(models.Model):

    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'

    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (APPROVED, 'Approved'),
        (REJECTED, 'Rejected'),
    ]

    name = models.CharField(max_length=255)
    description = models.TextField()

    college = models.ForeignKey(
        College,
        on_delete=models.CASCADE,
        related_name='clubs'
    )

    admin = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_clubs'
    )

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default=PENDING
    )

    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_clubs'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.college.name})"


# 🔥 VENUE MODEL (ONLY ONE — FIXED)
class Venue(models.Model):
    name = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    capacity = models.IntegerField()

    college = models.ForeignKey(
        College,
        on_delete=models.CASCADE,
        related_name='venues'
    )

    def __str__(self):
        return f"{self.name} ({self.college.name})"


# 🔥 VENUE SLOT MODEL (NEW SYSTEM)
class VenueSlot(models.Model):
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()

    is_available = models.BooleanField(default=True)

    def clean(self):
        # Prevent overlapping slots for same venue
        conflicts = VenueSlot.objects.filter(
            venue=self.venue,
            date=self.date,
            start_time__lt=self.end_time,
            end_time__gt=self.start_time
        ).exclude(id=self.id)

        if conflicts.exists():
            raise ValidationError("❌ This slot overlaps with an existing slot.")

    def __str__(self):
        return f"{self.venue.name} - {self.date} ({self.start_time} - {self.end_time})"


# 🔥 EVENT MODEL (UPDATED WITH SLOT)
# 🔥 EVENT MODEL (UPDATED — SMART VENUE SYSTEM)
class Event(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()

    club = models.ForeignKey(
        Club,
        on_delete=models.CASCADE,
        related_name='events'
    )

    # 🔥 KEEP SLOT (but optional, not used actively)
    slot = models.ForeignKey(
        VenueSlot,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='events'
    )

    # 🔥 MAIN FIELD NOW
    venue = models.ForeignKey(
        Venue,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='events'
    )

    # 🔥 PRIMARY TIME SYSTEM
    date = models.DateField(null=True, blank=True)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)

    poster = models.ImageField(upload_to='event_posters/', null=True, blank=True)

    capacity = models.PositiveIntegerField(default=50)
    is_registration_open = models.BooleanField(default=True)

    is_active = models.BooleanField(default=True)
    is_approved = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if self.start_time and self.end_time:
            if self.end_time <= self.start_time:
                raise ValidationError("End time must be after start time.")

        # 🔥 SMART CONFLICT CHECK (CORE FEATURE)
        if self.venue and self.date and self.start_time and self.end_time:
            conflict = Event.objects.filter(
                venue=self.venue,
                date=self.date,
                start_time__lt=self.end_time,
                end_time__gt=self.start_time
            ).exclude(id=self.id)

            if conflict.exists():
                raise ValidationError(
                    "This venue is already booked for the selected time."
                )

    def save(self, *args, **kwargs):
        # ❌ REMOVE SLOT AUTO BLOCK (DISABLED)
        # Old slot logic removed to avoid complexity

        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

# 🔥 EVENT REGISTRATION
class EventRegistration(models.Model):

    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'

    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (APPROVED, 'Approved'),
        (REJECTED, 'Rejected'),
    ]

    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name='registrations'
    )

    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='registrations'
    )

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default=PENDING
    )

    is_attended = models.BooleanField(default=False)

    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_registrations'
    )

    registered_at = models.DateTimeField(auto_now_add=True)

    # 🔥 QR SYSTEM
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True, null=True)
    qr_token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    class Meta:
        unique_together = ('event', 'student')

    def save(self, *args, **kwargs):
        # Generate QR code if not exists
        if not self.qr_code:
            qr_data = f"{self.event.id}-{self.student.id}-{self.qr_token}"
            qr_img = qrcode.make(qr_data)

            buffer = BytesIO()
            qr_img.save(buffer, format='PNG')

            file_name = f"qr_{self.qr_token}.png"
            self.qr_code.save(file_name, File(buffer), save=False)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.student.username} → {self.event.title} ({self.status})"