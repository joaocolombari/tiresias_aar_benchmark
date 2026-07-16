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

- [ ] Gravar deriva inicial em 0° por 120 s.
- [ ] Gravar ascending: `0, 10, ..., 350, 360`.
- [ ] Marcar 360° de ascending como fechamento.
- [ ] Gravar descending: `360, 350, ..., 10, 0`.
- [ ] Marcar 0° final de descending como fechamento.
- [ ] Gravar randomized com a ordem da seed `20260713`.
- [ ] Marcar 360° final de randomized como fechamento.
- [ ] Gravar deriva final em 0° por 120 s.

## Ordem aleatória atual

```text
280, 140, 350, 300, 180, 70, 130, 20, 330, 100, 90, 270,
80, 190, 210, 310, 290, 30, 340, 10, 250, 110, 170, 160,
150, 240, 120, 0, 220, 40, 60, 320, 50, 260, 200, 230, 360
```

## Antes de desmontar

- [ ] Criar `processed/segmented_orientation.csv`.
- [ ] Conferir 36 direções únicas por run.
- [ ] Conferir fechamento de cada run.
- [ ] Conferir duração/amostras de cada segmento.
- [ ] Conferir quaternions.
- [ ] Processar métricas:

```bash
python -m tiresias_benchmark experiment-run \
  --experiment 1 \
  --config experiments/exp01_orientation_characterization/config.yaml \
  --output experiments/exp01_orientation_characterization/metrics/exp01_metrics.json
```

- [ ] Backup dos CSVs brutos, CSV segmentado, config e notas.
