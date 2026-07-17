# Como Executar o Experimento 2

Este procedimento descreve o Experimento 2 no repositório
`tiresias_aar_benchmark`. Ele usa como referência a aplicação nativa criada no
diretório `brian_exp_2`, mas mantém a organização do benchmark e o protocolo
científico do projeto.

## 1. Objetivo

Medir respostas impulsivas binaurais da bancada para cada posição angular do
manequim, alto-falante e repetição.

O resultado esperado da campanha completa é:

- 37 blocos angulares: `0, 10, ..., 350, 360`;
- 2 monitores: Neumann A e Neumann B;
- 2 repetições independentes por monitor;
- 148 sweeps oficiais;
- 296 respostas impulsivas, uma para cada ouvido por sweep.

A posição 360 graus é uma medição de fechamento. Ela é fisicamente equivalente
a 0 graus, mas não é o mesmo arquivo, trial ou diretório. O ID `theta_360`
deve existir para testar fechamento/repetibilidade.

## 2. O Que Este Experimento Mede

Mede:

- resposta acústica do monitor A até os microfones L/R para cada orientação;
- resposta acústica do monitor B até os microfones L/R para cada orientação;
- ITD/ILD reais da bancada, preservados pela aquisição simultânea;
- variação de nível, atraso e resposta espectral com a rotação;
- qualidade/repetibilidade das duas repetições;
- telemetria BLE auxiliar do Tiresias durante cada sweep.

Não mede:

- atenção auditiva diretamente;
- benefício perceptual;
- separação de fontes;
- desempenho em fala;
- ganho do modelo de atenção.

Essas análises usam as BRIRs depois, nos Experimentos 3 a 6.

## 3. Montagem Física

Roteamento nominal:

| Scarlett | Uso |
|---|---|
| input 1 | Earthworks L |
| input 2 | Earthworks R |
| stream input 3 | referência elétrica |
| output 1 | Neumann A |
| output 2 | Neumann B |
| output 3 | cópia elétrica do sweep para o canal de referência |

Regras importantes:

- apenas um Neumann toca por sweep;
- output 3 deve copiar exatamente o sinal enviado ao Neumann ativo;
- output 3 deve entrar no canal de referência configurado, sem phantom power;
- phantom power deve ficar ligado somente nos inputs dos Earthworks;
- direct monitoring e mixes internos da Scarlett devem ficar desligados;
- os ganhos dos dois Earthworks devem permanecer fixos durante toda a campanha;
- a posição dos microfones no manequim não pode mudar entre ângulos.

## 4. Preparação

Entre no repositório:

```bash
cd /Users/joaovitor/developer/tiresias_aar_workspace/tiresias_aar_benchmark
```

Instale o ambiente normal do benchmark. Para falar com a Scarlett via
PortAudio/ASIO, inclua o extra `acquisition`:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[acquisition,ble,metrics,dev]"
```

No Windows de aquisição, use o equivalente com `py`/PowerShell.

## 5. Gerar e Conferir o Plano

Execute:

```bash
python -m tiresias_benchmark experiment-run \
  --experiment 2 \
  --config experiments/exp02_brir_measurement/config.yaml
```

Esse comando cria:

```text
experiments/exp02_brir_measurement/metrics/exp02_plan.csv
```

Conferências obrigatórias:

- `planned_trials = 148`;
- `expected_impulse_responses = 296`;
- `first_trial_id = brir_theta_000_spk_A_rep01`;
- `last_trial_id = brir_theta_360_spk_B_rep02`;
- existem 4 linhas com `angle_nominal_deg = 0`;
- existem 4 linhas com `angle_nominal_deg = 360`;
- as linhas de 360 têm `angle_wrapped_deg = 0`, mas `trial_id` com
  `theta_360`.

## 6. Ordem de Aquisição

Em cada ângulo, capture quatro sweeps. A ordem alterna por índice angular:

| Índice angular | Ordem |
|---:|---|
| par | A rep01, B rep01, A rep02, B rep02 |
| ímpar | B rep01, A rep01, B rep02, A rep02 |

Isso reduz viés sistemático causado por aquecimento, deriva, fadiga de
operador ou ordem fixa de alto-falantes.

Não pule a posição 360. Ela é a closure measurement do experimento acústico.

## 7. Testes de Scarlett/PortAudio

Liste os dispositivos:

```bash
python -m tiresias_benchmark exp02-audio-list-devices
```

Na máquina Windows observada, a Scarlett apareceu como dois dispositivos
WDM-KS separados:

```text
input:  Analogue 1 + 2 (wc4800_8214)
output: Speakers (wr4800_8214)
API:    Windows WDM-KS
```

Isso é esperado. A aplicação deve selecionar um par input/output e abrir uma
única stream full-duplex:

```python
sounddevice.Stream(device=(input_device, output_device), channels=(4, 4))
```

Rode o preflight full-duplex com saída digital zero:

Primeiro descubra qual formato de stream o driver aceita:

```bash
python -m tiresias_benchmark exp02-audio-format-probe \
  --config experiments/exp02_brir_measurement/config.yaml \
  --output experiments/exp02_brir_measurement/metrics/audio_format_probe.json
```

O YAML atual usa:

```yaml
stream_dtype: auto
stream_dtype_candidates: [float32, int32, int16]
storage_dtype: float32
```

Se `float32` falhar com `Sample format not supported`, a aplicação tenta
`int32` e depois `int16`. Mesmo quando o stream usa inteiro, os arquivos
`raw_input.wav` e `playback_output.wav` continuam sendo salvos como float32.

Depois rode o preflight:

```bash
python -m tiresias_benchmark exp02-audio-preflight \
  --config experiments/exp02_brir_measurement/config.yaml \
  --output experiments/exp02_brir_measurement/metrics/audio_preflight.json
```

Se o driver não aceitar os canais configurados, ajuste no YAML:

```text
audio_device.preferred_host_api
audio_device.input_device_name_contains
audio_device.output_device_name_contains
audio_device.open_input_channel_count
audio_device.open_output_channel_count
audio_device.channel_selection
```

Teste o caminho de arquivos sem hardware:

```bash
python -m tiresias_benchmark exp02-channel-probe \
  --config experiments/exp02_brir_measurement/config.yaml \
  --speaker A \
  --simulate \
  --overwrite
```

Para emitir áudio real, use sempre `--armed`.

Probe real de canal, em nível baixo:

```bash
python -m tiresias_benchmark exp02-channel-probe \
  --config experiments/exp02_brir_measurement/config.yaml \
  --speaker A \
  --session-id exp02_probe_YYYYMMDD \
  --armed
```

Repita para `--speaker B`.

Primeiro sweep real em 0 graus:

```bash
python -m tiresias_benchmark exp02-record-test-sweep \
  --config experiments/exp02_brir_measurement/config.yaml \
  --speaker A \
  --angle 0 \
  --repetition 1 \
  --session-id exp02_pilot_YYYYMMDD \
  --armed
```

Cada tentativa gera:

```text
raw_input.wav
playback_output.wav
metadata.json
callback_timeline.csv
qc.json
```

O arquivo `raw_input.wav` tem tres canais: `[ear_L, ear_R,
electrical_reference]`. Ele deve entrar no passo seguinte de deconvolucao.

## 8. Sequência Operacional Recomendada

Antes da campanha:

1. Fotografe a montagem, incluindo 0 graus, posição dos microfones e
   roteamento da Scarlett.
2. Confirme serial/nome dos Earthworks e marque fisicamente L/R.
3. Confirme qual Neumann é A e qual é B.
4. Confirme o sentido positivo da plataforma.
5. Gere `exp02_plan.csv`.
6. Faça teste de canal com nível baixo.
7. Grave ruído de sala.
8. Faça piloto em 0 graus: A1, B1, A2, B2.
9. Rode deconvolução e veja as IRs do piloto antes de seguir.

Durante a campanha:

1. Coloque a plataforma no ângulo nominal exibido.
2. Aguarde estabilizar mecanicamente.
3. Confirme que o Tiresias está rigidamente preso.
4. Capture os quatro sweeps do bloco angular.
5. Confira QC antes de avançar para o próximo ângulo.
6. Se falhar, repita como nova tentativa; não sobrescreva a tentativa ruim.

Depois da campanha:

1. Faça auditoria de quantidades: 148 sweeps aprovados e 296 IRs.
2. Confira se 0 e 360 existem separadamente.
3. Compare rep01 e rep02 de cada condição.
4. Gere tabela de QC com clipping, SNR, correlação e ITD.
5. Faça backup da sessão inteira, incluindo raw, BLE, metadados e logs.

## 9. Formato dos Dados

Arquivo bruto canônico por tentativa:

```text
raw_input.wav
```

Formato:

- WAV IEEE float32;
- 48 kHz;
- três canais lógicos na ordem `[ear_L, ear_R, electrical_reference]`;
- sem normalização;
- sem limiter;
- sem remoção de DC no arquivo bruto;
- inclui pré-silêncio, sweep, pós-silêncio e padding.

Metadados mínimos por tentativa:

```text
metadata.json
callback_timeline.csv
ble_notifications.csv
qc.json
checksums.sha256
```

IRs derivadas:

```text
brir_theta_000_spk_A_rep01_ear_L.wav
brir_theta_000_spk_A_rep01_ear_R.wav
```

As IRs L/R devem usar a mesma origem temporal e a mesma janela. Não alinhe o
pico de cada ouvido separadamente; isso destruiria o ITD.

## 10. Controle de Qualidade

Reprovar uma tentativa se houver:

- clipping em qualquer Earthworks;
- clipping ou nível insuficiente na referência elétrica;
- xrun, overflow ou underflow;
- speaker errado ativo;
- ambos os speakers ativos;
- ausência de sinal no Earthworks esperado;
- BLE ausente quando a campanha tiver marcado BLE como obrigatório;
- IR sem chegada direta plausível;
- diferença grande entre rep01 e rep02;
- alteração física da montagem durante o sweep.

Critérios de aceitação iniciais estão em:

```text
experiments/exp02_brir_measurement/config.yaml
```

Eles podem ser ajustados depois do piloto, mas a configuração final deve ser
congelada antes da campanha oficial.

## 11. Dependências de Hardware

Ainda precisam ser verificados na máquina Windows:

- nomes exatos dos dispositivos PortAudio/WDM-KS ou ASIO;
- ordem real dos canais retornada pelo driver;
- correspondência entre os quatro canais abertos e a fiação física da Scarlett;
- nível seguro dos Neumanns;
- ganho adequado do loopback elétrico;
- ruído de fundo da sala;
- cauda de reverberação necessária para o pós-silêncio;
- estabilidade BLE enquanto o stream de áudio está aberto.

Uma foto da montagem só é necessária se houver dúvida sobre simetria dos
Earthworks, definição de 0 graus ou qual Neumann deve ser A/B.
