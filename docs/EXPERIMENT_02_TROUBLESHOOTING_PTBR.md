# Troubleshooting do Experimento 2

## Scarlett aparece como dois dispositivos

No Windows, o PortAudio pode representar a mesma Scarlett como:

- um dispositivo lógico somente de entrada;
- outro dispositivo lógico somente de saída.

Isso não impede full-duplex. O requisito é abrir uma única stream:

```python
sounddevice.Stream(
    device=(input_device_index, output_device_index),
    channels=(4, 4),
    samplerate=48000,
    dtype="float32",
)
```

Não abra duas streams independentes.

## Configuração observada

Na máquina de aquisição, a listagem observada foi:

```text
input index observado: 26
input name: Analogue 1 + 2 (wc4800_8214)
input host API: Windows WDM-KS
input max channels: 8

output index observado: 27
output name: Speakers (wr4800_8214)
output host API: Windows WDM-KS
output max channels: 8
```

Os índices 26 e 27 não são fixos. Eles podem mudar entre boots, drivers e
máquinas. A configuração seleciona por host API e trechos de nome:

```yaml
audio_device:
  preferred_host_api: "Windows WDM-KS"
  input_device_name_contains: "Analogue 1 + 2"
  output_device_name_contains: "Speakers"
  open_input_channel_count: 4
  open_output_channel_count: 4
  sample_rate_hz: 48000
  dtype: float32
```

Use `input_device_index_override` e `output_device_index_override` somente como
diagnóstico temporário.

## Nenhum par candidato aparece

Execute:

```bash
python -m tiresias_benchmark exp02-audio-list-devices \
  --config experiments/exp02_brir_measurement/config.yaml
```

Confira:

- se `candidate_pairs` contém o par esperado;
- se os dois dispositivos estão na mesma host API;
- se o nome do input contém `Analogue 1 + 2`;
- se o nome do output contém `Speakers`;
- se ambos têm canais suficientes para 4x4.

Se a Scarlett aparecer por ASIO como dispositivo full-duplex único, altere:

```yaml
preferred_host_api: "ASIO"
input_device_name_contains: "Scarlett"
output_device_name_contains: "Scarlett"
```

## Preflight falha

Rode:

```bash
python -m tiresias_benchmark exp02-audio-preflight \
  --config experiments/exp02_brir_measurement/config.yaml \
  --output experiments/exp02_brir_measurement/metrics/audio_preflight.json
```

O relatório separa:

- seleção do input;
- seleção do output;
- `check_input_settings`;
- `check_output_settings`;
- abertura full-duplex do par.

Falhas comuns:

- `input device not found`: ajuste `input_device_name_contains`;
- `output device not found`: ajuste `output_device_name_contains`;
- `host API mismatch`: input e output não estão na mesma API;
- `insufficient input channels`: aumente/ajuste o dispositivo de entrada;
- `insufficient output channels`: ajuste o dispositivo de saída;
- `unsupported input settings`: driver recusou 4 canais, 48 kHz ou float32;
- `unsupported output settings`: saída recusou 4 canais, 48 kHz ou float32;
- `full-duplex pair open failed`: o par foi encontrado, mas o driver recusou a
  stream simultânea.

## O canal de referência não aparece

O arquivo bruto usa canais lógicos:

```text
[ear_L, ear_R, electrical_reference]
```

No YAML atual:

```yaml
channel_selection:
  mic_left_index: 0
  mic_right_index: 1
  reference_input_index: 2
```

Esses índices são colunas do stream aberto, não necessariamente o número
impresso no painel físico da Scarlett. Se o probe mostrar a referência em outra
coluna, ajuste `reference_input_index` e documente a mudança.

## Proteção contra áudio acidental

Comandos que emitem áudio real exigem `--armed`.

Sem `--armed`, a aplicação aborta antes de abrir a stream de reprodução:

```text
Refusing to emit audio without --armed. Use --simulate for dry runs.
```

Use `--simulate` para validar arquivos e metadados sem hardware.
