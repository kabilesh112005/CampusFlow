# accounts/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # ── Auth ──────────────────────────────────
    path('register/',  views.register_view,   name='register'),
    path('login/',     views.login_view,      name='login'),
    path('logout/',    views.logout_view,     name='logout'),

    # ── Dashboard ─────────────────────────────
    path('dashboard/', views.dashboard_view,  name='dashboard'),

    # ── Events ────────────────────────────────
    path('events/',         views.events_view,       name='events'),
    path('events/create/',  views.create_event_view, name='create_event'),

    # 🔥 NEW: REGISTER EVENT
    path('events/register/<int:event_id>/', views.register_event_view, name='register_event'),

    

    # ── Club Approval ─────────────────────────
    path('manage-clubs/', views.manage_clubs_view, name='manage_clubs'),
    path('approve-club/<int:club_id>/', views.approve_club_view, name='approve_club'),

    # 🔥 NEW: REGISTRATIONS SYSTEM
    path('my-registrations/', views.my_registrations_view, name='my_registrations'),
    path('manage-registrations/', views.manage_registrations_view, name='manage_registrations'),
    path('update-registration/<int:reg_id>/<str:action>/', views.update_registration_status, name='update_registration'),
    path('my-events/', views.my_registrations_view, name='my_events'),
    path('scan/<int:event_id>/<str:token>/', views.scan_qr_view, name='scan_qr'),
    path('scanner/<int:event_id>/', views.qr_scanner_view, name='qr_scanner'),
    path('attendance/', views.attendance_list_view, name='attendance'),
    path('export-attendance/', views.export_attendance, name='export_attendance'),
    path('registrations/manage/', views.manage_registrations_view, name='manage_registrations'),
path('registrations/update/<int:reg_id>/<str:status>/', views.update_registration_status, name='update_registration'),
path('venues/add/', views.create_venue_view, name='create_venue'),
path('slots/add/', views.create_slot_view, name='create_slot'),
path('events/update/<int:event_id>/<str:action>/', views.update_event_status, name='update_event_status'),
path('panel/', views.admin_dashboard_view, name='admin_dashboard'),
path('panel/users/', views.manage_users_view, name='manage_users'),
path('panel/update-role/<int:user_id>/', views.update_user_role_view, name='update_user_role'),
path('panel/colleges/', views.manage_colleges_view, name='manage_colleges'),
path('panel/colleges/create/', views.create_college_view, name='create_college'),
path('panel/assign-college-admin/<int:user_id>/', views.assign_college_admin_view, name='assign_college_admin'),
path('panel/delete-user/<int:user_id>/', views.delete_user_view, name='delete_user'),
path('events/edit/<int:event_id>/', views.edit_event_view, name='edit_event'),
path('events/<int:event_id>/', views.event_detail_view, name='event_detail'),
]