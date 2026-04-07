# accounts/views.py
# CampusFlow — All views: auth + events + bookings + dashboard

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import EventRegistration


from .forms import RegisterForm, LoginForm, EventForm
from .models import Event, Venue, Club , VenueSlot

import pandas as pd
from django.http import HttpResponse
import json


# ═══════════════════════════════════════════════════════
# AUTH VIEWS  (keep exactly as you had them)
# ═══════════════════════════════════════════════════════

def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            login(request, user)
            messages.success(request, f"Welcome to CampusFlow, {user.first_name or user.username}!")
            return redirect('dashboard')
        messages.error(request, "Please fix the errors below.")
    else:
        form = RegisterForm()

    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            messages.success(request, f"Welcome back, {form.get_user().first_name or form.get_user().username}!")
            return redirect('dashboard')
        messages.error(request, "Invalid username or password.")
    else:
        form = LoginForm(request)

    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, "You've been logged out.")
    return redirect('login')


# ═══════════════════════════════════════════════════════
# 🔥 UPDATED EVENT REGISTRATION LOGIC
# ═══════════════════════════════════════════════════════

@login_required
def register_event_view(request, event_id):

    event = get_object_or_404(
        Event,
        id=event_id,
        club__college=request.user.college,
        club__status='approved'
    )

    user = request.user

    # 1. Only students
    if not user.is_student:
        messages.error(request, "Only students can register for events.")
        return redirect('events')

    # 2. Same college check
    if user.college != event.club.college:
        messages.error(request, "You can only register for events in your college.")
        return redirect('events')

    # 3. Email domain validation
    if not user.email.endswith(user.college.email_domain):
        messages.error(request, "Use your college email to register.")
        return redirect('events')

    # 4. Prevent duplicate registration
    if EventRegistration.objects.filter(
        event=event,
        student=user
    ).exists():
        messages.info(request, "You have already registered for this event.")
        return redirect('events')

    # 5 & 6. Capacity check (only approved registrations counted)
    current_count = EventRegistration.objects.filter(
        event=event,
        status='approved'
    ).count()

    if current_count >= event.capacity:
        messages.error(request, "Registration closed. Event is full.")
        return redirect('events')

    # 7. Auto approval
    EventRegistration.objects.create(
        event=event,
        student=user,
        status='approved',
        reviewed_by=None
    )

    messages.success(request, "Successfully registered! You're in 🎉")
    return redirect('events')


# ═══════════════════════════════════════════════════════
# DASHBOARD
# ═══════════════════════════════════════════════════════

@login_required(login_url='login')
def dashboard_view(request):

    user = request.user
    college = user.college

    if user.is_college_admin:
        total_events = Event.objects.filter(
            club__college=college,
            is_approved=True,
            is_active=True
        ).count()
        total_bookings = 0
        total_clubs = Club.objects.filter(college=college).count()
        total_venues = Venue.objects.filter(college=college).count()

    elif user.is_club_admin:
        user_clubs = Club.objects.filter(admin=user, college=college)

        total_events = Event.objects.filter(
            club__in=user_clubs,
            is_approved=True,
            is_active=True
        ).count()
        total_bookings = 0
        total_clubs = user_clubs.count()
        total_venues = Venue.objects.filter(college=college).count()

    else:
        total_events = Event.objects.filter(
            club__college=college,
            is_approved=True,
            is_active=True
        ).count()
        total_bookings = None
        total_clubs = Club.objects.filter(college=college, status='approved').count()
        total_venues = Venue.objects.filter(college=college).count()

    # 🔥 UPDATED
    upcoming_events = Event.objects.select_related('club').filter(
        club__college=college,
        is_approved=True,
        is_active=True
    ).order_by('date', 'start_time')[:5]

    # 🔥 CHART DATA
    events = Event.objects.filter(
        club__college=college,
        is_approved=True,
        is_active=True
    )

    event_labels = []
    event_attendance = []

    for event in events:
        attended = EventRegistration.objects.filter(
            event=event,
            is_attended=True
        ).count()

        event_labels.append(event.title)
        event_attendance.append(attended)

    context = {
        'user': user,
        'role_display': user.get_role_display(),
        'total_events': total_events,
        'total_bookings': total_bookings,
        'total_clubs': total_clubs,
        'total_venues': total_venues,
        'upcoming_events': upcoming_events,
        'event_labels': json.dumps(event_labels),
        'event_attendance': json.dumps(event_attendance),
    }

    return render(request, 'accounts/dashboard.html', context)


# ═══════════════════════════════════════════════════════
# EVENTS
# ═══════════════════════════════════════════════════════
@login_required(login_url='login')
def events_view(request):

    # 🔥 ROLE-BASED EVENTS
    if request.user.is_student:
        events = Event.objects.select_related('club').filter(
            club__college=request.user.college,
            club__status='approved',
            is_approved=True,
            is_active=True
        )

    elif request.user.is_club_admin:
        user_clubs = Club.objects.filter(admin=request.user)
        events = Event.objects.select_related('club').filter(
            club__in=user_clubs
        )

    elif request.user.is_college_admin:
        events = Event.objects.select_related('club').filter(
            club__college=request.user.college
        )

    # 🔥 ORDERING
    events = events.order_by('date', 'start_time')

    # 🔍 SEARCH
    query = request.GET.get('q', '').strip()
    if query:
        events = events.filter(title__icontains=query)

    # 🔥 SMART LOGIC
    for event in events:
        event.is_registered = EventRegistration.objects.filter(
            event=event,
            student=request.user
        ).exists()

        event.is_full = EventRegistration.objects.filter(
            event=event,
            status='approved'
        ).count() >= event.capacity

        event.attended_count = EventRegistration.objects.filter(
            event=event,
            is_attended=True
        ).count()

        event.total_registered = EventRegistration.objects.filter(
            event=event
        ).count()

    context = {
        'events': events,
        'query': query,
    }

    return render(request, 'accounts/events.html', context)

@login_required(login_url='login')
def create_event_view(request):

    if request.user.is_student:
        messages.error(request, "Students cannot create events.")
        return redirect('events')

    if request.user.is_club_admin:
        club = Club.objects.filter(
            admin=request.user,
            college=request.user.college,
            status='approved'
        ).first()

        if not club:
            messages.error(request, "Your club is not approved yet.")
            return redirect('dashboard')

    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES, user=request.user)

        if form.is_valid():
            print("FORM VALID ✅")

            event = form.save(commit=False)

            # 🔥 FIX: assign club automatically for college admin
            if request.user.is_college_admin:
                event.club = None

            if request.user.is_club_admin:
                event.is_approved = False
            elif request.user.is_college_admin:
                event.is_approved = True
            
            event.is_active = True

            event.save()

            messages.success(request, "Event '{event.title}' created successfully!")
            return redirect('events')

        else:
            print("FORM ERRORS ❌", form.errors)

            # 🔥 IMPORTANT: return form again if invalid
            return render(request, 'accounts/create_event.html', {'form': form})

    else:
        form = EventForm(user=request.user)

    # 🔥 ALWAYS RETURN (THIS FIXES YOUR ERROR)
    return render(request, 'accounts/create_event.html', {'form': form})
   
@login_required(login_url='login')
def create_venue_view(request):

    if not request.user.is_college_admin:
        return redirect('dashboard')

    if request.method == 'POST':
        name = request.POST.get('name')
        location = request.POST.get('location')
        capacity = request.POST.get('capacity')

        if name and location and capacity:
            Venue.objects.create(
                name=name,
                location=location,
                capacity=capacity,
                college=request.user.college
            )
            messages.success(request, "Venue added successfully!")
            return redirect('create_venue')

        else:
            messages.error(request, "All fields are required.")

    venues = Venue.objects.filter(college=request.user.college)

    return render(request, 'accounts/create_venue.html', {
        'venues': venues
    })

@login_required(login_url='login')
def create_slot_view(request):

    if not request.user.is_college_admin:
        return redirect('dashboard')

    venues = Venue.objects.filter(college=request.user.college)

    if request.method == 'POST':
        venue_id = request.POST.get('venue')
        date = request.POST.get('date')
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')

        if venue_id and date and start_time and end_time:
            venue = Venue.objects.get(id=venue_id)

            VenueSlot.objects.create(
                venue=venue,
                date=date,
                start_time=start_time,
                end_time=end_time,
                is_available=True
            )

            messages.success(request, "Slot created successfully!")
            return redirect('create_slot')

        else:
            messages.error(request, "All fields are required.")

    slots = VenueSlot.objects.filter(
        venue__college=request.user.college
    ).order_by('-date')

    return render(request, 'accounts/create_slot.html', {
        'venues': venues,
        'slots': slots
    })


# ═══════════════════════════════════════════════════════
# BOOK VENUE
# ═══════════════════════════════════════════════════════

@login_required(login_url='login')
def book_venue_view(request):

    if request.user.is_student:
        messages.error(request, "Students cannot access venue slots.")
        return redirect('events')

    # 🔥 SLOT SYSTEM
    if request.user.is_college_admin:
        slots = VenueSlot.objects.filter(
            venue__college=request.user.college
        ).order_by('-date')

    elif request.user.is_club_admin:
        slots = VenueSlot.objects.filter(
            venue__college=request.user.college,
            is_available=True
        ).order_by('date')

    else:
        slots = []

    context = {
        'slots': slots,
    }

    return render(request, 'accounts/book.html', context)


# ═══════════════════════════════════════════════════════
# CLUB APPROVAL SYSTEM
# ═══════════════════════════════════════════════════════

@login_required
def manage_clubs_view(request):

    if not request.user.is_college_admin:
        return redirect('dashboard')

    clubs = Club.objects.filter(
        college=request.user.college,
        status='pending'
    )

    return render(request, 'accounts/manage_clubs.html', {'clubs': clubs})


@login_required
def approve_club_view(request, club_id):

    if not request.user.is_college_admin:
        return redirect('dashboard')

    club = get_object_or_404(Club, id=club_id)

    if club.college != request.user.college:
        return redirect('dashboard')

    club.status = 'approved'
    club.approved_by = request.user
    club.save()

    messages.success(request, f"{club.name} approved successfully!")
    return redirect('manage_clubs')


@login_required
def my_registrations_view(request):

    registrations = EventRegistration.objects.filter(
        student=request.user
    ).select_related('event', 'event__club')

    return render(request, 'accounts/my_registrations.html', {
        'registrations': registrations
    })


@login_required
def manage_registrations_view(request):

    if not request.user.is_club_admin:
        return redirect('dashboard')

    user_clubs = Club.objects.filter(
        admin=request.user,
        college=request.user.college
    )

    registrations = EventRegistration.objects.filter(
        event__club__in=user_clubs
    ).select_related('event', 'student')

    return render(request, 'accounts/manage_registrations.html', {
        'registrations': registrations
    })


@login_required
def update_registration_status(request, reg_id, action):

    if not request.user.is_club_admin:
        return redirect('dashboard')

    registration = get_object_or_404(EventRegistration, id=reg_id)

    if registration.event.club.admin != request.user:
        return redirect('dashboard')

    if action == 'approve':
        registration.status = 'approved'
    elif action == 'reject':
        registration.status = 'rejected'

    registration.reviewed_by = request.user
    registration.save()

    messages.success(request, "Updated successfully!")
    return redirect('manage_registrations')

import uuid

@login_required
def scan_qr_view(request, event_id, token):

    if request.user.is_student:
        return render(request, 'accounts/scan_result.html', {
            'error': 'Access denied ❌'
        })

    # 🔥 FIX: CLEAN UUID TOKEN
    try:
        clean_token = str(uuid.UUID(token))
    except ValueError:
        return render(request, 'accounts/scan_result.html', {
            'error': 'Invalid QR Code ❌'
        })

    # ✅ GET EVENT
    event = get_object_or_404(Event, id=event_id)

    # 🔒 STRICT ROLE-BASED ACCESS

    # CLUB ADMIN → ONLY their events
    if request.user.is_club_admin:
        if event.club.admin != request.user:
            return render(request, 'accounts/scan_result.html', {
                'error': 'You can only scan your club events ❌'
            })

    # COLLEGE ADMIN → ONLY college-created events
    elif request.user.is_college_admin:
        if event.club.admin is not None:
            return render(request, 'accounts/scan_result.html', {
                'error': 'You cannot scan club events ❌'
            })

    # 🔥 GET REGISTRATION
    registration = get_object_or_404(
        EventRegistration,
        qr_token=clean_token,
        event=event
    )

    # 🔒 Prevent duplicate scan
    if registration.is_attended:
        return render(request, 'accounts/scan_result.html', {
            'error': 'Already checked-in ⚠️'
        })

    registration.is_attended = True
    registration.save()

    return render(request, 'accounts/scan_result.html', {
        'registration': registration
    })

@login_required
def qr_scanner_view(request, event_id):

    if request.user.is_student:
        return redirect('dashboard')

    event = get_object_or_404(Event, id=event_id)

    # 🔒 CLUB ADMIN → ONLY their events
    if request.user.is_club_admin:
        if event.club.admin != request.user:
            return redirect('dashboard')

    # 🔒 COLLEGE ADMIN → ONLY college-created events
    elif request.user.is_college_admin:
        if event.club.admin is not None:
            return redirect('dashboard')

    return render(request, 'accounts/scanner.html', {
        'event_id': event_id
    })

@login_required
def attendance_list_view(request):

    if not (request.user.is_club_admin or request.user.is_college_admin):
        return redirect('dashboard')

    selected_event_id = request.GET.get('event')

    # 🔥 ROLE-BASED EVENTS
    if request.user.is_club_admin:
        user_clubs = Club.objects.filter(admin=request.user)
        events = Event.objects.filter(club__in=user_clubs)

    elif request.user.is_college_admin:
        events = Event.objects.filter(club__college=request.user.college)

    registrations = EventRegistration.objects.none()

    if selected_event_id:

        if request.user.is_club_admin:
            registrations = EventRegistration.objects.filter(
                event_id=selected_event_id,
                event__club__in=user_clubs
            ).select_related('student', 'event')

        elif request.user.is_college_admin:
            registrations = EventRegistration.objects.filter(
                event_id=selected_event_id,
                event__club__college=request.user.college
            ).select_related('student', 'event')

    return render(request, 'accounts/attendance_list.html', {
        'events': events,
        'registrations': registrations,
        'selected_event_id': selected_event_id
    })

@login_required
def export_attendance(request):

    if not (request.user.is_club_admin or request.user.is_college_admin):
        return redirect('dashboard')

    # 🔥 ROLE-BASED DATA
    if request.user.is_club_admin:
        user_clubs = Club.objects.filter(admin=request.user)
        registrations = EventRegistration.objects.filter(
            event__club__in=user_clubs
        ).select_related('student', 'event')

    elif request.user.is_college_admin:
        registrations = EventRegistration.objects.filter(
            event__club__college=request.user.college
        ).select_related('student', 'event')

    data = []

    for r in registrations:
        data.append({
            'Student': r.student.username,
            'Event': r.event.title,
            'Attended': 'Yes' if r.is_attended else 'No'
        })

    df = pd.DataFrame(data)

    response = HttpResponse(content_type='application/vnd.ms-excel')
    response['Content-Disposition'] = 'attachment; filename="attendance.xlsx"'

    df.to_excel(response, index=False)

    return response

@login_required
def manage_registrations_view(request):

    if not (request.user.is_club_admin or request.user.is_college_admin):
        return redirect('dashboard')

    selected_event_id = request.GET.get('event')

    # 🔥 ROLE-BASED EVENTS
    if request.user.is_club_admin:
        user_clubs = Club.objects.filter(admin=request.user)
        events = Event.objects.filter(club__in=user_clubs)

    elif request.user.is_college_admin:
        events = Event.objects.filter(club__college=request.user.college)

    registrations = EventRegistration.objects.none()

    if selected_event_id:

        if request.user.is_club_admin:
            registrations = EventRegistration.objects.filter(
                event_id=selected_event_id,
                event__club__in=user_clubs
            ).select_related('student', 'event')

        elif request.user.is_college_admin:
            registrations = EventRegistration.objects.filter(
                event_id=selected_event_id,
                event__club__college=request.user.college
            ).select_related('student', 'event')

    return render(request, 'accounts/manage_registrations.html', {
        'events': events,
        'registrations': registrations,
        'selected_event_id': selected_event_id
    })

@login_required
def update_registration_status(request, reg_id, status):

    registration = get_object_or_404(EventRegistration, id=reg_id)

    if not (request.user.is_club_admin or request.user.is_college_admin):
        return redirect('dashboard')

    # 🔥 SECURITY CHECK
    if request.user.is_club_admin:
        if registration.event.club.admin != request.user:
            return redirect('dashboard')

    elif request.user.is_college_admin:
        if registration.event.club.college != request.user.college:
            return redirect('dashboard')

    registration.status = status
    registration.reviewed_by = request.user
    registration.save()

    messages.success(request, f"Registration {status} successfully.")

    return redirect('manage_registrations')

@login_required
def update_event_status(request, event_id, action):

    event = get_object_or_404(Event, id=event_id)

    # 🔒 SECURITY
    if not request.user.is_college_admin:
        return redirect('dashboard')

    # ✅ FIXED SAFETY CHECK
    if event.club and event.club.college != request.user.college:
        return redirect('dashboard')

    # 🔥 ACTION LOGIC
    if action == 'approve':
        event.is_approved = True
        event.is_active = True
        messages.success(request, "Event approved successfully ✅")

    elif action == 'reject':
        event.is_approved = False
        event.is_active = False
        messages.error(request, "Event rejected ❌")

    elif action == 'cancel':
        event.is_active = False
        messages.warning(request, "Event cancelled 🚫")

    event.save()

    return redirect('events')