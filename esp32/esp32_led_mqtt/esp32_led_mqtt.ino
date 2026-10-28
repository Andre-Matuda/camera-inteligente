// ESP32-WROOM-32: Wi-Fi + MQTT (comando 'B' do detector.py) + servidor TCP/HTTP na porta 80 + Serial.
// Recebe 'B' por qualquer um dos caminhos abaixo e acende o LED por 3 s:
//   1) MQTT: tópico MQTT_TOPICO (é o que o pc/detector.py usa)
//   2) TCP/HTTP na porta 80 (byte 'B' ou página web) - funciona só na rede local
//   3) Monitor Serial: digite B, 1, 2 ou 3
//
// Comandos (gravidade -> padrão de piscadas do LED):
//   1 = LEVE   : pisca lento   (a cada 600 ms) por 3 s
//   2 = MEDIO  : pisca medio   (a cada 250 ms) por 4 s
//   3 = GRAVE  : pisca rapido  (a cada  80 ms) por 5 s
//   B = LED aceso fixo por 3 s (teste)
//
// Bibliotecas: PubSubClient (Gerenciador de Bibliotecas, versão 2.8 ou superior).
// Substitua SSID e senha pelos dados reais da sua rede de 2,4 GHz.
// O ESP32 precisa de INTERNET para falar com o broker MQTT (porta 1883 liberada).

#include <WiFi.h>
#include <esp_wifi.h>
#include <PubSubClient.h>

const char* WIFI_SSID  = "Sua_rede";
const char* WIFI_SENHA = "sua_senha";

// MQTT: deve ser igual ao pc/config.py
const char* MQTT_BROKER = "broker.hivemq.com";
const int   MQTT_PORTA  = 1883;
const char* MQTT_TOPICO = "camera-esp32-x7k2/led";

const bool FORCAR_MAC = false;
uint8_t macPersonalizado[6] = {0x02, 0xA1, 0xB2, 0xC3, 0xD4, 0xE5};

const int PINO_LED = 2;
const unsigned long TEMPO_LED_MS = 3000;

WiFiServer server(80);
bool servidorIniciado = false;
bool estavaConectado = false;
unsigned long ultimaTentativa = 0;

WiFiClient clienteRede;
PubSubClient mqtt(clienteRede);
bool mqttEstavaConectado = false;
unsigned long ultimaTentativaMqtt = 0;

bool ledLigado = false;
unsigned long ledAte = 0;

// Padrão de piscadas (alerta por gravidade)
bool piscando = false;
bool estadoPisca = false;
unsigned long piscaAte = 0, piscaIntervalo = 0, piscaUltimaTroca = 0;

int canalRede = 0;
uint8_t bssidRede[6];
bool achouRede = false;

void iniciarConexao() {
  if (achouRede) {
    WiFi.begin(WIFI_SSID, WIFI_SENHA, canalRede, bssidRede);
  } else {
    WiFi.begin(WIFI_SSID, WIFI_SENHA);
  }
}

void aoEventoWiFi(WiFiEvent_t evento, WiFiEventInfo_t info) {
  if (evento == ARDUINO_EVENT_WIFI_STA_DISCONNECTED) {
    Serial.printf("Wi-Fi desconectado, motivo: %d\n",
                  info.wifi_sta_disconnected.reason);
  }
}

void piscar(int vezes, int ms) {
  for (int i = 0; i < vezes; i++) {
    digitalWrite(PINO_LED, HIGH);
    delay(ms);
    digitalWrite(PINO_LED, LOW);
    delay(ms);
  }
}

void acenderLed() {
  piscando = false;
  digitalWrite(PINO_LED, HIGH);
  ledLigado = true;
  ledAte = millis() + TEMPO_LED_MS;
  Serial.println("LED ligado por 3 segundos.");
}

bool ehComando(char c) {
  return c == 'B' || c == 'b' || c == '1' || c == '2' || c == '3';
}

void iniciarPadrao(const char* nome, unsigned long intervalo, unsigned long duracao) {
  ledLigado = false;
  piscando = true;
  estadoPisca = true;
  piscaIntervalo = intervalo;
  piscaUltimaTroca = millis();
  piscaAte = millis() + duracao;
  digitalWrite(PINO_LED, HIGH);
  Serial.printf("ALERTA %s: pisca a cada %lu ms por %lu ms\n", nome, intervalo, duracao);
}

void executarComando(char c) {
  switch (c) {
    case '1': iniciarPadrao("LEVE",  600, 3000); break;
    case '2': iniciarPadrao("MEDIO", 250, 4000); break;
    case '3': iniciarPadrao("GRAVE",  80, 5000); break;
    default:  acenderLed(); break;               // 'B'
  }
}

// ---------------- MQTT ----------------

void aoReceberMqtt(char* topico, byte* payload, unsigned int tamanho) {
  if (tamanho > 0 && ehComando((char)payload[0])) {
    Serial.printf("MQTT: recebi %c\n", (char)payload[0]);
    executarComando((char)payload[0]);
  }
}

void conectarMqtt() {
  String id = "esp32-x7k2-" + String((uint32_t)esp_random(), HEX);
  Serial.printf("Conectando ao MQTT %s:%d ... ", MQTT_BROKER, MQTT_PORTA);
  if (mqtt.connect(id.c_str())) {
    Serial.println("OK");
    mqtt.subscribe(MQTT_TOPICO);
    Serial.printf("Assinando o topico: %s\n", MQTT_TOPICO);
  } else {
    Serial.printf("falhou (rc=%d). Tentando de novo em 5 s.\n", mqtt.state());
  }
}

// ---------------- Servidor TCP/HTTP ----------------

void enviarPagina(WiFiClient& client) {
  const char pagina[] = R"HTML(
<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Controle do LED ESP32</title>
<style>
body{font-family:Arial;text-align:center;margin:60px 15px;background:#f2f4f7}
button{font-size:20px;padding:16px 25px;border:0;border-radius:10px;background:#167d35;color:white}
</style>
</head>
<body>
<h1>Controle do LED ESP32</h1>
<p>Escolha o padrao de alerta do LED.</p>
<button onclick="acender('1')">LEVE</button>
<button onclick="acender('2')">MEDIO</button>
<button onclick="acender('3')">GRAVE</button>
<button onclick="acender('B')">FIXO 3s</button>
<p id="status">Pronto</p>
<script>
async function acender(c){
 const s=document.getElementById('status');
 s.textContent='Enviando comando...';
 try{
   const r=await fetch('/'+c,{cache:'no-store'});
   s.textContent=r.ok?'Comando recebido pelo ESP32!':'Erro HTTP: '+r.status;
 }catch(e){s.textContent='Falha de comunicacao com o ESP32.';}
}
</script>
</body>
</html>
)HTML";

  client.println("HTTP/1.1 200 OK");
  client.println("Content-Type: text/html; charset=utf-8");
  client.println("Connection: close");
  client.print("Content-Length: ");
  client.println(strlen(pagina));
  client.println();
  client.print(pagina);
}

void processarCliente(WiFiClient& client) {
  client.setTimeout(1500);

  // Espera os dados iniciais, sem bloquear indefinidamente.
  unsigned long inicio = millis();
  while (client.connected() && !client.available() &&
         millis() - inicio < 2000) {
    delay(1);
  }

  if (!client.available()) {
    Serial.println("Cliente conectado sem enviar dados.");
    client.stop();
    return;
  }

  // Cliente TCP simples envia somente o byte 'B' ou 'b'.
  int primeiro = client.peek();
  if (ehComando((char)primeiro)) {
    client.read();
    executarComando((char)primeiro);
    client.print("OK\n");
    client.stop();
    return;
  }

  // Navegador envia uma linha como: GET / HTTP/1.1
  String requisicao = client.readStringUntil('\n');
  requisicao.trim();
  Serial.print("Requisicao: ");
  Serial.println(requisicao);

  // Consumir os cabeçalhos HTTP até a linha vazia.
  inicio = millis();
  while (client.connected() && millis() - inicio < 1500) {
    if (!client.available()) {
      delay(1);
      continue;
    }
    String linha = client.readStringUntil('\n');
    if (linha == "\r" || linha.length() == 0) {
      break;
    }
  }

  if (requisicao.length() > 6 && requisicao.startsWith("GET /") &&
      requisicao[6] == ' ' && ehComando(requisicao[5])) {
    executarComando(requisicao[5]);
    client.println("HTTP/1.1 200 OK");
    client.println("Content-Type: text/plain; charset=utf-8");
    client.println("Connection: close");
    client.println();
    client.println("Comando executado.");
  } else if (requisicao.startsWith("GET / ") ||
             requisicao == "GET /") {
    enviarPagina(client);
  } else {
    client.println("HTTP/1.1 404 Not Found");
    client.println("Content-Type: text/plain; charset=utf-8");
    client.println("Connection: close");
    client.println();
    client.println("Pagina nao encontrada.");
  }

  delay(2);
  client.stop();
}

// ---------------- setup / loop ----------------

void setup() {
  Serial.begin(115200);
  delay(500);

  pinMode(PINO_LED, OUTPUT);
  digitalWrite(PINO_LED, LOW);

  WiFi.persistent(false);
  WiFi.mode(WIFI_STA);
  WiFi.disconnect(true, true);

  Serial.println();
  Serial.printf("Chip: %s, revisao %d, nucleos %d\n",
                ESP.getChipModel(), ESP.getChipRevision(), ESP.getChipCores());

  uint64_t efuse = ESP.getEfuseMac();
  Serial.printf("MAC de fabrica (eFuse): %04X%08X\n",
                (uint16_t)(efuse >> 32), (uint32_t)efuse);

  uint8_t macAtual[6];
  WiFi.macAddress(macAtual);
  bool macZerado = true;
  for (int i = 0; i < 6; i++) {
    if (macAtual[i] != 0) macZerado = false;
  }

  if (macZerado || FORCAR_MAC) {
    esp_wifi_set_mac(WIFI_IF_STA, macPersonalizado);
    Serial.println(macZerado
      ? "MAC zerado: usando MAC personalizado."
      : "Usando MAC personalizado (FORCAR_MAC).");
  }

  Serial.print("MAC em uso: ");
  Serial.println(WiFi.macAddress());

  WiFi.setSleep(false);
  WiFi.setTxPower(WIFI_POWER_8_5dBm);
  esp_wifi_set_protocol(WIFI_IF_STA,
      WIFI_PROTOCOL_11B | WIFI_PROTOCOL_11G | WIFI_PROTOCOL_11N);
  WiFi.onEvent(aoEventoWiFi);

  mqtt.setServer(MQTT_BROKER, MQTT_PORTA);
  mqtt.setCallback(aoReceberMqtt);
  mqtt.setSocketTimeout(4);          // não trava o loop se o broker não responder

  Serial.println();
  Serial.println("Redes encontradas:");
  int n = WiFi.scanNetworks();
  int melhorRssi = -1000;

  for (int i = 0; i < n; i++) {
    Serial.printf("%d: [%s] canal %d (%d dBm)\n",
                  i + 1, WiFi.SSID(i).c_str(),
                  WiFi.channel(i), WiFi.RSSI(i));

    if (WiFi.SSID(i) == WIFI_SSID && WiFi.RSSI(i) > melhorRssi) {
      melhorRssi = WiFi.RSSI(i);
      canalRede = WiFi.channel(i);
      memcpy(bssidRede, WiFi.BSSID(i), 6);
      achouRede = true;
    }
  }

  if (achouRede) {
    Serial.printf("Minha rede encontrada: canal %d, sinal %d dBm\n",
                  canalRede, melhorRssi);
  } else {
    Serial.println("ATENCAO: rede nao encontrada no scan.");
  }

  delay(1000);
  Serial.printf("Conectando em [%s] ...\n", WIFI_SSID);
  iniciarConexao();
  ultimaTentativa = millis();
}

void loop() {
  bool conectado = (WiFi.status() == WL_CONNECTED);

  if (conectado && !estavaConectado) {
    Serial.println("Conectado!");
    Serial.print("IP do ESP32: ");
    Serial.println(WiFi.localIP());

    if (!servidorIniciado) {
      server.begin();
      servidorIniciado = true;
      Serial.println("Servidor TCP/HTTP iniciado na porta 80.");
    }

    piscar(3, 150);
  }

  if (!conectado && estavaConectado) {
    Serial.println("Perdi a conexao com o Wi-Fi.");
  }
  estavaConectado = conectado;

  // Reconexão Wi-Fi com seleção de BSSID/canal.
  if (!conectado && millis() - ultimaTentativa > 10000) {
    ultimaTentativa = millis();
    WiFi.disconnect();
    delay(200);
    iniciarConexao();
    Serial.println("Tentando conectar de novo...");
  }

  // MQTT: conecta quando houver Wi-Fi e mantém a conexão viva.
  if (conectado) {
    if (!mqtt.connected()) {
      if (mqttEstavaConectado) {
        Serial.println("Perdi a conexao com o MQTT.");
        mqttEstavaConectado = false;
      }
      if (millis() - ultimaTentativaMqtt > 5000) {
        ultimaTentativaMqtt = millis();
        conectarMqtt();
        mqttEstavaConectado = mqtt.connected();
      }
    } else {
      mqtt.loop();
    }
  }

  if (conectado && servidorIniciado) {
    WiFiClient client = server.available();
    if (client) {
      Serial.println("Cliente conectado.");
      processarCliente(client);
    }
  }

  // Teste manual pelo Monitor Serial: digite B.
  while (Serial.available()) {
    char c = Serial.read();
    if (ehComando(c)) {
      Serial.printf("Recebi pela serial: %c\n", c);
      executarComando(c);
    }
  }

  // Padrão de piscadas: alterna o LED no intervalo da gravidade até acabar o tempo.
  if (piscando) {
    unsigned long agora = millis();
    if ((long)(agora - piscaAte) >= 0) {
      piscando = false;
      digitalWrite(PINO_LED, LOW);
      Serial.println("Alerta terminou.");
    } else if (agora - piscaUltimaTroca >= piscaIntervalo) {
      piscaUltimaTroca = agora;
      estadoPisca = !estadoPisca;
      digitalWrite(PINO_LED, estadoPisca ? HIGH : LOW);
    }
  }

  if (ledLigado && (long)(millis() - ledAte) >= 0) {
    digitalWrite(PINO_LED, LOW);
    ledLigado = false;
    Serial.println("LED desligado.");
  }
}
