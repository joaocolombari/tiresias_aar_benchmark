# Checklist Rapido do Experimento 2

## Antes de ligar sinal nos monitores

- [ ] Earthworks L no input 1.
- [ ] Earthworks R no input 2.
- [ ] Scarlett output 3 ligado ao canal de referência configurado.
- [ ] Phantom power ligado somente nos inputs dos Earthworks.
- [ ] Direct monitoring desligado.
- [ ] Neumann A no output 1.
- [ ] Neumann B no output 2.
- [ ] Output 4 sem uso.
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

- [ ] Sweep baixo em Neumann A.
- [ ] Sweep baixo em Neumann B.
- [ ] Referencia eletrica aparece no canal de referência configurado.
- [ ] Earthworks L/R capturam ambos os speakers.
- [ ] Speaker inativo permanece silencioso.
- [ ] Nenhum canal clipa.
- [ ] IR L/R tem chegada direta plausivel.
- [ ] Rep01 e rep02 sao semelhantes.

## Campanha oficial

Para cada angulo:

- [ ] Plataforma posicionada e travada.
- [ ] Cabos sem torque no manequim.
- [ ] Ordem do bloco seguida pelo `plan.csv`.
- [ ] Quatro sweeps capturados.
- [ ] QC conferido antes de mover a base.
- [ ] Tentativas ruins preservadas como `attempt_XX`.

## Depois

- [ ] 148 sweeps aprovados.
- [ ] 296 IRs exportadas.
- [ ] 0 e 360 preservados separadamente.
- [ ] Checksums gerados.
- [ ] `qc_summary.csv` completo.
- [ ] Sessao inteira copiada para backup fora do Git.
