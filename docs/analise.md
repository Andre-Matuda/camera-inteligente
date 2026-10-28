# Análise do projeto

## 1. O que funcionou
- (ex.: o MediaPipe acompanhou o corpo com boa estabilidade a ~X FPS)
- (ex.: o classificador separou bem normal x repetitivo; métricas do treino)
- (ex.: o ESP32 acendeu o LED em ~X s após o movimento)

## 2. Erros observados
- Falsos positivos: (ex.: coçar a cabeça classificado como golpe)
- Falsos negativos: (ex.: movimento brusco longe da câmera)
- Confusão entre classes parecidas (brusco x golpe_cabeca): (ver matriz de confusão)
- Problemas de ambiente: pouca luz, braço fora do enquadramento, roupa larga, atraso do Wi-Fi/MQTT

## 3. Modificações necessárias para um ambiente real
- **Dados:** gravar com mais pessoas, ambientes, ângulos e iluminação; incluir casos reais acompanhados por profissionais.
- **Modelo:** testar modelos de sequência (LSTM/1D-CNN) e ajustar limiares de confiança por custo de erro.
- **Hardware:** câmera fixa e bem posicionada, mais de uma câmera para evitar pontos cegos, processamento em máquina dedicada.
- **Rede:** broker MQTT próprio com autenticação e TLS; reconexão automática e monitoramento.
- **Alerta:** além do LED, notificação (app/SMS) e registro dos eventos; "debounce" para evitar alertas repetidos.
- **Privacidade e legislação (LGPD):** consentimento, não armazenar vídeo (só pontos do corpo), acesso restrito aos dados.
- **Segurança:** é um sistema de apoio; não substitui supervisão humana.
