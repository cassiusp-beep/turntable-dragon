// Dragon automaton: Elegoo Uno R3 + L298N H-bridge + DC gear motor on the camshaft.
// The laptop sends "S<0-100>\n" over USB (how much "anguish" it sees). 0 = calm, 100 = screaming.
// If the laptop goes quiet for 2 s, the dragon idles slowly. Optional knob on A0 sets the top speed (USE_KNOB).
//
// Wiring (turntable, 6 V wall adapter):
//   adapter + -> H-bridge "12V" terminal, adapter - -> H-bridge GND   (motor supply, ~4 V reaches the motor)
//   Uno 5V   -> H-bridge "5V" terminal  (logic only; 5V-EN jumper cap OFF; NO bridge wire between 12V and 5V)
//   Uno GND  -> H-bridge GND (shared ground)
//   D9 -> ENA (ENA jumper cap off), D7 -> IN1, D8 -> IN2, OUT1/OUT2 -> motor. The Uno is powered by the laptop USB.
//   USB-only fallback: Uno 5V -> 12V terminal + short 12V->5V bridge wire, no adapter. Set SUPPLY_V back to 5.0.

const int ENA = 9, IN1 = 7, IN2 = 8, KNOB = A0;

// ---- set these to match your parts ----
const float SUPPLY_V = 6.0;   // volts on the L298N 12V terminal (6 V adapter; was 5.0 on Uno USB power)
const float MOTOR_V  = 6.0;   // Mini-300 gearmotor: 3-7.2 V
const float DROP_V   = 2.0;   // the L298N loses about 2 V
const int   IDLE_PCT = 15;    // how fast the dragon moves when nobody is screaming (0-100)
const int   MIN_PWM  = 120;   // ~1.9 V at the motor on 6 V (USB needed 150 for the same); idle ~PWM 140 = ~2.2 V;
                              // raise it if the dragon stalls at idle, lower it if idle is too fast
const bool  USE_KNOB = false; // true if you wired a knob to A0 (outer legs 5V/GND, middle A0)

int maxPwm;                   // never send the motor more than ~MOTOR_V
int currentPwm = 0;
int anguish = 0;              // last value from the laptop, 0-100
unsigned long lastMsg = 0;
String buf = "";

void setup() {
  pinMode(ENA, OUTPUT); pinMode(IN1, OUTPUT); pinMode(IN2, OUTPUT);
  digitalWrite(IN1, HIGH); digitalWrite(IN2, LOW);   // if the wave runs head -> tail, swap the motor wires
  float v = SUPPLY_V - DROP_V;
  maxPwm = (v <= MOTOR_V) ? 255 : (int)(255.0 * MOTOR_V / v);
  Serial.begin(115200);
}

void readLaptop() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n') {
      if (buf.length() > 1 && buf[0] == 'S') {
        anguish = constrain(buf.substring(1).toInt(), 0, 100);
        lastMsg = millis();
      }
      buf = "";
    } else if (buf.length() < 8) {
      buf += c;
    }
  }
}

void loop() {
  readLaptop();
  int pct = (millis() - lastMsg < 2000) ? max(IDLE_PCT, anguish) : IDLE_PCT;  // laptop gone -> idle
  int topPwm = USE_KNOB ? map(analogRead(KNOB), 0, 1023, 0, maxPwm) : maxPwm;  // knob = speed limit
  int target = (topPwm < MIN_PWM) ? 0 : map(pct, 0, 100, MIN_PWM, topPwm);   // knob all the way down = off
  currentPwm += constrain(target - currentPwm, -4, 4);                       // smooth ramps, kind to the cams
  analogWrite(ENA, currentPwm);
  delay(10);
}
