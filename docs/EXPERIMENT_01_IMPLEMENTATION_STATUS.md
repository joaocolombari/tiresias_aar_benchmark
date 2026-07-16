# Status da Implementação do Experimento 1

| Capacidade exigida | Status | Arquivo e símbolo | Workaround manual | Bloqueia? |
|---|---|---|---|---|
| Configurar 0° a 360° em passos de 10° | Implementado em configuração | `experiments/exp01_orientation_characterization/config.yaml:4-8` | Nenhum | Não |
| Configurar descrição do zero físico | Implementado em configuração | `experiments/exp01_orientation_characterization/config.yaml:10-16` | Ajustar texto antes da campanha | Não |
| Configurar sentido positivo `clockwise`/`counterclockwise` | Implementado com validação | `src/tiresias_benchmark/experiments/experiment_01.py:19,120-126` | Alterar YAML e anotar no caderno | Não |
| Gerar sequência ascending | Implementado | `src/tiresias_benchmark/experiments/experiment_01.py:22-35` | Imprimir sequência ou seguir escala | Não |
| Gerar sequência descending | Implementado | `src/tiresias_benchmark/experiments/experiment_01.py:35-36` | Imprimir sequência ou seguir escala | Não |
| Gerar sequência randomized reprodutível | Implementado | `src/tiresias_benchmark/experiments/experiment_01.py:37-44` | Usar seed do YAML | Não |
| Marcar 360° como fechamento em ascending | Implementado no plano e no processamento | `src/tiresias_benchmark/experiments/experiment_01.py:60-67,169-183` | Preservar coluna `is_closure_measurement` | Não |
| Excluir fechamento das estatísticas globais | Implementado | `src/tiresias_benchmark/experiments/experiment_01.py:79-82,94-103` | Nenhum se CSV segmentado estiver correto | Não |
| Normalizar yaw para 0-360 | Implementado | `src/tiresias_benchmark/metrics/orientation.py:32-35` | Nenhum | Não |
| Calcular erro circular assinado | Implementado | `src/tiresias_benchmark/metrics/orientation.py:38-44` | Nenhum | Não |
| Testar casos 359/0, 1/360, 2/350, 348/10 | Implementado | `tests/test_orientation_circular.py:12-16` | Rodar unit tests | Não |
| Média circular | Implementado como função | `src/tiresias_benchmark/metrics/orientation.py:47-53` | Usar na segmentação externa | Não |
| Estatísticas MAE/RMSE/bias/máximo | Implementado | `src/tiresias_benchmark/metrics/orientation.py:10-29` | Nenhum | Não |
| Closure error por run | Implementado | `src/tiresias_benchmark/experiments/experiment_01.py:186-217` | CSV deve conter run/posição/closure | Não |
| Deriva em graus/minuto | Implementado como função e opcional no runner | `src/tiresias_benchmark/metrics/orientation.py:56-62`; `src/tiresias_benchmark/experiments/experiment_01.py:220-242` | Adicionar `before_csv`/`after_csv` ao config ou processar fora | Não |
| Estatística de intervalo BLE | Implementado | `src/tiresias_benchmark/metrics/telemetry.py:19-42` | Nenhum se timestamps existirem | Não |
| Perda de pacotes | Implementado somente quando `seq` existe | `src/tiresias_benchmark/metrics/telemetry.py:26-33`; `src/tiresias_benchmark/telemetry/logger.py:81-85` | Se pacote legado, reportar como indisponível | Não |
| Seleção de dispositivo BLE por nome | Implementado | `src/tiresias_benchmark/telemetry/ble_client.py:20-27,40-43` | Alterar `device_name` se exposto em config de gravação | Não |
| Seleção por endereço BLE | Ausente | `src/tiresias_benchmark/telemetry/ble_client.py:40-43` | Garantir nome único `Tiresias_DK` | Não, se só houver um Tiresias |
| Service UUID BLE | Não usado pelo host benchmark | `src/tiresias_benchmark/telemetry/decoder.py:12-13`; `src/tiresias_benchmark/telemetry/ble_client.py:77-82` | Usar characteristic UUIDs conhecidos | Não |
| Characteristic telemetry v1 | Implementado | `src/tiresias_benchmark/telemetry/decoder.py:12,46-76`; `src/tiresias_benchmark/telemetry/ble_client.py:77-79` | Nenhum | Não |
| Characteristic legado quaternion | Implementado como fallback | `src/tiresias_benchmark/telemetry/decoder.py:13,79-102`; `src/tiresias_benchmark/telemetry/ble_client.py:80-82` | Aceitar campos ausentes | Não |
| Payload 64-byte com timestamp/seq/raw IMU/yaw/calibração | Implementado no decoder | `src/tiresias_benchmark/telemetry/decoder.py:14-17,46-76` | Requer firmware que envie esse payload | Não, mas limita métricas se ausente |
| Payload legado 16-byte `<ffff>` | Implementado | `src/tiresias_benchmark/telemetry/decoder.py:17,79-102` | Sem seq/timestamp/raw yaw/calibração | Não |
| Tare automático host-side no primeiro pacote | Implementado | `src/tiresias_benchmark/orientation/calibration.py:16-39`; `src/tiresias_benchmark/telemetry/ble_client.py:45-59` | Iniciar gravação em 0° ou 360° | Sim, se operador iniciar em ângulo errado |
| Tare por teclado | Ausente | Não existe parser/comando para isso em `src/tiresias_benchmark/cli.py:198-230` | Reiniciar aquisição no 0° | Não ideal |
| Tare por BLE | Ausente | `src/tiresias_benchmark/telemetry/ble_client.py:55-88` só assina notificações | Nenhum sem mudar código/firmware | Não para estático |
| Registro CSV bruto | Implementado | `src/tiresias_benchmark/telemetry/logger.py:11-50,53-135` | Nenhum | Não |
| Segmentação por posição angular | Ausente | `src/tiresias_benchmark/cli.py:202-227` não tem comando de segmentação | Criar `processed/segmented_orientation.csv` manualmente | Sim para processamento completo |
| Prompt interativo por posição | Ausente | `src/tiresias_benchmark/cli.py:98-113` grava por duração | Usar cronômetro/anotações | Não, mas aumenta risco |
| Invalidar/repetir segmento no software | Ausente | Não há campo/CLI de invalidação em `src/tiresias_benchmark/cli.py:198-230` | Notas manuais e recriar CSV segmentado | Não |
| Resume de aquisição interrompida | Ausente | `src/tiresias_benchmark/telemetry/ble_client.py:84-88` termina por duração | Repetir run ou concatenar manualmente com cuidado | Não recomendado |
| Processamento `experiment-run --experiment 1` | Implementado | `src/tiresias_benchmark/cli.py:176-191`; `src/tiresias_benchmark/experiments/experiment_01.py:70-117` | Requer CSV segmentado | Não, se CSV existir |
| Gerador de figuras | Ausente/intencionalmente não implementado | `src/tiresias_benchmark/cli.py:194-195` | Notebook/script externo | Não para aquisição; sim para relatório |
| Testes de protocolo Exp. 1 | Implementado | `tests/test_experiment_01_protocol.py:6-26` | Rodar unit tests | Não |

## Resumo de lacunas

O Experimento 1 já possui matemática circular, configuração do protocolo,
decodificação BLE, logging e processamento de métricas sobre CSV segmentado.

O que ainda falta para uma campanha totalmente guiada por software:

- comando interativo de aquisição por posição;
- segmentação automática dos CSVs brutos;
- arquivo automático de notas do operador;
- invalidação/repetição de segmentos;
- resume;
- geração de figuras;
- preservação de tare entre vários comandos separados.
