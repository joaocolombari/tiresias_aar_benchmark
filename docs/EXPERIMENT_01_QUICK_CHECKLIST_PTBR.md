# Checklist Rápido: Experimento 1

## Antes de ligar a aquisição

- [ ] Abrir o repo:
  `cd /Users/joaovitor/developer/tiresias_aar_workspace/tiresias_aar_benchmark`
- [ ] Ativar ambiente:
  `source .venv/bin/activate`
- [ ] Conferir CLI:
  `python -m tiresias_benchmark --help`
- [ ] Conferir config:
  `experiments/exp01_orientation_characterization/config.yaml`
- [ ] Confirmar 0° físico.
- [ ] Confirmar que 360° retorna ao mesmo ponto físico de 0°.
- [ ] Confirmar sentido positivo: `clockwise` ou `counterclockwise`.
- [ ] Tiresias preso rigidamente à cabeça.
- [ ] Cabos sem torque na base.
- [ ] Microfones, Scarlett e alto-falantes desligados ou ignorados; eles não são usados.

## Piloto obrigatório

- [ ] Plataforma em 0°.
- [ ] Aguardar 3 s.
- [ ] Rodar:

```bash
python -m tiresias_benchmark telemetry-record \
  --output experiments/exp01_orientation_characterization/raw/pilot_0deg.csv \
  --duration-s 10
```

- [ ] CSV criado.
- [ ] Quaternion com norma próxima de 1.
- [ ] `calibrated_yaw_deg` próximo de 0° após tare.
- [ ] Intervalos BLE plausíveis.
- [ ] Sem desconexão.

## Aquisição

- [ ] Rodar aquisição guiada crescente:

```bash
python -m tiresias_benchmark exp01-guided-acquire \
  --config experiments/exp01_orientation_characterization/config.yaml \
  --run ascending \
  --no-drift
```

- [ ] Confirmar mensagens: conectou, tarou, mover para ângulo, estabilizando, medindo.
- [ ] Completar ascending: `0, 10, ..., 350, 360`.
- [ ] Marcar 360° de ascending como fechamento.
- [ ] Processar `processed/segmented_ascending_*.csv` antes de continuar.
- [ ] Rodar aquisição guiada decrescente:

```bash
python -m tiresias_benchmark exp01-guided-acquire \
  --config experiments/exp01_orientation_characterization/config.yaml \
  --run descending \
  --no-drift
```

- [ ] Completar descending: `360, 350, ..., 10, 0`.
- [ ] Marcar 0° final de descending como fechamento.
- [ ] Processar `processed/segmented_descending_*.csv` antes de continuar.
- [ ] Rodar aquisição guiada aleatória:

```bash
python -m tiresias_benchmark exp01-guided-acquire \
  --config experiments/exp01_orientation_characterization/config.yaml \
  --run randomized \
  --no-drift
```

- [ ] Completar randomized com a ordem da seed `20260713`.
- [ ] Marcar 360° final de randomized como fechamento.
- [ ] Processar `processed/segmented_randomized_*.csv` antes de desmontar.
- [ ] Se necessário, medir deriva estática de 120 s antes e/ou depois como gravações separadas.

## Ordem aleatória atual

```text
280, 140, 350, 300, 180, 70, 130, 20, 330, 100, 90, 270,
80, 190, 210, 310, 290, 30, 340, 10, 250, 110, 170, 160,
150, 240, 120, 0, 220, 40, 60, 320, 50, 260, 200, 230, 360
```

## Antes de desmontar

- [ ] Confirmar que os CSVs `processed/segmented_ascending_*.csv`,
      `processed/segmented_descending_*.csv` e
      `processed/segmented_randomized_*.csv` foram criados.
- [ ] Conferir 36 direções únicas por run.
- [ ] Conferir fechamento de cada run.
- [ ] Conferir duração/amostras de cada segmento.
- [ ] Conferir quaternions.
- [ ] Processar métricas:

```bash
python -m tiresias_benchmark experiment-run \
  --experiment 1 \
  --config experiments/exp01_orientation_characterization/config.yaml \
  --telemetry-csv experiments/exp01_orientation_characterization/processed/segmented_ascending_YYYYMMDD_HHMMSS.csv \
  --output experiments/exp01_orientation_characterization/metrics/exp01_metrics.json
```

- [ ] Se o drift estiver grande, gerar análise pós-hoc derivada sem alterar o
      CSV bruto:

```bash
python -m tiresias_benchmark exp01-drift-correct \
  --config experiments/exp01_orientation_characterization/config.yaml \
  --input experiments/exp01_orientation_characterization/processed/segmented_ascending_YYYYMMDD_HHMMSS.csv \
  --output-csv experiments/exp01_orientation_characterization/processed/segmented_ascending_drift_corrected.csv \
  --output-json experiments/exp01_orientation_characterization/metrics/exp01_ascending_drift_corrected_metrics.json
```

- [ ] Backup dos CSVs brutos, CSV segmentado, config e notas.
