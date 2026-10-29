// Default ESP32 Blink Sketch
// Blinks onboard LED (GPIO 2) every 1 second and reports status via Serial

#define LED_PIN 2

void setup() {
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);
  delay(1000);
  Serial.println("\n==================================");
  Serial.println("ESP32 Blink Firmware Running!");
  Serial.println("Blinking onboard LED on GPIO 2");
  Serial.println("==================================");
}

void loop() {
  digitalWrite(LED_PIN, HIGH);
  Serial.println("[ESP32] LED is ON");
  delay(1000);
  
  digitalWrite(LED_PIN, LOW);
  Serial.println("[ESP32] LED is OFF");
  delay(1000);
}

