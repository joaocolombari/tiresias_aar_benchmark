# Troubleshooting do Experimento 2

## Scarlett não aparece

Rode:

```bash
python -m tiresias_benchmark exp02-audio-list-devices \
  --config experiments/exp02_brir_measurement/config.yaml
```

Procure um dispositivo Core Audio com nome contendo `Scarlett`. Se aparecer com
outro nome, edite no YAML:

```yaml
input_device_name_contains: "nome observado"
output_device_name_contains: "nome observado"
```

Se a Scarlett for o único dispositivo Core Audio com canais suficientes, use:

```yaml
input_device_name_contains: ""
output_device_name_contains: ""
```

## Preflight falha

Rode primeiro:

```bash
python -m tiresias_benchmark exp02-audio-format-probe \
  --config experiments/exp02_brir_measurement/config.yaml \
  --output experiments/exp02_brir_measurement/metrics/audio_format_probe.json
```

Depois:

```bash
python -m tiresias_benchmark exp02-audio-preflight \
  --config experiments/exp02_brir_measurement/config.yaml \
  --output experiments/exp02_brir_measurement/metrics/audio_preflight.json
```

O relatório separa:

- seleção do input;
- seleção do output;
- formato de stream;
- `check_input_settings`;
- `check_output_settings`;
- abertura full-duplex.

## Canal de referência errado

O raw esperado é:

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

Esses índices são colunas do stream Core Audio. Se o probe mostrar a referência
em outra coluna, ajuste `reference_input_index`.

## Sem som no Neumann correto

Confira:

- `speaker_A_output_index`;
- `speaker_B_output_index`;
- `reference_output_index`;
- roteamento da Scarlett;
- direct monitoring/mixes internos desligados;
- monitores em volume baixo, mas não mutados.

## Proteção contra áudio acidental

Comandos que emitem áudio exigem `--armed`. Sem isso, a aplicação aborta antes
de abrir a reprodução real.

Use `--simulate` para validar escrita de arquivos sem hardware.
