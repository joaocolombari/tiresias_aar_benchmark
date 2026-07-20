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

Geometria física usada na campanha:

- zero físico: manequim olhando para a referência frontal;
- rotação positiva: sentido horário;
- Neumann A: `-30 graus`;
- Neumann B: `+30 graus`;
- distância dos Neumanns: `1.0 m` em relação ao nariz do manequim.

Regras:

- apenas um Neumann toca por sweep;
- output 3 copia o sinal enviado ao Neumann ativo;
- a referência elétrica deve ser linha, sem phantom power;
- phantom power fica ligado somente nos Earthworks;
- direct monitoring/mixes internos da Scarlett devem ficar desligados;
- os ganhos dos canais não mudam durante a campanha.

### Configuração física da Scarlett

Antes de qualquer sweep real, deixe a interface em um estado sem monitoramento
interno:

- `Direct Monitor` desligado ou totalmente fechado;
- nenhum input físico enviado para o monitor mix;
- nenhum canal de loopback/reference enviado para os monitores ou headphones;
- `Mute`, `Solo`, `Dim` e efeitos desligados no Focusrite Control;
- line output 1 recebendo somente o stream/DAW 1;
- line output 2 recebendo somente o stream/DAW 2;
- line output 3 recebendo somente o stream/DAW 3;
- output 3 conectado apenas ao input de referência, nunca a monitor/speaker;
- knobs de volume dos Neumanns baixos no primeiro teste e depois travados;
- ganhos dos inputs 1 e 2 ajustados para os Earthworks sem clipping;
- ganho do input de referência ajustado para nível forte, mas sem clipping;
- se houver seletor `Inst`, `Air` ou pad nos canais usados como linha,
  deixe em modo neutro/linha.

Use a escuta apenas como diagnóstico inicial. A evidência válida vem de
`raw_input.wav`, `playback_output.wav` e `qc.json`.

Importante: um Neumann físico deve aparecer nos dois Earthworks. Portanto,
um sinal "stereo" nos microfones L/R é esperado. O que não pode acontecer é
um teste de A tocar acusticamente também no Neumann B, ou o loopback/reference
ser ouvido nos monitores por monitoramento interno.

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

Probe real por papel lógico. Este comando ativa o speaker e também a cópia de
referência, portanto não serve para isolar canais físicos quando há suspeita
de monitoramento interno:

```bash
python -m tiresias_benchmark exp02-channel-probe \
  --config experiments/exp02_brir_measurement/config.yaml \
  --speaker A \
  --session-id exp02_probe_001 \
  --armed
```

Repita para `--speaker B`.

Probe real de roteamento físico. Este comando ativa exatamente um canal de
saída por vez e grava todos os canais de entrada abertos. Use antes dos sweeps
piloto para confirmar se A, B e loopback não estão sendo misturados pela
Scarlett:

```bash
python -m tiresias_benchmark exp02-output-probe \
  --config experiments/exp02_brir_measurement/config.yaml \
  --output-index 0 \
  --session-id exp02_route_check \
  --armed \
  --overwrite
```

Repita com `--output-index 1` e `--output-index 2`.

Interpretação esperada:

| output-index | Deve acontecer |
|---:|---|
| 0 | toca somente o Neumann A |
| 1 | toca somente o Neumann B |
| 2 | aparece somente na referência elétrica; não deve tocar nos Neumanns |

Se `output-index 2` for ouvido nos monitores, o loopback/reference está sendo
monitorado em tempo real e o roteamento da Scarlett precisa ser corrigido antes
da campanha.

Primeiro sweep piloto:

```bash
python -m tiresias_benchmark exp02-record-test-sweep \
  --config experiments/exp02_brir_measurement/config.yaml \
  --speaker A \
  --angle 0 \
  --repetition 1 \
  --session-id exp02_pilot_001 \
  --armed \
  --overwrite
```

```bash
python -m tiresias_benchmark exp02-record-test-sweep \
  --config experiments/exp02_brir_measurement/config.yaml \
  --speaker B \
  --angle 0 \
  --repetition 1 \
  --session-id exp02_pilot_001 \
  --armed \
  --overwrite 
```

## 6. Campanha oficial

Crie uma sessão nova para a campanha oficial. Use uma identificação com data e
contador, por exemplo:

```bash
SESSION_ID=exp02_campaign_20260718_001
```

Durante a campanha oficial:

- não use `--overwrite`;
- não mude ganhos, volumes, roteamento, posição dos mics ou posição das caixas;
- preserve tentativas ruins como `attempt_02`, `attempt_03`, etc.;
- se qualquer ganho ou roteamento precisar mudar, encerre a sessão e comece
  outra com novo `SESSION_ID`;
- confira o `qc.json` antes de mover a plataforma para o próximo ângulo.

O plano oficial fica em:

```text
experiments/exp02_brir_measurement/metrics/exp02_plan.csv
```

Cada linha do plano informa:

```text
angle_nominal_deg
speaker
repetition
trial_id
attempt_number
```

Siga a ordem do `plan.csv`. A lógica padrão é:

| Índice angular | Ângulo | Ordem dos quatro sweeps |
|---:|---:|---|
| par | 0, 20, 40, ... | A1, B1, A2, B2 |
| ímpar | 10, 30, 50, ... | B1, A1, B2, A2 |

O ângulo `360` é medido no final como fechamento físico. Ele não substitui o
ângulo `0` e deve gerar arquivos próprios com `theta_360`.

### Comandos por bloco angular

Para um ângulo de índice par, por exemplo `0 graus`:

```bash
python -m tiresias_benchmark exp02-record-test-sweep \
  --config experiments/exp02_brir_measurement/config.yaml \
  --speaker A \
  --angle 0 \
  --repetition 1 \
  --session-id "$SESSION_ID" \
  --armed

python -m tiresias_benchmark exp02-record-test-sweep \
  --config experiments/exp02_brir_measurement/config.yaml \
  --speaker B \
  --angle 0 \
  --repetition 1 \
  --session-id "$SESSION_ID" \
  --armed

python -m tiresias_benchmark exp02-record-test-sweep \
  --config experiments/exp02_brir_measurement/config.yaml \
  --speaker A \
  --angle 0 \
  --repetition 2 \
  --session-id "$SESSION_ID" \
  --armed

python -m tiresias_benchmark exp02-record-test-sweep \
  --config experiments/exp02_brir_measurement/config.yaml \
  --speaker B \
  --angle 0 \
  --repetition 2 \
  --session-id "$SESSION_ID" \
  --armed
```

Para um ângulo de índice ímpar, por exemplo `10 graus`, use a ordem invertida:

```bash
python -m tiresias_benchmark exp02-record-test-sweep \
  --config experiments/exp02_brir_measurement/config.yaml \
  --speaker B \
  --angle 10 \
  --repetition 1 \
  --session-id "$SESSION_ID" \
  --armed

python -m tiresias_benchmark exp02-record-test-sweep \
  --config experiments/exp02_brir_measurement/config.yaml \
  --speaker A \
  --angle 10 \
  --repetition 1 \
  --session-id "$SESSION_ID" \
  --armed

python -m tiresias_benchmark exp02-record-test-sweep \
  --config experiments/exp02_brir_measurement/config.yaml \
  --speaker B \
  --angle 10 \
  --repetition 2 \
  --session-id "$SESSION_ID" \
  --armed

python -m tiresias_benchmark exp02-record-test-sweep \
  --config experiments/exp02_brir_measurement/config.yaml \
  --speaker A \
  --angle 10 \
  --repetition 2 \
  --session-id "$SESSION_ID" \
  --armed
```

Para repetir uma tentativa ruim, use o mesmo `speaker`, `angle` e `repetition`,
mas incremente `--attempt`:

```bash
python -m tiresias_benchmark exp02-record-test-sweep \
  --config experiments/exp02_brir_measurement/config.yaml \
  --speaker B \
  --angle 10 \
  --repetition 1 \
  --session-id "$SESSION_ID" \
  --attempt 2 \
  --armed
```

### Conferência após cada bloco

Depois dos quatro sweeps de um ângulo, confira os arquivos:

```text
experiments/exp02_brir_measurement/raw/<SESSION_ID>/sweeps/
```

Para cada trial, abra ou inspecione:

```text
brir_theta_XXX_spk_A_rep01/attempt_01/qc.json
brir_theta_XXX_spk_B_rep01/attempt_01/qc.json
brir_theta_XXX_spk_A_rep02/attempt_01/qc.json
brir_theta_XXX_spk_B_rep02/attempt_01/qc.json
```

Só mova a plataforma quando:

- o canal de referência estiver presente;
- não houver clipping;
- não houver xrun/overflow/underflow;
- os dois Earthworks tiverem capturado sinal;
- o speaker ativo for o esperado;
- nenhuma configuração física tiver sido alterada.

### Pausas durante a campanha

Pode pausar entre ângulos. Ao retomar:

- não toque nos knobs;
- não reabra o Focusrite Control alterando mixes;
- confirme que a plataforma ainda está no ângulo esperado;
- rode outro sweep apenas se precisar validar que o caminho não mudou.

Se a sessão ficar suspeita, não apague nada. Comece uma nova sessão e anote o
motivo no caderno/log externo.

## 7. Artefatos por tentativa

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

## 8. Checklist antes da campanha

- [ ] Scarlett selecionada em Core Audio.
- [ ] Inputs 1/2 recebem Earthworks L/R.
- [ ] Referência elétrica aparece no canal configurado.
- [ ] Output 1 toca somente Neumann A.
- [ ] Output 2 toca somente Neumann B.
- [ ] Output 3 copia o sweep do Neumann ativo, mas não é monitorado.
- [ ] `exp02-output-probe --output-index 2` não gera som acústico.
- [ ] Nenhum canal clipa.
- [ ] Rep01 e rep02 do piloto são parecidas.
- [ ] 0 graus e 360 graus foram conferidos fisicamente.
- [ ] `SESSION_ID` oficial definido.
- [ ] `exp02_plan.csv` aberto ou impresso para acompanhamento.
- [ ] Regra de não usar `--overwrite` nos dados oficiais combinada.

## 9. Deconvolução

Depois de medir a campanha completa, gere os BRIRs com:

```bash
python -m tiresias_benchmark brir-process \
  --config experiments/exp02_brir_measurement/config.yaml \
  --session-id exp02_campaign_20260718_001
```

Se precisar regenerar os arquivos processados da mesma sessão:

```bash
python -m tiresias_benchmark brir-process \
  --config experiments/exp02_brir_measurement/config.yaml \
  --session-id exp02_campaign_20260718_001 \
  --overwrite
```

A deconvolução usa:

- `raw_input.wav` canal 1 como `ear_L`;
- `raw_input.wav` canal 2 como `ear_R`;
- `raw_input.wav` canal 3 como referência elétrica;
- regularização definida por `qc.deconvolution_lambda_fraction`;
- janela comum para L/R, sem alinhar cada orelha separadamente.
- arquivos de calibração de fábrica dos Earthworks, quando definidos em
  `microphones[*].calibration_file`, aplicados como correção inversa de
  magnitude no domínio da frequência.

Essa janela comum preserva o ITD medido. Não aplique normalização, limiter ou
alinhamento independente entre orelhas nos arquivos de BRIR.

A correção dos microfones remove a coloração de magnitude de cada Earthworks,
mas não altera a fase medida da bancada. A validação por reconvolução aplica a
mesma correção aos sinais captados antes de calcular SDR, correlação e NRMSE.

Saídas:

```text
experiments/exp02_brir_measurement/processed/<SESSION_ID>/irs/
experiments/exp02_brir_measurement/processed/<SESSION_ID>/metadata/
experiments/exp02_brir_measurement/metrics/<SESSION_ID>/brir_processing_summary.csv
experiments/exp02_brir_measurement/metrics/<SESSION_ID>/brir_processing_summary.json
```

Cada trial gera:

```text
brir_theta_XXX_spk_A_rep01_ear_L.wav
brir_theta_XXX_spk_A_rep01_ear_R.wav
brir_theta_XXX_spk_A_rep01_stereo.wav
```

O resumo contém `itd_ms`, `ild_db`, níveis RMS, `loopback_lag_ms` e
`loopback_correlation`.

Observação: o `qc.json` criado durante a aquisição pode marcar
`low_reference_correlation` porque aquele QC usa correlação sem compensar o
atraso do loopback. Para a etapa de deconvolução, use os campos
`loopback_lag_ms` e `loopback_correlation` do resumo processado.

## 10. Validação por reconvolução

Para verificar se as IRs estimadas reproduzem os sinais medidos, rode:

```bash
python -m tiresias_benchmark brir-validate \
  --config experiments/exp02_brir_measurement/config.yaml \
  --session-id exp02_campaign_20260718_001 \
  --mode both
```

O comando reconstrói a resposta esperada dos microfones por convolução:

```text
predicted_ear = electrical_reference * estimated_ir_ear
```

e compara com o `raw_input.wav` experimental. A comparação usa dois modos:

- `same_trial`: usa a IR estimada de um sweep para reconstruir o mesmo sweep;
- `cross_repetition`: usa a IR da rep01 para prever a rep02 e a IR da rep02
  para prever a rep01.

O modo `same_trial` é um limite superior, porque valida contra o mesmo dado que
gerou a IR. O modo `cross_repetition` é mais relevante para prever o desempenho
em convoluções futuras com outros sinais.

Saídas:

```text
experiments/exp02_brir_measurement/metrics/<SESSION_ID>/brir_validation_summary.csv
experiments/exp02_brir_measurement/metrics/<SESSION_ID>/brir_validation_summary.json
```

Métricas principais:

- `mean_prediction_sdr_db`: razão entre sinal medido e erro de predição;
- `mean_corr`: correlação entre sinal medido e sinal previsto;
- `mean_nrmse`: erro RMS normalizado;
- `ear_l_*` e `ear_r_*`: métricas separadas por orelha;
- `gain_corrected_sdr_db`: SDR se um ganho escalar ótimo fosse permitido.

Para exportar também WAVs de sinal previsto e resíduo:

```bash
python -m tiresias_benchmark brir-validate \
  --config experiments/exp02_brir_measurement/config.yaml \
  --session-id exp02_campaign_20260718_001 \
  --mode both \
  --write-wavs
```

Isso cria arquivos em:

```text
experiments/exp02_brir_measurement/processed/<SESSION_ID>/validation/
```

Use `--overwrite` apenas se quiser regenerar validações já processadas.

## 11. QC

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
