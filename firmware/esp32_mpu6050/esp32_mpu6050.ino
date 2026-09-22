/*
  Smart Elderly Activity Monitoring & Fall Detection System
  ESP32 + MPU6050 Wearable Sensor Node Firmware
  
  Hardware Wiring (I2C):
    ESP32 Pin 21 -> MPU6050 SDA
    ESP32 Pin 22 -> MPU6050 SCL
    ESP32 3.3V   -> MPU6050 VCC
    ESP32 GND    -> MPU6050 GND
*/

#include <WiFi.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <ArduinoJson.h>

// Wi-Fi Credentials
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// Server Ingestion Endpoint (Update with your laptop/server IP)
const char* serverUrl = "http://192.168.1.100:8000/api/imu/stream";

// MPU6050 I2C Address
const int MPU_ADDR = 0x68;

// Sampling Configuration: 50 Hz (20ms period), 25 samples per batch window (~500ms transmission)
const int SAMPLE_RATE_HZ = 50;
const int SAMPLE_INTERVAL_MS = 1000 / SAMPLE_RATE_HZ;
const int BATCH_SIZE = 25;

struct IMUSample {
  float ax;
  float ay;
  float az;
  float gx;
  float gy;
  float gz;
};

IMUSample sampleBuffer[BATCH_SIZE];
int bufferIndex = 0;
unsigned long lastSampleTime = 0;

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n[ESP32] Initializing Smart Elderly Monitor Wearable Node...");

  // Initialize I2C bus
  Wire.begin(21, 22);
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x6B); // PWR_MGMT_1 register
  Wire.write(0);    // Wake up MPU6050
  byte error = Wire.endTransmission();
  if (error == 0) {
    Serial.println("[ESP32] MPU6050 IMU connected successfully via I2C.");
  } else {
    Serial.println("[ESP32] WARNING: Failed to communicate with MPU6050!");
  }

  // Connect to Wi-Fi
  Serial.printf("[ESP32] Connecting to Wi-Fi: %s ", ssid);
  WiFi.begin(ssid, password);
  int retry = 0;
  while (WiFi.status() != WL_CONNECTED && retry < 20) {
    delay(500);
    Serial.print(".");
    retry++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n[ESP32] Wi-Fi Connected!");
    Serial.print("[ESP32] IP Address: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\n[ESP32] Wi-Fi connection timed out. Node will attempt auto-reconnect.");
  }
}

void readMPU6050(IMUSample &sample) {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x3B); // Register for ACCEL_XOUT_H
  Wire.endTransmission(false);
  Wire.requestFrom(MPU_ADDR, 14, true);

  if (Wire.available() >= 14) {
    int16_t rawAx = Wire.read() << 8 | Wire.read();
    int16_t rawAy = Wire.read() << 8 | Wire.read();
    int16_t rawAz = Wire.read() << 8 | Wire.read();
    int16_t rawTemp = Wire.read() << 8 | Wire.read();
    int16_t rawGx = Wire.read() << 8 | Wire.read();
    int16_t rawGy = Wire.read() << 8 | Wire.read();
    int16_t rawGz = Wire.read() << 8 | Wire.read();

    // Convert to g (default ±2g scale: 16384 LSB/g)
    sample.ax = rawAx / 16384.0f;
    sample.ay = rawAy / 16384.0f;
    sample.az = rawAz / 16384.0f;

    // Convert to deg/s (default ±250 deg/s: 131.0 LSB/(deg/s))
    sample.gx = rawGx / 131.0f;
    sample.gy = rawGy / 131.0f;
    sample.gz = rawGz / 131.0f;
  }
}

void sendBatchToServer() {
  if (WiFi.status() != WL_CONNECTED) {
    return;
  }

  HTTPClient http;
  http.begin(serverUrl);
  http.addHeader("Content-Type", "application/json");

  // Create JSON document
  StaticJsonDocument<4096> doc;
  doc["device_id"] = "ESP32_NODE_01";
  doc["battery_pct"] = 85; // Can connect ADC pin to voltage divider for real battery%
  doc["rssi"] = WiFi.RSSI();

  JsonArray samplesArray = doc.createNestedArray("samples");
  for (int i = 0; i < bufferIndex; i++) {
    JsonObject s = samplesArray.createNestedObject();
    s["ax"] = sampleBuffer[i].ax;
    s["ay"] = sampleBuffer[i].ay;
    s["az"] = sampleBuffer[i].az;
    s["gx"] = sampleBuffer[i].gx;
    s["gy"] = sampleBuffer[i].gy;
    s["gz"] = sampleBuffer[i].gz;
  }

  String requestBody;
  serializeJson(doc, requestBody);

  int httpResponseCode = http.POST(requestBody);
  if (httpResponseCode > 0) {
    String response = http.getString();
    // In production, parse response: if fall confirmed, drive buzzer on GPIO 25
  } else {
    Serial.printf("[ESP32] HTTP POST failed, error: %s\n", http.errorToString(httpResponseCode).c_str());
  }

  http.end();
  bufferIndex = 0;
}

void loop() {
  unsigned long currentMillis = millis();

  if (currentMillis - lastSampleTime >= SAMPLE_INTERVAL_MS) {
    lastSampleTime = currentMillis;

    // Read IMU sample
    readMPU6050(sampleBuffer[bufferIndex]);
    bufferIndex++;

    // Transmit when window/batch is complete
    if (bufferIndex >= BATCH_SIZE) {
      sendBatchToServer();
    }
  }
}
