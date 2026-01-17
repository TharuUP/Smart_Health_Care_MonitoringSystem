// =========================================================
// SMART REMOTE HEALTH MONITORING SYSTEM - ESP32 CODE
// Uses Potentiometers (GPIO 34, 35) to simulate missing sensors
// =========================================================

// --- 1. LIBRARIES & CONFIGURATION ---
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>      
#include <Adafruit_GFX.h>     
#include <Adafruit_SSD1306.h> 
#include <DHTesp.h>           
#include <Wire.h>             

// --- Define GPIO Pins (Based on Potentiometer Wiring) ---
#define DHT_PIN      16  // DHT22 Data Pin
#define BUZZER_PIN   17  // Buzzer Pin 
#define RED_LED_PIN   4  // Red LED Pin (Alert/Status)
#define GREEN_LED_PIN 2  // Green LED Pin (Connected/OK)
#define BUTTON_PIN   18  // Menu Control Button (Input)

// --- Potentiometer Analog Pins ---
#define HR_POT_PIN   34  // Potentiometer 1 for Heart Rate Simulation
#define TEMP_POT_PIN 35  // Potentiometer 2 for Body Temp Simulation

// --- WiFi & API Secrets (UPDATED WITH YOUR VALUES) ---
const char* ssid = "Wokwi-WiFi";
const char* password = ""; 
// Ngrok Public HTTPS URL + API Endpoint
const char* api_host = "https://f7fadfa51ed9.ngrok-free.app/api/submit_data/"; 
// Patient API Key from Django Admin
const char* api_key = "ad31e7c1-1444-4562-b293-fc6273e5408f"; 

// --- Object Instantiation ---
DHTesp dht;
Adafruit_SSD1306 display(128, 64, &Wire, -1); 

// --- State Management ---
enum DeviceState { INITIALIZING, CONNECTING, IDLE_MENU, CHECKING_SENSORS, SENDING_DATA };
DeviceState currentState = INITIALIZING;

// --- Data Storage ---
float envTemp = 0.0, humidity = 0.0;
float bodyTemp = 0.0;
int heartRate = 0; 
int batteryLevel = 90; 
long lastDebounceTime = 0; 
long debounceDelay = 50; 
int menuIndex = 0;
const int MAX_MENU_ITEMS = 3; 

// =========================================================
// 2. HELPER FUNCTIONS (LED, BUZZER, DISPLAY)
// =========================================================

void beep(int durationMs) {
  tone(BUZZER_PIN, 1000, durationMs); 
}

void playErrorTone() {
  for(int i=0; i<5; i++) {
    beep(50);
    delay(100);
  }
}

void setLed(int pin, bool state) {
  digitalWrite(pin, state ? HIGH : LOW);
}

void displayStatus(const char* line1, const char* line2) {
  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(0, 0);
  display.println(line1);
  display.setCursor(0, 16);
  display.setTextSize(2);
  display.println(line2);
  display.display();
}

void displayPhoneHeader(int battery, int rssi) {
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  
  // RSSI (Signal)
  int bars = map(rssi, -100, -50, 0, 4);
  if (bars < 0) bars = 0;
  
  for(int i=0; i<4; i++) {
    int height = 3 + i * 2;
    if (i < bars) {
        display.fillRect(128 - 20 + i * 4, 8 - height, 3, height, SSD1306_WHITE);
    } else {
        display.drawRect(128 - 20 + i * 4, 8 - height, 3, height, SSD1306_WHITE);
    }
  }

  // Battery
  display.setCursor(128 - 45, 0);
  display.print(battery);
  display.print("%");
}

// =========================================================
// 3. SIMULATION READING FUNCTIONS
// =========================================================

bool readDht() {
  // Read actual DHT22 sensor
  displayStatus("1. CHECKING ENV", "Reading Temp/Hum...");
  delay(1000);
  
  TempAndHumidity data = dht.getTempAndHumidity();

  if (dht.getStatus() != 0) {
    displayStatus("DHT22 ERROR", "Check Sensor (GPIO 16)");
    playErrorTone();
    return false;
  }
  
  envTemp = data.temperature;
  humidity = data.humidity;
  
  displayStatus("DHT22 SUCCESS", String(envTemp, 1) + " C / " + String(humidity, 0) + " %");
  delay(1000);
  return true;
}

bool readSimulatedBodyTemp() {
  // Read Potentiometer 2 (GPIO 35) and map value to 36.0 - 38.0 C
  displayStatus("2. SIMULATING TEMP", "Reading GPIO 35...");
  delay(500);
  
  int rawValue = analogRead(TEMP_POT_PIN);
  // Map 0-4095 range to a realistic body temp range (36.0 to 38.5)
  bodyTemp = map(rawValue, 0, 4095, 360, 385) / 10.0; 

  if (bodyTemp < 35.0) {
    displayStatus("TEMP WARNING", "Simulated data too low.");
    playErrorTone();
    return false;
  }
  
  displayStatus("TEMP SIMULATION", String(bodyTemp, 1) + " C");
  delay(1000);
  return true;
}

bool readSimulatedHeartRate() {
  // Read Potentiometer 1 (GPIO 34) and map value to 60 - 120 BPM
  displayStatus("3. SIMULATING HR", "Reading GPIO 34...");
  delay(500);
  
  int rawValue = analogRead(HR_POT_PIN);
  // Map 0-4095 range to a realistic heart rate range (60 to 120)
  heartRate = map(rawValue, 0, 4095, 60, 120); 

  if (heartRate < 50) { 
     displayStatus("HR WARNING", "Simulated data too low.");
     playErrorTone();
     return false;
  }
  
  displayStatus("HR SIMULATION", String(heartRate) + " BPM");
  delay(1000);
  return true;
}


// =========================================================
// 4. API & SYSTEM HEALTH
// =========================================================

void simulateBatteryDrain() {
    // Simulates a battery drain based on time
    if (batteryLevel > 1) {
        batteryLevel -= 1;
    } else {
        // Critical low battery
        batteryLevel = 1; 
    }
}

void sendDataToServer() {
  if (WiFi.status() != WL_CONNECTED) {
    displayStatus("API FAILED", "WiFi Lost.");
    currentState = CONNECTING;
    return;
  }
  
  displayStatus("4. TRANSMITTING", "Sending Data...");
  
  HTTPClient http;
  
  int rssi = WiFi.RSSI(); 

  // Create JSON Payload
  StaticJsonDocument<512> doc; 
  doc["api_key"] = api_key;
  doc["heart_rate"] = heartRate;
  doc["body_temperature"] = bodyTemp;
  doc["room_temperature"] = envTemp;
  doc["humidity"] = humidity;
  doc["battery_level"] = batteryLevel;
  doc["signal_strength"] = rssi;

  String jsonString;
  serializeJson(doc, jsonString);

  http.begin(api_host);
  http.addHeader("Content-Type", "application/json");
  
  int httpResponseCode = http.POST(jsonString);

  if (httpResponseCode == HTTP_CODE_OK) {
    displayStatus("TRANSMISSION OK", "Data Sent to Server!");
    setLed(GREEN_LED_PIN, HIGH);
    // Doctor Notification Check (Simulated SMS Tone on success)
    beep(50); delay(50); beep(50);
  } else {
    displayStatus("API ERROR", "Code: " + String(httpResponseCode));
    playErrorTone();
    setLed(RED_LED_PIN, HIGH);
  }
  
  http.end();
  delay(1000);
}


// =========================================================
// 5. SETUP & MAIN LOOP
// =========================================================

void setup() {
  Serial.begin(115200);
  // Pin setup
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(RED_LED_PIN, OUTPUT);
  pinMode(GREEN_LED_PIN, OUTPUT);
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  
  // Initialize I2C and DHT
  Wire.begin();
  dht.setup(DHT_PIN, DHTesp::DHT22);
  
  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    while (true) { setLed(RED_LED_PIN, HIGH); delay(500); setLed(RED_LED_PIN, LOW); delay(500); }
  }
  display.setTextWrap(true);
  display.display();
  
  displayStatus("SYSTEM INIT", "Starting WiFi...");
  currentState = CONNECTING;
}

void handleMenuInput(bool buttonPressed) {
    if (buttonPressed) {
        // Execute the currently highlighted item
        if (menuIndex == 0) {
          currentState = CHECKING_SENSORS;
        } else if (menuIndex == 1) {
          // Individual Check: Read and display Body Temp
          if(readSimulatedBodyTemp()) delay(3000); 
        } else if (menuIndex == 2) {
          // Individual Check: Read and display Heart Rate
          if(readSimulatedHeartRate()) delay(3000); 
        }
        
        // Cycle menu index for the next press
        menuIndex = (menuIndex + 1) % MAX_MENU_ITEMS; 
    }
}


void loop() {
  // --- Input Debounce Logic ---
  static bool lastButtonState = HIGH; 
  int reading = digitalRead(BUTTON_PIN);
  
  if (reading != lastButtonState) {
    lastDebounceTime = millis();
  }
  
  bool buttonPressed = false;
  if ((millis() - lastDebounceTime) > debounceDelay) {
    if (reading == LOW && lastButtonState == HIGH) {
      buttonPressed = true;
    }
  }
  lastButtonState = reading;

  // Reset LEDs unless in an error state
  if (currentState != CONNECTING && currentState != SENDING_DATA) {
      setLed(RED_LED_PIN, LOW);
      setLed(GREEN_LED_PIN, LOW);
  }
  
  // --- STATE MACHINE ---
  switch (currentState) {

    case CONNECTING: {
      WiFi.begin(ssid, password);
      int timeout = 0;
      
      while (WiFi.status() != WL_CONNECTED && timeout < 20) {
        // Fast Blinking Red/Green during connection attempt
        setLed(RED_LED_PIN, HIGH); delay(100); 
        setLed(RED_LED_PIN, LOW); setLed(GREEN_LED_PIN, HIGH); delay(100);
        setLed(GREEN_LED_PIN, LOW); 
        timeout++;
        displayStatus("CONNECTING...", "Try: " + String(timeout));
      }

      if (WiFi.status() == WL_CONNECTED) {
        setLed(RED_LED_PIN, LOW);
        setLed(GREEN_LED_PIN, HIGH); // Solid Green when connected
        displayStatus("WiFi CONNECTED", WiFi.localIP().toString());
        delay(1500);
        currentState = IDLE_MENU;
      } else {
        displayStatus("CONNECTION FAIL", "Retrying...");
        playErrorTone();
        delay(3000);
        // Loop retry handled automatically by switch case
      }
      break;
    }

    case IDLE_MENU: {
      if (buttonPressed) {
        handleMenuInput(buttonPressed);
      } else {
         display.clearDisplay();
         displayPhoneHeader(batteryLevel, WiFi.RSSI()); 

         display.setTextSize(1);
         display.setTextColor(SSD1306_WHITE);
         display.setCursor(0, 15);
         display.println(">> USE BUTTON TO CYCLE <<");
         
         for(int i = 0; i < MAX_MENU_ITEMS; i++) {
           display.setCursor(0, 30 + i * 11);
           if (i == menuIndex) {
             display.print("> ");
             display.setTextColor(SSD1306_BLACK, SSD1306_WHITE);
           } else {
             display.print("  ");
             display.setTextColor(SSD1306_WHITE);
           }
           
           if (i == 0) display.println("START FULL CHECK (Doctor)");
           if (i == 1) display.println("CHECK BODY TEMP (Pot 2)");
           if (i == 2) display.println("CHECK HEART RATE (Pot 1)");
         }
         display.display();
      }
      break;
    }
    
    case CHECKING_SENSORS: {
      // 1. Read Environment (DHT22)
      if (!readDht()) { currentState = IDLE_MENU; break; }

      // 2. Read Body Temp (MLX90614 Simulation)
      if (!readSimulatedBodyTemp()) { currentState = IDLE_MENU; break; }
      
      // 3. Read Heart Rate (MAX30102 Simulation)
      if (!readSimulatedHeartRate()) { currentState = IDLE_MENU; break; }

      // 4. If all successful, move to sending data
      currentState = SENDING_DATA;
      break;
    }

    case SENDING_DATA: {
      sendDataToServer();
      simulateBatteryDrain();
      
      currentState = IDLE_MENU;
      break;
    }
  } // end switch
  
  delay(10); 
}