#include <TinyGPS++.h>
#include <HardwareSerial.h>
#include <SPI.h>
#include <MFRC522.h>
#include <WiFi.h>
#include <HTTPClient.h>

const char* ssid = "********";
const char* password = "********";
const char* serverIP = "SERVER_IP_ADD"; 
WiFiClient client;

TinyGPSPlus gps;
HardwareSerial gpsSerial(2);

float latitude, longitude;

int SS_PIN = 20;
int RST_PIN = 21;
int card_detected;
MFRC522 rfid(SS_PIN, RST_PIN);

#define AQIPin 35
int AQIValue = 0;

struct SensorValues {
  float latitude;
  float longitude;
  int AQIValue;
};
SensorValues sensor;

#define PWMA 25
#define AIN1 14
#define AIN2 12

#define PWMB 33
#define BIN1 26
#define BIN2 27

#define STBY 32

#define IR1 22
#define IR2 23

float Kp = 75;
float Ki = 0;
float Kd = 10;

int error = 0, previous_error = 0;
float integral = 0;

int base_speed = 100;

bool followBlack = true;
unsigned long lastSwitchTime = 0;

void setup() {
  Serial.begin(115200);
  SPI.begin(18, 19, 23, SS_PIN); 

  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) delay(500);

  pinMode(PWMA, OUTPUT);
  pinMode(AIN1, OUTPUT);
  pinMode(AIN2, OUTPUT);

  pinMode(PWMB, OUTPUT);
  pinMode(BIN1, OUTPUT);
  pinMode(BIN2, OUTPUT);

  pinMode(STBY, OUTPUT);
  digitalWrite(STBY, HIGH);

  pinMode(IR1, INPUT);
  pinMode(IR2, INPUT);
}

void loop() {
  
  if (!client.connected()){
    client.connect(serverIP, 80);
  }

  sensor.latitude = random(-900000, 900000) / 10000.0;
  sensor.longitude = random(-1800000, 1800000) / 10000.0;
  //gps values taken random as it doesn't work under closed rooms

  sensor.AQIValue = analogRead(AQIPin);

  if (client.connected()){
    client.write((uint8_t*)&sensor, sizeof(sensor));
  }

  Serial.print("Latitude : ");
  Serial.print(sensor.latitude);
  Serial.print(" || Latitude : ");
  Serial.print(sensor.longitude);
  Serial.print(" || AQI : ");
  Serial.println(sensor.AQIValue);

  int left = digitalRead(IR1);
  int right = digitalRead(IR2);

  if (left == right && millis() - lastSwitchTime > 800) {
    followBlack = !followBlack;
    lastSwitchTime = millis();
  }

  if (followBlack) {
    if (left == 1 && right == 1) error = 0;
    else if (left == 1 && right == 0) error = -1;
    else if (left == 0 && right == 1) error = 1;
    else error = 0;
  } else {
    if (left == 0 && right == 0) error = 0;
    else if (left == 0 && right == 1) error = -1;
    else if (left == 1 && right == 0) error = 1;
    else error = 0;
  }

  integral += error;
  int derivative = error - previous_error;
  int correction = Kp * error + Ki * integral + Kd * derivative;

  int leftSpeed = base_speed + correction;
  int rightSpeed = base_speed - correction;

  leftSpeed = constrain(leftSpeed, 0, 255);
  rightSpeed = constrain(rightSpeed, 0, 255);

  digitalWrite(AIN1, HIGH);
  digitalWrite(AIN2, LOW);
  analogWrite(PWMA, leftSpeed);

  digitalWrite(BIN1, LOW);
  digitalWrite(BIN2, HIGH);
  analogWrite(PWMB, rightSpeed);

  previous_error = error;

  getCommand();
  delay(100);
}

void getCommand() {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin("http://SERVER_IP_ADD:5000/get_command");

    int code = http.GET();

    if (code == 200) {
      String payload = http.getString();

      if (payload.indexOf("STOP") != -1) {
        digitalWrite(STBY, LOW);
      }
      else if (payload.indexOf("MOVE") != -1) {
        digitalWrite(STBY, HIGH);
      }
    }

    http.end();
  }
}