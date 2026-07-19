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

Use o probe de roteamento físico antes do comando por speaker:

```bash
python -m tiresias_benchmark exp02-output-probe \
  --config experiments/exp02_brir_measurement/config.yaml \
  --output-index 0 \
  --session-id exp02_route_check \
  --armed \
  --overwrite
```

Repita para `--output-index 1` e `--output-index 2`.

Resultado esperado:

- `0`: somente Neumann A;
- `1`: somente Neumann B;
- `2`: somente referência elétrica, sem som acústico.

Se `output-index 2` for ouvido nos monitores, o canal de referência/loopback
está sendo monitorado em tempo real. Corrija o Focusrite Control ou o direct
monitoring antes de medir BRIR.

## Parece que A vem stereo

Há duas situações diferentes:

- se o sinal aparece nos dois Earthworks, isso é normal: uma fonte física chega
  aos dois microfones;
- se o sinal toca nos dois Neumanns, isso é erro de roteamento ou monitor mix.

O comando `exp02-channel-probe --speaker A` ativa o speaker A e também a cópia
de referência. Portanto ele não isola os canais físicos. Para testar isolamento,
use `exp02-output-probe`.

## Proteção contra áudio acidental

Comandos que emitem áudio exigem `--armed`. Sem isso, a aplicação aborta antes
de abrir a reprodução real.

Use `--simulate` para validar escrita de arquivos sem hardware.
