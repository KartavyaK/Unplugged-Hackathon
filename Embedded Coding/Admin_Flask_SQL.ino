#include <WiFi.h>
#include <HTTPClient.h>

const char* ssid = "********";
const char* password = "********";
const char* serverUrl = "http://SERVER_IP_ADD:5000/data";

WiFiServer server(80);
WiFiClient client;

int rfid, aqi;
float lat, lon;


struct SensorValues {
  int card_detected;
  float latitude;
  float longitude;
  int AQIValue;
};
SensorValues sensors;

void setup() {
  Serial.begin(115200);
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) delay(500);

  server.begin();
  Serial.println(WiFi.localIP());
}

void loop() {
  if (!client || !client.connected()) {
    client = server.available(); // wait for client
  }

  if (client && client.connected()) {
    
    if (client.available() >= sizeof(sensors)) {
      client.read((uint8_t*)&sensors, sizeof(sensors));
    } 

    rfid = sensors.card_detected;
    lat = sensors.latitude;
    lon = sensors.longitude;
    aqi = sensors.AQIValue;

    Serial.print("Card: ");
    Serial.print(rfid);
    Serial.print(" || Lat: ");
    Serial.print(lat, 6);
    Serial.print(" || Lon: ");
    Serial.println(lon, 6);
    Serial.print(" || AQI: ");
    Serial.println(aqi);

    sendToFlask(rfid, lat, lon, aqi);
    checkCommand();

    delay(500);
  }
}

void checkCommand() {
  HTTPClient http;
  http.begin("http://SERVER_IP_ADD:5000/get_command");

  int code = http.GET();
  if (code == 200) {
    String payload = http.getString();

    if (payload.indexOf("MOVE") > 0) {
      Serial.println("MOVE CAR");
      // motor forward code
    }
    else if (payload.indexOf("STOP") > 0) {
      Serial.println("STOP CAR");
      // motor stop code
    }
  }

  http.end();
}

void sendToFlask(int rfid, float lat, float lon, int aqi) {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;

    http.begin(serverUrl);
    http.addHeader("Content-Type", "application/json");

    String json = "{";
    json += "\"rfid\":" + String(rfid) + ",";
    json += "\"lat\":" + String(lat, 6) + ",";
    json += "\"lon\":" + String(lon, 6) + ",";
    json += "\"aqi\":" + String(aqi);
    json += "}";

    int responseCode = http.POST(json);

    Serial.println("Sent JSON:");
    Serial.println(json);
    Serial.print("Response: ");
    Serial.println(responseCode);

    http.end();
  }
}
