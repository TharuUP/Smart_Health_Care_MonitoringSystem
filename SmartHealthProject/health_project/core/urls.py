from django.urls import path
from . import views

urlpatterns = [
    # --- Auth & Home ---
    path('', views.home_view, name='home'),
    path('login/', views.login_view, name='login-page'),
    path('logout/', views.logout_view, name='logout-page'),
    
    # --- ADMIN DASHBOARD ---
    path('dashboard/admin/', views.admin_dashboard_view, name='admin-dashboard'),
    
    # --- ADMIN MANAGEMENT PAGES ---
    path('dashboard/admin/doctors/', views.admin_doctors_view, name='admin-doctors'),
    path('dashboard/admin/patients/', views.admin_patients_view, name='admin-patients'),
    path('dashboard/admin/users/', views.admin_users_view, name='admin-users'),

    # --- PATIENT URLs ---
    path('dashboard/patient/', views.patient_dashboard_view, name='patient-dashboard'),
    path('patient/history/', views.patient_history_view, name='patient-history'),
    path('patient/medications/', views.patient_medications_view, name='patient-medications'),
    path('patient/settings/', views.patient_settings_view, name='patient-settings'),
    path('patient/password/', views.patient_password_view, name='patient-password'),
    path('patient/sos/', views.send_sos_view, name='send-sos'),
    
    # --- FIX: LIVE DATA API (Used by JavaScript Polling) ---
    path('patient/live-data/', views.get_patient_live_data, name='patient-live-data'),

    # --- DOCTOR URLs ---
    path('dashboard/doctor/', views.doctor_dashboard_view, name='doctor-dashboard'),
    path('dashboard/add_prescription/', views.add_prescription_view, name='add-prescription'),
    
    # Doctor Utilities (Notes)
    path('dashboard/add_note/', views.add_note_view, name='add-note'),
    path('dashboard/delete_note/<int:note_id>/', views.delete_note_view, name='delete-note'),

    # Doctor: Patient Detail & Settings
    path('dashboard/patient/<int:patient_id>/', views.patient_detail_view, name='patient-detail'),
    
    # Shared Settings
    path('settings/', views.settings_view, name='settings'),
    path('settings/password/', views.password_settings_view, name='password-settings'),

    # --- API ---
    path('api/submit_data/', views.api_submit_data, name='api-submit-data'),
]