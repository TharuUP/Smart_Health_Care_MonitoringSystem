from django.db import models
from django.contrib.auth.models import User
import uuid

# --- Model 1: Doctor (UPDATED) ---
class Doctor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    
    # --- THIS FIELD IS REQUIRED FOR SOS ---
    telegram_chat_id = models.CharField(max_length=100, blank=True, null=True)
    
    profile_photo = models.ImageField(upload_to='doctor_photos/', null=True, blank=True)
    specialty = models.CharField(max_length=100, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    blood_type = models.CharField(max_length=5, blank=True)
    contact_number = models.CharField(max_length=20, blank=True)
    working_hours = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return f"Dr. {self.user.first_name} {self.user.last_name}"

# --- Model 2: Patient ---
class Patient(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    doctor = models.ForeignKey(Doctor, on_delete=models.SET_NULL, null=True, blank=True)
    age = models.IntegerField(null=True, blank=True)
    api_key = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    telegram_chat_id = models.CharField(max_length=100, blank=True, null=True, unique=True)
    
    blood_type = models.CharField(max_length=5, blank=True)
    contact_number = models.CharField(max_length=20, blank=True)
    occupation = models.CharField(max_length=100, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    medical_condition = models.CharField(max_length=255, blank=True, null=True)
    profile_photo = models.ImageField(upload_to='patient_photos/', null=True, blank=True)

    def __str__(self):
        return f"Patient: {self.user.first_name} {self.user.last_name}"

# --- Model 3: Sensor Readings ---
class SensorReading(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    heart_rate = models.FloatField()
    body_temperature = models.FloatField()
    room_temperature = models.FloatField(null=True, blank=True)
    humidity = models.FloatField(null=True, blank=True)
    battery_level = models.IntegerField(null=True, blank=True)
    signal_strength = models.IntegerField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Reading for {self.patient.user.username} at {self.timestamp}"

# --- Model 4: Prescriptions ---
class Prescription(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    medicine_name = models.CharField(max_length=100)
    dose = models.CharField(max_length=100) 
    reminder_time = models.TimeField()
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    def __str__(self):
        return f"{self.medicine_name} for {self.patient.user.username}"

# --- Model 5: Patient Notes ---
class PatientNote(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Note for {self.patient}: {self.text[:20]}"