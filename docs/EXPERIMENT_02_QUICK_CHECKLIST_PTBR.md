# Checklist Rapido do Experimento 2

## Antes de ligar sinal nos monitores

- [ ] Earthworks L no input 1.
- [ ] Earthworks R no input 2.
- [ ] Scarlett output 3 ligado ao canal de referência configurado.
- [ ] Phantom power ligado somente nos inputs dos Earthworks.
- [ ] Direct monitoring desligado ou totalmente fechado.
- [ ] Inputs físicos fora do monitor mix.
- [ ] Loopback/reference fora dos monitores e headphones.
- [ ] Focusrite Control sem solo, mute, dim ou mix alternativo acidental.
- [ ] Line output 1 recebe somente stream/DAW 1.
- [ ] Line output 2 recebe somente stream/DAW 2.
- [ ] Line output 3 recebe somente stream/DAW 3.
- [ ] Neumann A no output 1.
- [ ] Neumann B no output 2.
- [ ] Output 3 usado apenas como referência elétrica, não como monitor.
- [ ] Output 4 sem uso e sem roteamento audível.
- [ ] Ganhos dos Earthworks anotados e travados.
- [ ] Ganho do canal de referência anotado e sem clipping.
- [ ] 0 graus fisico fotografado.
- [ ] 360 graus conferido como fechamento visual de 0 graus.

## Plano

```bash
python -m tiresias_benchmark experiment-run \
  --experiment 2 \
  --config experiments/exp02_brir_measurement/config.yaml
```

Confirmar no resultado:

- [ ] 37 angle blocks.
- [ ] 36 orientacoes espaciais unicas.
- [ ] 148 trials planejados.
- [ ] 296 IRs esperadas.
- [ ] `brir_theta_000_spk_A_rep01` existe.
- [ ] `brir_theta_360_spk_A_rep01` existe.
- [ ] 360 tem wrapped angle 0, mas ID proprio.

## Piloto em 0 graus

- [ ] `exp02-output-probe --output-index 0`: somente Neumann A audível.
- [ ] `exp02-output-probe --output-index 1`: somente Neumann B audível.
- [ ] `exp02-output-probe --output-index 2`: referência elétrica sem som acústico.
- [ ] Sweep baixo em Neumann A usando o comando por speaker.
- [ ] Sweep baixo em Neumann B usando o comando por speaker.
- [ ] Referencia eletrica aparece no canal de referência configurado.
- [ ] Earthworks L/R capturam ambos os speakers.
- [ ] Speaker inativo permanece silencioso.
- [ ] Sinal stereo nos mics L/R entendido como normal; stereo nos monitores, não.
- [ ] Nenhum canal clipa.
- [ ] IR L/R tem chegada direta plausivel.
- [ ] Rep01 e rep02 sao semelhantes.

## Campanha oficial

Antes de iniciar:

- [ ] `SESSION_ID` oficial definido, por exemplo `exp02_campaign_20260718_001`.
- [ ] `exp02_plan.csv` aberto para seguir a ordem real.
- [ ] `--overwrite` proibido nos dados oficiais.
- [ ] Knobs, volume das Neumann, roteamento e posição dos mics congelados.
- [ ] Critério combinado: se algo físico mudar, iniciar nova sessão.

Para cada angulo:

- [ ] Plataforma posicionada e travada.
- [ ] Cabos sem torque no manequim.
- [ ] Ordem do bloco seguida pelo `plan.csv`.
- [ ] Quatro sweeps capturados.
- [ ] QC conferido antes de mover a base.
- [ ] Tentativas ruins preservadas como `attempt_XX`.

Ordem dos blocos:

- [ ] Índice par, como 0, 20, 40: `A1, B1, A2, B2`.
- [ ] Índice ímpar, como 10, 30, 50: `B1, A1, B2, A2`.
- [ ] 360 preservado como `theta_360`, não misturado com `theta_000`.

Comando base:

```bash
python -m tiresias_benchmark exp02-record-test-sweep \
  --config experiments/exp02_brir_measurement/config.yaml \
  --speaker A \
  --angle 0 \
  --repetition 1 \
  --session-id "$SESSION_ID" \
  --armed
```

Para repetir tentativa ruim:

```bash
python -m tiresias_benchmark exp02-record-test-sweep \
  --config experiments/exp02_brir_measurement/config.yaml \
  --speaker A \
  --angle 0 \
  --repetition 1 \
  --session-id "$SESSION_ID" \
  --attempt 2 \
  --armed
```

## Depois

- [ ] 148 sweeps aprovados.
- [ ] Deconvolução executada com `brir-process --session-id "$SESSION_ID"`.
- [ ] 296 IRs individuais exportadas.
- [ ] 148 arquivos estéreo de BRIR exportados.
- [ ] 0 e 360 preservados separadamente.
- [ ] `brir_processing_summary.csv` criado.
- [ ] `loopback_correlation` conferido no resumo processado.
- [ ] Validação por reconvolução executada com `brir-validate`.
- [ ] `brir_validation_summary.csv` criado.
- [ ] Métricas `cross_repetition` conferidas.
- [ ] Checksums gerados.
- [ ] `qc_summary.csv` completo.
- [ ] Sessao inteira copiada para backup fora do Git.

Comando de processamento:

```bash
python -m tiresias_benchmark brir-process \
  --config experiments/exp02_brir_measurement/config.yaml \
  --session-id "$SESSION_ID"
```

Comando de validação:

```bash
python -m tiresias_benchmark brir-validate \
  --config experiments/exp02_brir_measurement/config.yaml \
  --session-id "$SESSION_ID" \
  --mode both
```
