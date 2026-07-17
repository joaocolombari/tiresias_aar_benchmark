# Como Executar o Experimento 2

Este experimento mede as respostas impulsivas binaurais da bancada. Ele não usa
BLE. A orientação do Tiresias não entra neste procedimento: a posição da cabeça
é definida pela plataforma física.

O objetivo é obter:

```text
h_{speaker, ear, theta}
```

para cada Neumann, cada Earthworks e cada ângulo físico da cabeça.

## 1. Montagem

Roteamento nominal da Scarlett:

| Porta | Uso |
|---|---|
| input 1 | Earthworks L |
| input 2 | Earthworks R |
| stream input 3 | referência elétrica |
| output 1 | Neumann A |
| output 2 | Neumann B |
| output 3 | cópia elétrica do sweep |

Regras:

- apenas um Neumann toca por sweep;
- output 3 copia o sinal enviado ao Neumann ativo;
- a referência elétrica deve ser linha, sem phantom power;
- phantom power fica ligado somente nos Earthworks;
- direct monitoring/mixes internos da Scarlett devem ficar desligados;
- os ganhos dos canais não mudam durante a campanha.

## 2. Plano

Ângulos físicos:

```text
0, 10, 20, ..., 350, 360 graus
```

O 360 graus é fechamento. Ele continua como `theta_360` nos arquivos.

Total:

- 37 blocos angulares;
- 2 Neumanns;
- 2 repetições por Neumann;
- 148 sweeps;
- 296 IRs esperadas.

Ordem por bloco:

- índice angular par: `A1, B1, A2, B2`;
- índice angular ímpar: `B1, A1, B2, A2`.

## 3. Configuração no Mac

O arquivo principal já está configurado para macOS/Core Audio:

```text
experiments/exp02_brir_measurement/config.yaml
```

Campos relevantes:

```yaml
audio_device:
  preferred_host_api: "Core Audio"
  input_device_name_contains: "Scarlett"
  output_device_name_contains: "Scarlett"
  open_input_channel_count: 4
  open_output_channel_count: 4
  stream_dtype: auto
  stream_dtype_candidates:
    - float32
  storage_dtype: float32
```

Se o PortAudio listar a Scarlett com outro nome, ajuste
`input_device_name_contains` e `output_device_name_contains`. Se ela for o
único dispositivo Core Audio com canais suficientes, pode usar strings vazias.

## 4. Preparação do ambiente

```bash
cd /Users/joaovitor/developer/tiresias_aar_workspace/tiresias_aar_benchmark
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[acquisition,metrics,dev]"
```

## 5. Comandos

Gere/confira o plano:

```bash
python -m tiresias_benchmark experiment-run \
  --experiment 2 \
  --config experiments/exp02_brir_measurement/config.yaml
```

Liste os dispositivos:

```bash
python -m tiresias_benchmark exp02-audio-list-devices \
  --config experiments/exp02_brir_measurement/config.yaml
```

Teste o formato de stream:

```bash
python -m tiresias_benchmark exp02-audio-format-probe \
  --config experiments/exp02_brir_measurement/config.yaml \
  --output experiments/exp02_brir_measurement/metrics/audio_format_probe.json
```

Rode o preflight full-duplex com saída zero:

```bash
python -m tiresias_benchmark exp02-audio-preflight \
  --config experiments/exp02_brir_measurement/config.yaml \
  --output experiments/exp02_brir_measurement/metrics/audio_preflight.json
```

Teste sem hardware:

```bash
python -m tiresias_benchmark exp02-channel-probe \
  --config experiments/exp02_brir_measurement/config.yaml \
  --speaker A \
  --simulate \
  --overwrite
```

Probe real de canal, em nível baixo:

```bash
python -m tiresias_benchmark exp02-channel-probe \
  --config experiments/exp02_brir_measurement/config.yaml \
  --speaker A \
  --session-id exp02_probe_001 \
  --armed
```

Repita para `--speaker B`.

Primeiro sweep piloto:

```bash
python -m tiresias_benchmark exp02-record-test-sweep \
  --config experiments/exp02_brir_measurement/config.yaml \
  --speaker A \
  --angle 0 \
  --repetition 1 \
  --session-id exp02_pilot_001 \
  --armed
```

## 6. Artefatos por tentativa

Cada tentativa gera:

```text
raw_input.wav
playback_output.wav
metadata.json
callback_timeline.csv
qc.json
```

`raw_input.wav` tem três canais float32:

```text
[ear_L, ear_R, electrical_reference]
```

Esse arquivo entra na deconvolução.

## 7. Checklist antes da campanha

- [ ] Scarlett selecionada em Core Audio.
- [ ] Inputs 1/2 recebem Earthworks L/R.
- [ ] Referência elétrica aparece no canal configurado.
- [ ] Output 1 toca somente Neumann A.
- [ ] Output 2 toca somente Neumann B.
- [ ] Output 3 copia o sweep do Neumann ativo.
- [ ] Nenhum canal clipa.
- [ ] Rep01 e rep02 do piloto são parecidas.
- [ ] 0 graus e 360 graus foram conferidos fisicamente.

## 8. QC

Reprovar uma tentativa se houver:

- clipping;
- xrun/overflow/underflow;
- ausência da referência elétrica;
- speaker errado ativo;
- ambos os speakers ativos;
- ruído excessivo;
- alteração física da montagem durante o sweep;
- IR sem chegada direta plausível.

Não sobrescreva tentativas ruins. Repita como nova tentativa.
