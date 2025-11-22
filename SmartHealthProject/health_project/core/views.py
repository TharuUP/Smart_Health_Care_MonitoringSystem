from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from .models import Doctor, Patient, SensorReading, Prescription, PatientNote
from django.utils import timezone
from datetime import timedelta
from django.http import JsonResponse
import json
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Avg
import asyncio
import telegram
from django.conf import settings

# --- TELEGRAM CONFIGURATION ---
BOT_TOKEN = settings.TELEGRAM_BOT_TOKEN

# --- Helper to send Telegram Messages ---
async def send_async_msg(chat_id, msg):
    try:
        bot = telegram.Bot(token=BOT_TOKEN)
        await bot.send_message(chat_id=chat_id, text=msg, parse_mode='Markdown')
    except Exception as e:
        print(f"Telegram Error: {e}")

def send_telegram(chat_id, msg):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(send_async_msg(chat_id, msg))
        loop.close()
    except Exception as e:
        print(f"Async Error: {e}")

# ==========================================
# AUTHENTICATION & HOME
# ==========================================

def login_view(request):
    error = None
    if request.method == "POST":
        username_from_form = request.POST.get('username')
        password_from_form = request.POST.get('password')
        user = authenticate(request, username=username_from_form, password=password_from_form)
        
        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            error = "Invalid username or password. Please try again."

    context = {'error': error}
    return render(request, 'core/login.html', context)

def logout_view(request):
    logout(request)
    return redirect('login-page')

@login_required(login_url='login-page')
def home_view(request):
    user = request.user
    if hasattr(user, 'doctor'):
        return redirect('doctor-dashboard')
    elif hasattr(user, 'patient'):
        return redirect('patient-dashboard')
    elif user.is_superuser:
        return redirect('admin-dashboard')
    else:
        return redirect('/admin')

# ==========================================
# ADMIN VIEWS
# ==========================================

@login_required(login_url='login-page')
def admin_dashboard_view(request):
    if not request.user.is_superuser:
        return redirect('home')
        
    total_doctors = Doctor.objects.count()
    total_patients = Patient.objects.count()
    total_prescriptions = Prescription.objects.count()
    total_readings = SensorReading.objects.count()
    
    users_queryset = User.objects.order_by('-date_joined')[:5]
    recent_users = []
    for u in users_queryset:
        if u.is_superuser: u.role_type = 'admin'
        elif hasattr(u, 'doctor'): u.role_type = 'doctor'
        elif hasattr(u, 'patient'): u.role_type = 'patient'
        else: u.role_type = 'staff'
        recent_users.append(u)
    
    # Check if system is online (any reading in last 30s)
    last_reading = SensorReading.objects.order_by('-timestamp').first()
    system_status = "Offline"
    if last_reading and last_reading.timestamp > (timezone.now() - timedelta(seconds=30)):
        system_status = "Online"

    context = {
        'user': request.user,
        'total_doctors': total_doctors,
        'total_patients': total_patients,
        'total_prescriptions': total_prescriptions,
        'total_readings': total_readings,
        'recent_users': recent_users,
        'system_status': system_status,
        'today_date': timezone.now()
    }
    return render(request, 'core/admin_dashboard.html', context)

@login_required(login_url='login-page')
def admin_doctors_view(request):
    if not request.user.is_superuser: return redirect('home')
    doctors = Doctor.objects.all()
    return render(request, 'core/admin_manage_doctors.html', {'doctors': doctors})

@login_required(login_url='login-page')
def admin_patients_view(request):
    if not request.user.is_superuser: return redirect('home')
    patients = Patient.objects.all()
    return render(request, 'core/admin_manage_patients.html', {'patients': patients})

@login_required(login_url='login-page')
def admin_users_view(request):
    if not request.user.is_superuser: return redirect('home')
    users = User.objects.all().order_by('-date_joined')
    
    for u in users:
        if u.is_superuser: u.role_label = 'Admin'
        elif hasattr(u, 'doctor'): u.role_label = 'Doctor'
        elif hasattr(u, 'patient'): u.role_label = 'Patient'
        else: u.role_label = 'Staff'
        
    return render(request, 'core/admin_manage_users.html', {'users': users})

# ==========================================
# PATIENT VIEWS
# ==========================================

@login_required(login_url='login-page')
def patient_dashboard_view(request):
    if not hasattr(request.user, 'patient'):
        return redirect('home')
    patient = request.user.patient
    
    prescriptions = Prescription.objects.filter(patient=patient).order_by('reminder_time')
    all_readings = SensorReading.objects.filter(patient=patient).order_by('-timestamp')
    latest_reading = all_readings.first()
    
    # Strict Threshold (15 Seconds)
    time_threshold = timezone.now() - timedelta(seconds=15)
    
    is_active = False
    battery = "--"
    signal = "--"
    
    if latest_reading:
        if latest_reading.timestamp > time_threshold:
            is_active = True
            
        if latest_reading.battery_level is not None:
            battery = latest_reading.battery_level
        
        signal_val = latest_reading.signal_strength
        if signal_val is not None:
            if signal_val > -50: signal = "Excellent"
            elif signal_val > -70: signal = "Good"
            elif signal_val > -85: signal = "Weak"
            else: signal = "Poor"
        
    context = {
        'user': request.user,
        'patient': patient,
        'prescriptions': prescriptions[:5],
        'latest_reading': latest_reading,
        'is_active': is_active, 
        'battery': battery,
        'signal': signal,
        'all_readings': all_readings[:5],
        'today_date': timezone.now()
    }
    return render(request, 'core/patient_dashboard.html', context)

# --- API for Patient Dashboard Polling (Live Updates) ---
@login_required(login_url='login-page')
def get_patient_live_data(request):
    if not hasattr(request.user, 'patient'):
        return JsonResponse({})

    patient = request.user.patient
    reading = SensorReading.objects.filter(patient=patient).order_by('-timestamp').first()
    time_threshold = timezone.now() - timedelta(seconds=15)
    
    data = {
        'is_active': False, 'heart_rate': '--', 'body_temp': '--',
        'room_temp': '--', 'humidity': '--', 'battery': '--', 'signal': '--'
    }

    if reading:
        if reading.timestamp > time_threshold:
            data['is_active'] = True
        
        data['heart_rate'] = int(reading.heart_rate)
        data['body_temp'] = round(reading.body_temperature, 1)
        if reading.room_temperature: data['room_temp'] = round(reading.room_temperature, 1)
        if reading.humidity: data['humidity'] = int(reading.humidity)
        if reading.battery_level: data['battery'] = reading.battery_level
        
        sig = reading.signal_strength
        if sig:
            if sig > -50: data['signal'] = "Excellent"
            elif sig > -70: data['signal'] = "Good"
            elif sig > -85: data['signal'] = "Weak"
            else: data['signal'] = "Poor"

    return JsonResponse(data)

@login_required(login_url='login-page')
def send_sos_view(request):
    if hasattr(request.user, 'patient'):
        patient = request.user.patient
        doctor = patient.doctor
        
        if doctor and doctor.telegram_chat_id:
            last_reading = SensorReading.objects.filter(patient=patient).order_by('-timestamp').first()
            time_threshold = timezone.now() - timedelta(minutes=1)
            diagnosis = "✅ **Sensors seem operational.** Patient initiated alert manually."
            
            if not last_reading:
                diagnosis = "⚠️ **CRITICAL:** No data has ever been received from this device."
            elif last_reading.timestamp < time_threshold:
                diagnosis = "⚠️ **CRITICAL: DEVICE OFFLINE**\nLast data received over 1 minute ago."
            
            msg = (
                f"🚨 **SOS: EMERGENCY ALERT** 🚨\n\n"
                f"**Patient:** {patient.user.first_name} {patient.user.last_name}\n"
                f"**Contact:** {patient.contact_number}\n\n"
                f"**SYSTEM DIAGNOSTIC:**\n{diagnosis}"
            )
            send_telegram(doctor.telegram_chat_id, msg)
            messages.success(request, "Emergency Alert sent to Dr. " + doctor.user.last_name)
        else:
            messages.error(request, "Error: Your doctor has not set up Telegram alerts.")
            
    return redirect('patient-dashboard')

@login_required(login_url='login-page')
def patient_history_view(request):
    if not hasattr(request.user, 'patient'): return redirect('home')
    patient = request.user.patient
    readings = SensorReading.objects.filter(patient=patient).order_by('-timestamp')
    return render(request, 'core/patient_history.html', {'readings': readings})

@login_required(login_url='login-page')
def patient_medications_view(request):
    if not hasattr(request.user, 'patient'): return redirect('home')
    patient = request.user.patient
    prescriptions = Prescription.objects.filter(patient=patient).order_by('reminder_time')
    return render(request, 'core/patient_medications.html', {'prescriptions': prescriptions})

@login_required(login_url='login-page')
def patient_settings_view(request):
    if not hasattr(request.user, 'patient'): return redirect('home')
    patient = request.user.patient
    user = request.user
    if request.method == "POST":
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.email = request.POST.get('email')
        user.save()
        patient.contact_number = request.POST.get('contact_number')
        patient.occupation = request.POST.get('occupation')
        patient.address = request.POST.get('address')
        patient.age = request.POST.get('age')
        patient.blood_type = request.POST.get('blood_type')
        if request.FILES.get('profile_photo'):
            patient.profile_photo = request.FILES['profile_photo']
        patient.save()
        return redirect('patient-settings')
    return render(request, 'core/patient_settings.html', {'patient': patient, 'user': user})

@login_required(login_url='login-page')
def patient_password_view(request):
    if not hasattr(request.user, 'patient'): return redirect('home')
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Password updated successfully!')
            return redirect('patient-password')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'core/patient_password.html', {'form': form})

# ==========================================
# DOCTOR VIEWS
# ==========================================

@login_required(login_url='login-page')
def doctor_dashboard_view(request):
    if not hasattr(request.user, 'doctor'):
        return redirect('home')
    
    doctor = request.user.doctor
    all_my_patients = Patient.objects.filter(doctor=doctor)
    
    patients_data = {}
    time_threshold = timezone.now() - timedelta(seconds=15)

    for p in all_my_patients:
        last_reading = SensorReading.objects.filter(patient=p).last()
        is_active = False
        
        if last_reading and last_reading.timestamp > time_threshold:
            is_active = True
            
        status_text = "Active Monitoring" if is_active else "Not Active"
        status_color = "text-green-500" if is_active else "text-red-500"

        try:
            notes = PatientNote.objects.filter(patient=p).order_by('-created_at')
            notes_list = [{'id': n.id, 'text': n.text, 'date': n.created_at.strftime('%d/%m')} for n in notes]
        except:
            notes_list = []
        
        patients_data[p.id] = {
            'id': p.id,
            'name': f"{p.user.first_name} {p.user.last_name}",
            'age': p.age,
            'blood': p.blood_type if p.blood_type else "--",
            'contact': p.contact_number if p.contact_number else "--",
            'occupation': p.occupation if p.occupation else "--",
            'address': p.address if p.address else "--",
            'condition': p.medical_condition if p.medical_condition else "Healthy",
            'photo': p.user.first_name[0] if p.user.first_name else "P",
            'photo_url': p.profile_photo.url if p.profile_photo else "", 
            'initial': p.user.first_name[0] if p.user.first_name else "P",
            'heart_rate': int(last_reading.heart_rate) if last_reading else "--",
            'temp': round(last_reading.body_temperature, 1) if last_reading else "--",
            'room_temp': round(last_reading.room_temperature, 1) if last_reading and last_reading.room_temperature else "--",
            'humidity': int(last_reading.humidity) if last_reading and last_reading.humidity else "--",
            'notes': notes_list,
            'status': status_text,       
            'status_color': status_color
        }

    all_readings = SensorReading.objects.filter(patient__in=all_my_patients)
    avg_hr = all_readings.aggregate(Avg('heart_rate'))['heart_rate__avg']
    avg_temp = all_readings.aggregate(Avg('body_temperature'))['body_temperature__avg']

    context = {
        'user': request.user,
        'doctor': doctor,
        'patients': all_my_patients,
        'total_patients': all_my_patients.count(),
        'today_date_display': timezone.now().strftime("%A, %B %d, %Y"),
        'patients_data_json': json.dumps(patients_data),
        'avg_hr': int(avg_hr) if avg_hr else "--",
        'avg_temp': round(avg_temp, 1) if avg_temp else "--",
    }
    return render(request, 'core/doctor_dashboard.html', context)

@login_required(login_url='login-page')
def add_prescription_view(request):
    if request.method == "POST":
        patient_id = request.POST.get('patient_id')
        med_name = request.POST.get('medicine_name')
        dose = request.POST.get('dose')
        time = request.POST.get('reminder_time')
        if patient_id:
            patient = get_object_or_404(Patient, id=patient_id)
            Prescription.objects.create(patient=patient, doctor=request.user.doctor, medicine_name=med_name, dose=dose, reminder_time=time)
    return redirect('doctor-dashboard')

@login_required(login_url='login-page')
def patient_detail_view(request, patient_id):
    if not hasattr(request.user, 'doctor'): return redirect('home')
    patient = get_object_or_404(Patient, id=patient_id)
    if patient.doctor != request.user.doctor: return redirect('doctor-dashboard') 
    if request.method == "POST":
        med_name = request.POST.get('medicine_name')
        dose = request.POST.get('dose')
        time = request.POST.get('reminder_time')
        Prescription.objects.create(patient=patient, doctor=request.user.doctor, medicine_name=med_name, dose=dose, reminder_time=time)
        return redirect('patient-detail', patient_id=patient.id)
    prescriptions = Prescription.objects.filter(patient=patient).order_by('reminder_time')
    all_readings = SensorReading.objects.filter(patient=patient).order_by('-timestamp')
    context = {'patient': patient, 'prescriptions': prescriptions, 'all_readings': all_readings}
    return render(request, 'core/patient_detail.html', context)

@csrf_exempt
def api_submit_data(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            key = data.get('api_key')
            hr = data.get('heart_rate')
            temp = data.get('body_temperature')
            room_temp = data.get('room_temperature')
            humidity = data.get('humidity')
            battery = data.get('battery_level')
            signal = data.get('signal_strength')

            try:
                patient = Patient.objects.get(api_key=key)
            except Patient.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Invalid API Key'}, status=403)

            SensorReading.objects.create(
                patient=patient,
                heart_rate=hr,
                body_temperature=temp,
                room_temperature=room_temp,
                humidity=humidity,
                battery_level=battery,
                signal_strength=signal
            )
            return JsonResponse({'status': 'success', 'message': 'Data received'})
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)

@login_required(login_url='login-page')
def settings_view(request):
    if not hasattr(request.user, 'doctor'): return redirect('home')
    doctor = request.user.doctor
    user = request.user
    if request.method == "POST":
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.email = request.POST.get('email')
        user.save()
        doctor.contact_number = request.POST.get('contact_number')
        doctor.specialty = request.POST.get('specialty')
        doctor.working_hours = request.POST.get('working_hours')
        doctor.date_of_birth = request.POST.get('date_of_birth')
        doctor.blood_type = request.POST.get('blood_type')
        if request.FILES.get('profile_photo'):
            doctor.profile_photo = request.FILES['profile_photo']
        doctor.save()
        return redirect('settings')
    context = {'doctor': doctor, 'user': user}
    return render(request, 'core/settings.html', context)

@login_required(login_url='login-page')
def password_settings_view(request):
    if not hasattr(request.user, 'doctor'): return redirect('home')
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password was successfully updated!')
            return redirect('password-settings')
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        form = PasswordChangeForm(request.user)
    context = {'form': form, 'user': request.user}
    return render(request, 'core/password_settings.html', context)

@csrf_exempt
def add_note_view(request):
    if request.method == "POST":
        data = json.loads(request.body)
        patient_id = data.get('patient_id')
        text = data.get('text')
        patient = Patient.objects.get(id=patient_id)
        note = PatientNote.objects.create(patient=patient, doctor=request.user.doctor, text=text)
        return JsonResponse({'status': 'success', 'note_id': note.id, 'date': note.created_at.strftime('%d/%m')})
    return JsonResponse({'status': 'error'})

def delete_note_view(request, note_id):
    note = get_object_or_404(PatientNote, id=note_id)
    if note.doctor == request.user.doctor:
        note.delete()
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'})