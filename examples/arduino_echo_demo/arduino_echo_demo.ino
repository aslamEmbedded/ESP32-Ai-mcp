/*
  ESP32 Arduino Interactive Serial Demo
  Baud Rate: 115200
  Responds to commands: PING, LED ON, LED OFF, STATUS
*/

#define LED_PIN 2

unsigned long lastHeartbeat = 0;
String inputString = "";
bool stringComplete = false;

void setup() {
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
  
  delay(1000);
  Serial.println("\n====================================");
  Serial.println("ESP32 Arduino Bridge Demo Initialized");
  Serial.println("Commands available: PING, LED_ON, LED_OFF, STATUS");
  Serial.println("====================================");
}

void loop() {
  // Read incoming serial commands
  while (Serial.available()) {
    char inChar = (char)Serial.read();
    if (inChar == '\n' || inChar == '\r') {
      if (inputString.length() > 0) {
        stringComplete = true;
      }
    } else {
      inputString += inChar;
    }
  }

  // Handle command
  if (stringComplete) {
    inputString.trim();
    inputString.toUpperCase();

    if (inputString == "PING") {
      Serial.println("[ESP32 Reply] PONG!");
    } else if (inputString == "LED_ON" || inputString == "LED ON") {
      digitalWrite(LED_PIN, HIGH);
      Serial.println("[ESP32 Reply] LED is now ON");
    } else if (inputString == "LED_OFF" || inputString == "LED OFF") {
      digitalWrite(LED_PIN, LOW);
      Serial.println("[ESP32 Reply] LED is now OFF");
    } else if (inputString == "STATUS") {
      Serial.printf("[ESP32 Reply] Uptime: %lu ms, Free Heap: %u bytes\n", millis(), ESP.getFreeHeap());
    } else {
      Serial.printf("[ESP32 Reply] Unknown command: '%s'\n", inputString.c_str());
    }

    inputString = "";
    stringComplete = false;
  }

  // Heartbeat message every 4 seconds
  if (millis() - lastHeartbeat >= 4000) {
    lastHeartbeat = millis();
    Serial.printf("[ESP32 Heartbeat] Millis: %lu | FreeHeap: %u\n", lastHeartbeat, ESP.getFreeHeap());
  }
}

