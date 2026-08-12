#include <M5Stack.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <esp_task_wdt.h>
#include <mbedtls/md.h>
#include <mbedtls/base64.h>
#include "config.h"

const char* MQTT_BROKER = IOT_HUB_HOSTNAME;
const int   MQTT_PORT   = 8883;

String mqttTopic;
String generatedSasToken;

WiFiClientSecure wifiClient;
PubSubClient mqttClient(wifiClient);

bool isSeatInUse = false;
bool mqttReady   = false;

void connectWiFi();
void connectMQTT();
void sendSeatStatus(bool inUse);
void updateDisplay(bool inUse);
String generateSasToken();

String generateSasToken() {
    String resourceUri = String(IOT_HUB_HOSTNAME) + "/devices/" + String(DEVICE_ID);

    String encodedUri = "";
    for (int i = 0; i < resourceUri.length(); i++) {
        char c = resourceUri[i];
        if (c == '/') encodedUri += "%2F";
        else if (c == '=') encodedUri += "%3D";
        else encodedUri += c;
    }

    unsigned long expiry = 1900000000UL;
    String stringToSign = encodedUri + "\n" + String(expiry);

    String keyStr = String(SHARED_ACCESS_KEY);
    size_t keyLen = 32;
    unsigned char keyBytes[32];
    mbedtls_base64_decode(
        keyBytes, sizeof(keyBytes), &keyLen,
        (const unsigned char*)keyStr.c_str(), keyStr.length()
    );

    unsigned char hmacResult[32];
    mbedtls_md_context_t ctx;
    mbedtls_md_init(&ctx);
    mbedtls_md_setup(&ctx, mbedtls_md_info_from_type(MBEDTLS_MD_SHA256), 1);
    mbedtls_md_hmac_starts(&ctx, keyBytes, keyLen);
    mbedtls_md_hmac_update(&ctx,
        (const unsigned char*)stringToSign.c_str(), stringToSign.length());
    mbedtls_md_hmac_finish(&ctx, hmacResult);
    mbedtls_md_free(&ctx);

    size_t sigLen = 0;
    unsigned char sigBase64[64];
    mbedtls_base64_encode(
        sigBase64, sizeof(sigBase64), &sigLen, hmacResult, 32
    );

    String sig = "";
    for (int i = 0; i < (int)sigLen; i++) {
        char c = sigBase64[i];
        if (c == '+') sig += "%2B";
        else if (c == '=') sig += "%3D";
        else sig += c;
    }

    String sas = "SharedAccessSignature sr=" + encodedUri +
                 "&sig=" + sig +
                 "&se=" + String(expiry);

    Serial.println("Generated SAS: " + sas.substring(0, 80) + "...");
    return sas;
}

void setup() {
    M5.begin();
    Serial.begin(115200);

    esp_task_wdt_init(30, false);

    mqttTopic = "devices/" + String(DEVICE_ID) + "/messages/events/";

    M5.Lcd.fillScreen(BLACK);
    M5.Lcd.setTextColor(WHITE, BLACK);
    M5.Lcd.setTextSize(2);
    M5.Lcd.setCursor(0, 0);
    M5.Lcd.println("Aki-Chance");

    connectWiFi();

if (WiFi.status() == WL_CONNECTED) {
    generatedSasToken = generateSasToken();

    // ✅ 一時的にsetInsecureで試す
    wifiClient.setInsecure();
    wifiClient.setTimeout(60);

    mqttClient.setServer(MQTT_BROKER, MQTT_PORT);
    mqttClient.setSocketTimeout(60);
    mqttClient.setBufferSize(1024);

    connectMQTT();
}
}

void loop() {
    M5.update();

    if (mqttReady) {
        if (!mqttClient.connected()) {
            connectMQTT();
        }
        mqttClient.loop();
    }

    if (M5.BtnA.wasPressed() && !isSeatInUse) {
        isSeatInUse = true;
        sendSeatStatus(true);
        updateDisplay(true);
    }

    if (M5.BtnC.wasPressed() && isSeatInUse) {
        isSeatInUse = false;
        sendSeatStatus(false);
        updateDisplay(false);
    }

    if (M5.BtnB.wasPressed()) {
        updateDisplay(isSeatInUse);
    }

    delay(50);
    yield();
}

void connectWiFi() {
    M5.Lcd.println("Connecting WiFi...");
    Serial.println("Connecting to WiFi...");

    WiFi.disconnect(true);
    delay(500);
    WiFi.mode(WIFI_STA);
    delay(500);

    IPAddress localIP (192, 168, 129, 200);
    IPAddress gateway (192, 168, 129,  34);
    IPAddress subnet  (255, 255, 255,   0);
    IPAddress dns1    (  8,   8,   8,   8);
    IPAddress dns2    (  1,   1,   1,   1);

    bool cfg = WiFi.config(localIP, gateway, subnet, dns1, dns2);
    Serial.println("WiFi.config: " + String(cfg ? "OK" : "FAILED"));

    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    int retry = 0;
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        esp_task_wdt_reset();
        Serial.print(".");
        retry++;
        if (retry > 40) {
            Serial.println("\nFailed. status=" + String(WiFi.status()));
            M5.Lcd.println("WiFi Failed");
            return;
        }
    }

    Serial.println("\nWiFi connected!");
    Serial.println("IP      : " + WiFi.localIP().toString());
    Serial.println("Gateway : " + WiFi.gatewayIP().toString());
    Serial.println("DNS     : " + WiFi.dnsIP().toString());
    M5.Lcd.println("WiFi OK");
    M5.Lcd.println(WiFi.localIP().toString());
}

void connectMQTT() {
    String mqttUser = String(IOT_HUB_HOSTNAME)
                    + "/"
                    + String(DEVICE_ID)
                    + "/?api-version=2021-04-12";

    M5.Lcd.println("Connecting IoTHub...");
    Serial.println("Connecting to IoTHub...");
    Serial.println("MQTT User: " + mqttUser);

    int retry = 0;
    while (!mqttClient.connected()) {
        esp_task_wdt_reset();
        Serial.println("Attempting connection...");

        if (mqttClient.connect(
                DEVICE_ID,
                mqttUser.c_str(),
                generatedSasToken.c_str())) {
            mqttReady = true;
            M5.Lcd.println("IoTHub OK!");
            Serial.println("IoTHub connected!");
            updateDisplay(isSeatInUse);
        } else {
            int rc = mqttClient.state();
            Serial.print("Connection failed. rc=");
            Serial.println(rc);
            Serial.println("Waiting 10 seconds...");
            delay(10000);
            esp_task_wdt_reset();
            retry++;
            if (retry > 3) {
                mqttReady = false;
                Serial.println("IoTHub connection failed - skipping");
                M5.Lcd.println("IoTHub Failed");
                updateDisplay(isSeatInUse);
                return;
            }
        }
    }
}

void sendSeatStatus(bool inUse) {
    if (!mqttReady) {
        Serial.println("IoTHub not connected - skipping send");
        Serial.println("Local status: " + String(inUse ? "in_use" : "available"));
        return;
    }

    StaticJsonDocument<256> doc;
    doc["deviceId"]  = DEVICE_ID;
    doc["seatId"]    = SEAT_ID;
    doc["status"]    = inUse ? "in_use" : "available";
    doc["timestamp"] = millis();

    char payload[256];
    serializeJson(doc, payload);

    bool result = mqttClient.publish(mqttTopic.c_str(), payload);

    if (result) {
        Serial.println("Send successful: " + String(payload));
    } else {
        Serial.println("Send failed");
    }
}

void updateDisplay(bool inUse) {
    M5.Lcd.clear();
    M5.Lcd.setCursor(0, 0);
    M5.Lcd.setTextSize(2);
    M5.Lcd.setTextColor(WHITE, BLACK);
    M5.Lcd.println("=== Aki-Chance ===");
    M5.Lcd.println("");

    if (inUse) {
        M5.Lcd.setTextColor(RED, BLACK);
        M5.Lcd.println("  [ IN USE ]");
        M5.Lcd.println("  OCCUPIED");
    } else {
        M5.Lcd.setTextColor(GREEN, BLACK);
        M5.Lcd.println("  [ AVAILABLE ]");
        M5.Lcd.println("  VACANT");
    }

    M5.Lcd.setTextColor(WHITE, BLACK);
    M5.Lcd.println("");
    M5.Lcd.println("A:In Use  C:Available");

    M5.Lcd.setCursor(0, 220);
    M5.Lcd.setTextSize(1);
    if (mqttReady) {
        M5.Lcd.setTextColor(GREEN, BLACK);
        M5.Lcd.print("IoTHub: Connected");
    } else {
        M5.Lcd.setTextColor(YELLOW, BLACK);
        M5.Lcd.print("IoTHub: Disconnected");
    }
}
