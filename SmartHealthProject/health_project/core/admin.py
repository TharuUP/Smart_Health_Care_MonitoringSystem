from django.contrib import admin
from .models import Doctor, Patient, SensorReading, Prescription

# 1. Create a custom admin view for Patients
class PatientAdmin(admin.ModelAdmin):
    # This tells Django to display these fields even if they are 'editable=False'
    readonly_fields = ('api_key',)
    
    # This determines what columns show up in the main list
    list_display = ('user', 'doctor', 'age', 'api_key')

# 2. Register your models
admin.site.register(Doctor)
admin.site.register(Patient, PatientAdmin) # Use the custom view we just made
admin.site.register(SensorReading)
admin.site.register(Prescription)