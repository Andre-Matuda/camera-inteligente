"""Envio do comando 'B' ao ESP32 via MQTT (o ESP32 acende o LED por 3 s)."""
import paho.mqtt.client as mqtt
import config

_cliente = None


def iniciar():
    global _cliente
    try:
        c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=config.MQTT_CLIENT_ID)

        def on_connect(client, userdata, flags, reason_code, properties):
            ok = getattr(reason_code, "value", reason_code) == 0
            print(f"MQTT conectado a {config.MQTT_BROKER}" if ok
                  else f"Falha ao conectar ao MQTT: {reason_code}")

        c.on_connect = on_connect
        c.connect(config.MQTT_BROKER, config.MQTT_PORT, keepalive=60)
        c.loop_start()
        _cliente = c
    except Exception as e:
        print(f"Erro ao iniciar MQTT: {e}")


def _publicar(cmd):
    if _cliente is None:
        print("MQTT não iniciado; comando não enviado.")
        return
    try:
        info = _cliente.publish(config.MQTT_TOPIC_LED, cmd, qos=0)
        print(f"MQTT -> {config.MQTT_TOPIC_LED}: {cmd} (rc={info.rc})")
    except Exception as e:
        print(f"Erro ao publicar MQTT: {e}")


def enviar_alerta(classe):
    """Envia o comando da gravidade da classe: '1' leve, '2' médio, '3' grave."""
    gravidade = config.GRAVIDADE_POR_CLASSE.get(classe, "medio")
    print(f"Gravidade: {gravidade.upper()}")
    _publicar(config.COMANDO_POR_GRAVIDADE[gravidade])


def piscar_led():
    """LED aceso fixo por 3 s (comando 'B', usado para teste)."""
    _publicar("B")


def parar():
    if _cliente is not None:
        try:
            _cliente.loop_stop()
            _cliente.disconnect()
        except Exception:
            pass