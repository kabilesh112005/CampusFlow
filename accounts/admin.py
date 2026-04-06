from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, College, Club, Venue, Event, VenueSlot


@admin.register(College)
class CollegeAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'location', 'created_at')


@admin.register(Club)
class ClubAdmin(admin.ModelAdmin):
    list_display = ('name', 'college', 'admin')


@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ('name', 'location', 'college')


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'club', 'date')

@admin.register(VenueSlot)
class VenueSlotAdmin(admin.ModelAdmin):
    list_display = ('venue', 'date', 'start_time', 'end_time', 'is_available')



@admin.register(User)
class CustomUserAdmin(UserAdmin):

    list_display = ('username', 'email', 'role', 'college', 'is_staff')
    list_filter = ('role', 'college')

    fieldsets = UserAdmin.fieldsets + (
        ('CampusFlow Info', {'fields': ('role', 'college')}),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        ('CampusFlow Info', {'fields': ('role', 'college')}),
    )