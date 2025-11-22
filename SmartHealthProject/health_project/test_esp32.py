import requests
import json
import time
import random
import os
from dotenv import load_dotenv

# 1. Load environment variables from .env file
load_dotenv()

# The URL of your API on the local server
url = "http://127.0.0.1:8000/api/submit_data/"

# 2. Get Key from hidden .env file
api_key = os.getenv('PATIENT_API_KEY')

# Safety check
if not api_key:
    print("❌ ERROR: Could not find 'PATIENT_API_KEY' in your .env file.")
    print("Please make sure you created the .env file and added your key.")
    exit()

print(f"--- Starting Full ESP32 Simulation (Secure) ---")
print(f"Target: {url}")
print(f"Patient Key: {api_key[:5]}... (Hidden for security)")
print("-----------------------------------------------")

try:
    # Start with full battery
    battery = 100
    
    while True:
        # --- GENERATE FAKE SENSOR DATA ---
        
        # MAX30102 (Heart Rate)
        heart_rate = random.randint(70, 95) 
        
        # MLX90614 (Body Temperature)
        body_temp = round(random.uniform(36.4, 37.2), 1) 
        
        # DHT22 (Room Environment)
        room_temp = round(random.uniform(24.0, 28.0), 1)
        humidity = random.randint(50, 70)
        
        # System Health (Signal Strength & Battery)
        signal = random.randint(-65, -40) # -50 is strong, -90 is weak
        
        # Simulate battery draining slowly
        if battery > 10: 
            battery -= 1
        else:
            battery = 100 # Reset to full if it gets too low
        
        # --- PREPARE PAYLOAD ---
        data = {
            "api_key": api_key,
            "heart_rate": heart_rate,
            "body_temperature": body_temp,
            "room_temperature": room_temp,
            "humidity": humidity,
            "battery_level": battery,
            "signal_strength": signal
        }

        # --- SEND TO SERVER ---
        print(f"Sending: HR={heart_rate}, Room={room_temp}C, Batt={battery}% ... ", end="")
        
        try:
            response = requests.post(url, data=json.dumps(data), headers={'Content-Type': 'application/json'})
            
            if response.status_code == 200:
                print("SUCCESS ✅")
            else:
                print(f"FAILED ❌ (Status: {response.status_code})")
                print(f"Reason: {response.text}")
                
        except requests.exceptions.ConnectionError:
            print("\n[ERROR] Could not connect. Is 'python manage.py runserver' running?")
            
        # Wait 5 seconds before next reading
        time.sleep(5) 

except KeyboardInterrupt:
    print("\nSimulation stopped.")