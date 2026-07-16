# Comandos do Experimento 1

Use estes comandos em ordem. Alguns passos ainda exigem trabalho manual porque
o repositório não possui comando de segmentação por posição.

## 1. Entrar no repositório

```bash
cd /Users/joaovitor/developer/tiresias_aar_workspace/tiresias_aar_benchmark
```

Saída esperada: nenhuma.

## 2. Criar ambiente, se ainda não existir

```bash
python3 -m venv .venv
```

Saída esperada: diretório `.venv/`.

## 3. Ativar ambiente

```bash
source .venv/bin/activate
```

Saída esperada: prompt com ambiente ativo.

## 4. Instalar dependências

```bash
python -m pip install -e ".[ble,metrics,dev]"
```

Saída esperada: pacote instalado em modo editável e `bleak` disponível.

## 5. Conferir CLI

```bash
python -m tiresias_benchmark --help
python -m tiresias_benchmark telemetry-record --help
python -m tiresias_benchmark experiment-run --help
```

Saída esperada: ajuda dos comandos.

## 6. Testar BLE por 3 s

```bash
python -m tiresias_benchmark telemetry-record \
  --output experiments/exp01_orientation_characterization/raw/ble_probe.csv \
  --duration-s 3
```

Entrada esperada: Tiresias ligado e anunciando como `Tiresias_DK`.

Saída esperada: `raw/ble_probe.csv`.

## 7. Piloto em 0°

```bash
python -m tiresias_benchmark telemetry-record \
  --output experiments/exp01_orientation_characterization/raw/pilot_0deg.csv \
  --duration-s 10
```

Entrada esperada: plataforma parada em 0°.

Saída esperada: `raw/pilot_0deg.csv`.

## 8. Verificar piloto

```bash
python - <<'PY'
import csv, math
p="experiments/exp01_orientation_characterization/raw/pilot_0deg.csv"
rows=list(csv.DictReader(open(p)))
print("amostras:", len(rows))
if rows:
    q=[float(rows[0][k]) for k in ("qw","qx","qy","qz")]
    print("q_norm_primeira:", math.sqrt(sum(x*x for x in q)))
    print("calibrated_yaw_inicio:", rows[0]["calibrated_yaw_deg"])
    print("calibrated_yaw_fim:", rows[-1]["calibrated_yaw_deg"])
PY
```

Saída esperada: amostras > 0, norma próxima de 1, yaw calibrado perto de 0°.

## 9. Deriva inicial

```bash
python -m tiresias_benchmark telemetry-record \
  --output experiments/exp01_orientation_characterization/raw/drift_before_0deg.csv \
  --duration-s 120
```

Entrada esperada: plataforma parada em 0°.

Saída esperada: `raw/drift_before_0deg.csv`.

## 10. Série crescente

```bash
python -m tiresias_benchmark telemetry-record \
  --output experiments/exp01_orientation_characterization/raw/ascending_raw.csv \
  --duration-s 520
```

Entrada esperada: operador segue `0, 10, ..., 350, 360` e anota tempos.

Saída esperada: `raw/ascending_raw.csv`.

## 11. Série decrescente

```bash
python -m tiresias_benchmark telemetry-record \
  --output experiments/exp01_orientation_characterization/raw/descending_raw.csv \
  --duration-s 520
```

Entrada esperada: operador segue `360, 350, ..., 10, 0` e anota tempos.

Saída esperada: `raw/descending_raw.csv`.

## 12. Imprimir sequência aleatória

```bash
python - <<'PY'
from tiresias_benchmark.cli import load_yaml
from tiresias_benchmark.experiments.experiment_01 import build_reference_sequences
cfg = load_yaml("experiments/exp01_orientation_characterization/config.yaml")
seq = build_reference_sequences(cfg)["randomized"]
print(", ".join(str(int(x["reference_angle_commanded_deg"])) for x in seq))
PY
```

Saída esperada:

```text
280, 140, 350, 300, 180, 70, 130, 20, 330, 100, 90, 270, 80, 190, 210, 310, 290, 30, 340, 10, 250, 110, 170, 160, 150, 240, 120, 0, 220, 40, 60, 320, 50, 260, 200, 230, 360
```

## 13. Série aleatória

```bash
python -m tiresias_benchmark telemetry-record \
  --output experiments/exp01_orientation_characterization/raw/randomized_raw.csv \
  --duration-s 520
```

Entrada esperada: iniciar em 0° para tare, depois seguir a ordem aleatória.

Saída esperada: `raw/randomized_raw.csv`.

## 14. Deriva final

```bash
python -m tiresias_benchmark telemetry-record \
  --output experiments/exp01_orientation_characterization/raw/drift_after_0deg.csv \
  --duration-s 120
```

Entrada esperada: plataforma parada em 0°.

Saída esperada: `raw/drift_after_0deg.csv`.

## 15. Criar CSV segmentado

Não há comando implementado para isso. Criar manualmente ou por script externo:

```text
experiments/exp01_orientation_characterization/processed/segmented_orientation.csv
```

Colunas mínimas:

```text
run_id,run_type,position_index,reference_angle_commanded_deg,reference_angle_normalized_deg,is_closure_measurement,host_monotonic_timestamp_ns,seq,calibrated_yaw_deg
```

## 16. Processar métricas

```bash
python -m tiresias_benchmark experiment-run \
  --experiment 1 \
  --config experiments/exp01_orientation_characterization/config.yaml \
  --output experiments/exp01_orientation_characterization/metrics/exp01_metrics.json
```

Entrada esperada: `processed/segmented_orientation.csv` existe.

Saída esperada: `metrics/exp01_metrics.json`.

## 17. Figuras

Não há comando implementado para gerar as figuras do Experimento 1.

O comando abaixo existe, mas aborta:

```bash
python -m tiresias_benchmark figures-generate
```
