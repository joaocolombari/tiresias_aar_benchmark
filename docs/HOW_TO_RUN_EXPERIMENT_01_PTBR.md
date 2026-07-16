# Como Executar o Experimento 1

Este procedimento descreve o Experimento 1 conforme o repositório
`tiresias_aar_benchmark` existe agora. Ele não assume comandos ou telas que
ainda não foram implementados.

## 1. Objetivo do experimento

O Experimento 1 caracteriza a telemetria de orientação do Tiresias em posições
estáticas conhecidas ao longo de uma volta completa da plataforma.

Ele mede:

- acurácia angular estática;
- erro angular circular;
- repetibilidade entre séries;
- variação estacionária dentro de cada posição;
- deriva de yaw em medições estáticas;
- intervalo de atualização BLE;
- jitter das notificações;
- perda de pacotes, somente quando `seq` estiver disponível;
- erro de fechamento entre 0° e 360°.

Ele não mede:

- desempenho acústico;
- separação de fontes;
- renderização binaural;
- benefício perceptual;
- latência dinâmica absoluta ponta a ponta, pois não há referência angular
  física sincronizada independentemente.

## 2. Materiais necessários

Necessário:

- manequim;
- base giratória;
- escala angular física de 0° a 360° marcada a cada 10°;
- placa Tiresias rigidamente presa à cabeça do manequim;
- bateria ou alimentação estável para o Tiresias;
- computador com BLE;
- ambiente Python do repositório.

Não são usados neste experimento:

- microfones;
- interface Scarlett;
- alto-falantes;
- arquivos de áudio;
- respostas binaurais.

## 3. Preparação mecânica

Defina 0° como a cabeça do manequim apontando para a referência frontal
acústica do laboratório. No arquivo atual, isto está descrito como:

`Mannequin facing the acoustic frontal reference`.

A direção positiva configurada é `clockwise`. Se a marcação física do seu
setup usar o sentido anti-horário, altere o campo
`coordinate_system.positive_rotation_direction` antes de adquirir os dados e
registre essa decisão nas notas do operador. O código não inverte o sinal do
yaw automaticamente.

Procedimento mecânico:

1. Fixe a escala angular na base de modo que 0° e 360° coincidam fisicamente.
2. Alinhe um ponteiro fixo da base ao zero da escala.
3. Coloque o manequim em 0° olhando para a referência frontal.
4. Prenda o Tiresias rigidamente à cabeça. A placa não pode escorregar, girar
   ou vibrar em relação ao manequim.
5. Garanta que cabos ou alimentação não apliquem torque à cabeça ou à base.
6. Confira 360° retornando ao mesmo alinhamento visual de 0°.
7. Leia a escala sempre do mesmo ponto de vista para evitar paralaxe.
8. Fotografe a posição 0° e documente se o sentido positivo físico é horário
   ou anti-horário.

Checklist mecânico:

- [ ] 0° físico definido.
- [ ] 360° coincide com 0°.
- [ ] Sentido positivo documentado.
- [ ] Tiresias preso sem movimento relativo.
- [ ] Cabos sem torque.
- [ ] Ponteiro e escala legíveis sem paralaxe.

## 4. Preparação do software

Entre no repositório:

```bash
cd /Users/joaovitor/developer/tiresias_aar_workspace/tiresias_aar_benchmark
```

Crie e ative o ambiente:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Instale as dependências. Para BLE, é necessário o extra `ble`:

```bash
python -m pip install -e ".[ble,metrics,dev]"
```

Verifique a CLI:

```bash
python -m tiresias_benchmark --help
python -m tiresias_benchmark telemetry-record --help
python -m tiresias_benchmark experiment-run --help
```

Comandos disponíveis hoje:

- `telemetry-record`;
- `telemetry-replay`;
- `exp01-guided-acquire`;
- `sweep-generate`;
- `brir-process`;
- `experiment-run`;
- `figures-generate`.

Importante: `exp01-guided-acquire` é o comando recomendado para a campanha
física do Experimento 1. Ele guia o operador posição por posição, registra a
fase do procedimento em cada amostra e cria o CSV segmentado usado pelas
métricas.

Importante: `figures-generate` existe, mas atualmente aborta com a mensagem de
que a geração de figuras deve ser feita depois que métricas existirem. Portanto
não há gerador de figuras implementado para o Experimento 1.

Verifique BLE instalando e importando `bleak`:

```bash
python -c "import bleak; print('bleak OK')"
```

Teste se o Tiresias é descoberto pelo comando real de aquisição:

```bash
python -m tiresias_benchmark telemetry-record \
  --output experiments/exp01_orientation_characterization/raw/ble_probe.csv \
  --duration-s 3
```

Se o dispositivo for encontrado, o arquivo CSV será criado. Se não for
encontrado, o comando falhará com mensagem do tipo `BLE device matching
'Tiresias_DK' not found`.

Não existe hoje um comando dedicado para apenas listar dispositivos BLE.

## 5. Configuração do experimento

Arquivo:

`experiments/exp01_orientation_characterization/config.yaml`

Campos atuais:

| Campo | Valor atual | Significado | Alterar? |
|---|---:|---|---|
| `experiment_id` | `exp01_orientation_characterization` | Identificador do experimento | Normalmente não |
| `telemetry_csv` | `experiments/exp01_orientation_characterization/processed/segmented_orientation.csv` | CSV processado/segmentado consumido por `experiment-run` | Sim, se usar outro arquivo |
| `angular_protocol.start_deg` | `0` | Início físico da escala | Não |
| `angular_protocol.stop_deg` | `360` | Fechamento físico da escala | Não |
| `angular_protocol.step_deg` | `10` | Passo angular | Não |
| `angular_protocol.include_closure_endpoint` | `true` | Preserva 360° como fechamento | Não |
| `coordinate_system.zero_direction_description` | texto | Define o 0° físico | Sim, se a referência mudar |
| `coordinate_system.positive_rotation_direction` | `clockwise` | Sentido positivo físico configurado | Sim, se a escala for anti-horária |
| `coordinate_system.reference_angle_range_deg` | `[0, 360]` | Intervalo físico | Não |
| `coordinate_system.reference_angle_step_deg` | `10` | Passo físico | Não |
| `coordinate_system.telemetry_yaw_input_range` | `minus_180_to_180` | Convenção esperada do yaw de entrada | Só documenta; não muda cálculo |
| `coordinate_system.comparison_range` | `zero_to_360` | Faixa usada para comparação | Não |
| `acquisition.settling_time_s` | `3` | Tempo de estabilização após mover | Ajustável |
| `acquisition.recording_time_s` | `10` | Tempo de registro por posição | Ajustável |
| `acquisition.discard_initial_s` | `2` | Trecho descartado em cada posição | Ajustável |
| `acquisition.analyzed_stationary_interval_s` | `8` | Trecho analisado | Ajustável |
| `acquisition.repetitions` | `3` | Três séries completas | Não |
| `runs` | ascending, descending, randomized | Séries do protocolo | Não |
| `randomized_run.seed` | `20260713` | Seed reprodutível da série aleatória | Sim, se precisar nova ordem |
| `randomized_run.append_closure_measurement_deg` | `360` | Fechamento final da série aleatória | Não |
| `drift.duration_s` | `120` | Duração de cada deriva estática | Ajustável |
| `drift.measure_before` | `true` | Medição antes da campanha | Não |
| `drift.measure_after` | `true` | Medição depois da campanha | Não |

Exemplo completo baseado no schema atual:

```yaml
experiment_id: exp01_orientation_characterization
telemetry_csv: experiments/exp01_orientation_characterization/processed/segmented_orientation.csv

angular_protocol:
  start_deg: 0
  stop_deg: 360
  step_deg: 10
  include_closure_endpoint: true

coordinate_system:
  zero_direction_description: "Mannequin facing the acoustic frontal reference"
  positive_rotation_direction: "clockwise"
  reference_angle_range_deg: [0, 360]
  reference_angle_step_deg: 10
  telemetry_yaw_input_range: "minus_180_to_180"
  comparison_range: "zero_to_360"

acquisition:
  settling_time_s: 3
  recording_time_s: 10
  discard_initial_s: 2
  analyzed_stationary_interval_s: 8
  repetitions: 3

runs:
  - ascending
  - descending
  - randomized

randomized_run:
  seed: 20260713
  append_closure_measurement_deg: 360

drift:
  duration_s: 120
  measure_before: true
  measure_after: true
```

Identificação BLE: o comando `telemetry-record` usa `device_name` da configuração
se existir; caso contrário usa `Tiresias_DK`. O dispositivo é selecionado por
nome, não por endereço nem por UUID.

## 6. Teste preliminar obrigatório

Faça antes da campanha completa.

1. Coloque a plataforma em 0°.
2. Aguarde pelo menos 3 s.
3. Grave 10 s:

```bash
python -m tiresias_benchmark telemetry-record \
  --output experiments/exp01_orientation_characterization/raw/pilot_0deg.csv \
  --duration-s 10
```

4. Mova fisicamente para 90° e volte para 0°. O repositório ainda não possui
   comando interativo para registrar os três segmentos no mesmo arquivo; para
   o piloto, use este passo apenas para observar mecanicamente a montagem e,
   se quiser registrar a rotação inteira, rode uma gravação contínua:

```bash
python -m tiresias_benchmark telemetry-record \
  --output experiments/exp01_orientation_characterization/raw/pilot_motion.csv \
  --duration-s 30
```

Inspecione o CSV:

```bash
python - <<'PY'
import csv, math
from pathlib import Path
p = Path("experiments/exp01_orientation_characterization/raw/pilot_0deg.csv")
rows = list(csv.DictReader(p.open()))
print("amostras:", len(rows))
for r in rows[:3]:
    q = [float(r[k]) for k in ("qw", "qx", "qy", "qz")]
    print("packet_format", r["packet_format"], "seq", r["seq"], "yaw", r["yaw_deg"],
          "calibrated_yaw", r["calibrated_yaw_deg"],
          "q_norm", math.sqrt(sum(x*x for x in q)))
intervals = [float(r["receive_interval_ms"]) for r in rows[1:] if r["receive_interval_ms"]]
print("intervalo medio ms:", sum(intervals)/len(intervals) if intervals else "indisponivel")
print("packet_loss_count total:", sum(int(float(r["packet_loss_count"])) for r in rows if r["packet_loss_count"]))
PY
```

Critérios go/no-go:

- `amostras` deve ser maior que zero.
- Norma do quaternion deve estar próxima de 1.
- `calibrated_yaw_deg` deve ficar perto de 0° logo após o tare em 0°.
- `receive_interval_ms` deve ser plausível e sem lacunas enormes.
- Se `packet_format` for `legacy_quaternion`, `seq`, `device_timestamp_ms`,
  `yaw_deg`, IMU bruto e `calibration_state` ficarão vazios; isto é esperado.
- Se houver desconexão, arquivo truncado ou quaternion inválido, não inicie a
  campanha.

## 7. Procedimento de tare

No código atual, o tare é automático no host.

Mecanismo:

1. Posicione a plataforma no 0° físico ou em 360° físico, que é equivalente a
   0°.
2. Aguarde a estabilização configurada, por padrão 3 s.
3. Inicie `telemetry-record`.
4. O primeiro pacote recebido define `tare_quaternion = conjugate(q_raw)`.
5. Os pacotes seguintes são calibrados por multiplicação host-side.

Não há:

- comando BLE de tare;
- tecla de tare;
- botão de recalibração;
- persistência do estado de tare em arquivo.

Arquivo afetado: o CSV de saída recebe `calibrated_yaw_deg` já calculado pelo
host. O estado de tare vive apenas no processo Python atual.

Como verificar:

- no CSV, as primeiras amostras em 0° devem ter `calibrated_yaw_deg` próximo de
  0°;
- a norma do quaternion deve ficar próxima de 1.

Não repita tare entre segmentos da mesma série. Repetir tare significa iniciar
um novo processo `telemetry-record`; isto muda a referência angular e pode
invalidar fechamento, deriva e comparações entre posições.

Para a série aleatória, como a primeira posição da ordem padrão é 280°, não
inicie a gravação já em 280°. Faça o tare com a plataforma parada em 0°, depois
comece a sequência aleatória e registre as marcações/tempos manualmente. O
software atual não automatiza esse passo.

## 8. Medição inicial de deriva

A forma recomendada é deixar o comando guiado gravar a deriva inicial dentro da
mesma conexão e do mesmo tare da campanha:

```bash
python -m tiresias_benchmark exp01-guided-acquire \
  --config experiments/exp01_orientation_characterization/config.yaml \
  --run all
```

O terminal primeiro pede para colocar a plataforma em 0°, conecta ao Tiresias,
tara no primeiro pacote e registra a deriva inicial por 120 s se
`drift.measure_before` estiver habilitado.

Se precisar gravar deriva isolada para diagnóstico, ela também pode ser gravada
como telemetria normal:

1. Plataforma em 0°.
2. Aguardar 3 s.
3. Não tocar na base.
4. Rodar:

```bash
python -m tiresias_benchmark telemetry-record \
  --output experiments/exp01_orientation_characterization/raw/drift_before_0deg.csv \
  --duration-s 120
```

Anote em `operator_notes.md` ou caderno:

- hora;
- bateria/alimentação;
- sentido positivo configurado;
- se alguém tocou na mesa ou nos cabos;
- temperatura/situação do laboratório, se relevante.

Verificação rápida:

```bash
python - <<'PY'
import csv
p="experiments/exp01_orientation_characterization/raw/drift_before_0deg.csv"
rows=list(csv.DictReader(open(p)))
print("amostras:", len(rows))
if rows:
    t0=float(rows[0]["host_monotonic_timestamp_ns"])
    t1=float(rows[-1]["host_monotonic_timestamp_ns"])
    print("duracao_s:", (t1-t0)/1e9)
    print("yaw inicial/final:", rows[0]["calibrated_yaw_deg"], rows[-1]["calibrated_yaw_deg"])
PY
```

## 9. Execução da série crescente

Sequência física:

`0°, 10°, 20°, ..., 350°, 360°`.

O comando recomendado é guiado. Ele mostra no terminal mensagens como:

- `Conectou ao Tiresias`;
- `Tarou`;
- `Mova ate 10 graus`;
- `Estabilizando`;
- `Medindo. Nao mova`;
- `yaw_calibrado=...`;
- `Posicao armazenada`.

Comando recomendado para a campanha inteira:

```bash
python -m tiresias_benchmark exp01-guided-acquire \
  --config experiments/exp01_orientation_characterization/config.yaml \
  --run all
```

Procedimento por posição:

1. Comece em 0°.
2. O comando conecta e tara no primeiro pacote.
3. Quando o terminal pedir, mova para o ângulo informado.
4. Pressione Enter somente depois de alinhar a escala.
5. O software aplica a estabilização configurada.
6. O software descarta o transiente inicial.
7. O software grava o intervalo estacionário analisado.
8. Não mova a base enquanto aparecer `Medindo. Nao mova`.
9. O software escreve `run_id`, `run_type`, `position_index`,
   `reference_angle_commanded_deg`, `reference_angle_normalized_deg`,
   `is_closure_measurement` e fase do segmento em cada linha.

Tabela mínima:

| Ângulo comandado | Referência normalizada | Fechamento |
|---:|---:|---|
| 0 | 0 | false |
| 10 | 10 | false |
| 180 | 180 | false |
| 350 | 350 | false |
| 360 | 0 | true |

Depois da aquisição guiada, o CSV segmentado é criado automaticamente em:

`experiments/exp01_orientation_characterization/processed/segmented_orientation.csv`

Se você usar o método antigo com `telemetry-record`, aí sim esse arquivo precisa
ser criado manualmente ou por script externo.

## 10. Execução da série decrescente

Sequência física:

`360°, 350°, 340°, ..., 10°, 0°`.

Se estiver usando `exp01-guided-acquire --run all`, a série decrescente começa
automaticamente após a crescente.

Como `positive_rotation_direction` está configurado como `clockwise`, a série
decrescente normalmente exige inverter o sentido físico em relação à série
crescente. Se sua escala física estiver invertida, siga o sentido documentado no
campo `positive_rotation_direction` e nas notas.

Comando isolado para executar apenas a série decrescente:

```bash
python -m tiresias_benchmark exp01-guided-acquire \
  --config experiments/exp01_orientation_characterization/config.yaml \
  --run descending \
  --no-drift
```

Comece com a plataforma em 360°, que é fisicamente 0°. Assim o tare automático
continua referenciado ao zero físico. A medição final em 0° é fechamento da
série decrescente e deve ser marcada com `is_closure_measurement=true`.

Esta série ajuda a avaliar:

- erro dependente do sentido de rotação;
- reposicionamento mecânico;
- histerese da base;
- fechamento entre 360° inicial e 0° final.

## 11. Execução da série aleatória

A sequência é gerada por `build_reference_sequences` usando
`randomized_run.seed = 20260713`.

Sequência padrão atual:

```text
280, 140, 350, 300, 180, 70, 130, 20, 330, 100, 90, 270,
80, 190, 210, 310, 290, 30, 340, 10, 250, 110, 170, 160,
150, 240, 120, 0, 220, 40, 60, 320, 50, 260, 200, 230, 360
```

Os primeiros 36 valores são as orientações únicas de 0° a 350°. O 360° final é
medição de fechamento, não orientação independente.

O repositório ainda não salva a sequência em um arquivo antes da aquisição; ela
aparece no JSON de saída de `experiment-run` e pode ser impressa com:

```bash
python - <<'PY'
from tiresias_benchmark.cli import load_yaml
from tiresias_benchmark.experiments.experiment_01 import build_reference_sequences
cfg = load_yaml("experiments/exp01_orientation_characterization/config.yaml")
seq = build_reference_sequences(cfg)["randomized"]
print(", ".join(str(int(x["reference_angle_commanded_deg"])) for x in seq))
PY
```

Comando isolado para executar apenas a série aleatória:

```bash
python -m tiresias_benchmark exp01-guided-acquire \
  --config experiments/exp01_orientation_characterization/config.yaml \
  --run randomized \
  --no-drift
```

Importante: inicie o comando com a plataforma em 0° para realizar o tare. Depois
vá para a primeira posição da sequência, 280°. Esse trecho inicial de tare deve
ser excluído na segmentação manual. O software atual não faz isso
automaticamente.

## 12. Medição final de deriva

1. Retorne fisicamente a 0°.
2. Não faça novo tare se quiser avaliar a deriva em relação ao começo da
   campanha. Entretanto, o comando atual sempre faz tare ao iniciar um novo
   `telemetry-record`; portanto a deriva final gravada por este comando mede a
   estabilidade local durante os 120 s finais, não a deriva acumulada absoluta
   desde a primeira aquisição.
3. Rode:

```bash
python -m tiresias_benchmark telemetry-record \
  --output experiments/exp01_orientation_characterization/raw/drift_after_0deg.csv \
  --duration-s 120
```

Se a meta for medir deriva acumulada sem novo tare, isso ainda exige mudança de
implementação ou uma aquisição contínua única cobrindo toda a campanha.

## 13. Arquivos esperados

Árvore esperada:

```text
experiments/exp01_orientation_characterization/
  config.yaml
  raw/
    drift_before_0deg.csv
    ascending_raw.csv
    descending_raw.csv
    randomized_raw.csv
    drift_after_0deg.csv
    operator_notes.md              # manual
  processed/
    segmented_orientation.csv      # manual ou script externo
  metrics/
    exp01_metrics.json             # criado por experiment-run --output
  figures/
    measured_vs_reference.png      # ainda não implementado
    circular_error_vs_reference.png
    closure_comparison.png
    repeatability.png
    packet_interval_distribution.png
    yaw_drift_before_after.png
```

CSV de telemetria bruto criado por `telemetry-record`:

```csv
session_id,host_monotonic_timestamp_ns,receive_interval_ms,packet_loss_count,device_timestamp_ms,seq,packet_format,packet_version,flags,ax_m_s2,ay_m_s2,az_m_s2,gx_rad_s,gy_rad_s,gz_rad_s,qw,qx,qy,qz,yaw_deg,calibrated_yaw_deg,sigma_deg,bmax_db,audio_frame_index,calibration_state
20260716_120000,123456789000000,,,42,0,telemetry_v1,1,0,0.1,0.0,9.8,0.0,0.0,0.0,1.0,0.0,0.0,0.0,0.0,0.0,20.0,10.0,,
```

Se o pacote for legado, campos como `device_timestamp_ms`, `seq`, `yaw_deg`,
IMU bruto e `calibration_state` ficam vazios.

CSV segmentado esperado pelo processamento:

```csv
run_id,run_type,position_index,reference_angle_commanded_deg,reference_angle_normalized_deg,is_closure_measurement,host_monotonic_timestamp_ns,seq,calibrated_yaw_deg
ascending,ascending,0,0,0,false,123456789000000,0,0.2
ascending,ascending,36,360,0,true,123456999000000,3000,1.1
```

Saída JSON de `experiment-run`:

```json
{
  "mae_deg": 1.0,
  "rmse_deg": 1.18,
  "bias_deg": -0.6,
  "max_abs_error_deg": 2.0,
  "global_samples_used": 108,
  "closure_samples_excluded": 3,
  "closure_errors_deg": {
    "ascending": 1.0
  },
  "update_rate_hz": 50.0,
  "interval_p95_ms": 22.0,
  "lost_packets": 0,
  "packet_loss_percent": 0.0
}
```

## 14. Validação imediata da aquisição

Antes de desmontar a bancada:

```bash
python - <<'PY'
import csv, math
from collections import Counter, defaultdict
p="experiments/exp01_orientation_characterization/processed/segmented_orientation.csv"
rows=list(csv.DictReader(open(p)))
print("linhas:", len(rows))
for run in ("ascending","descending","randomized"):
    rr=[r for r in rows if r["run_type"]==run]
    print(run, "linhas", len(rr), "closure", sum(r["is_closure_measurement"].lower()=="true" for r in rr))
    vals=[int(float(r["reference_angle_commanded_deg"])) for r in rr if r["is_closure_measurement"].lower()!="true"]
    print("  faltando:", sorted(set(range(0,360,10))-set(vals)))
    print("  duplicados:", [k for k,v in Counter(vals).items() if v>1])
bad_q=0
for r in rows:
    if all(k in r and r[k] for k in ("qw","qx","qy","qz")):
        q=[float(r[k]) for k in ("qw","qx","qy","qz")]
        if abs(math.sqrt(sum(x*x for x in q))-1)>0.05:
            bad_q+=1
print("quaternions suspeitos:", bad_q)
PY
```

Checklist pass/fail:

- [ ] Todas as 36 orientações únicas existem por série.
- [ ] Ascending tem 360° como fechamento.
- [ ] Descending tem 0° final como fechamento.
- [ ] Randomized tem 36 posições únicas e 360° final.
- [ ] Cada segmento tem duração suficiente após descartar 2 s.
- [ ] Amostras por segmento são plausíveis.
- [ ] Gaps BLE não são excessivos.
- [ ] Quaternions têm norma próxima de 1.
- [ ] Yaw normalizado cobre a volta completa.
- [ ] 0° e 360° são razoavelmente próximos.
- [ ] Segmentos inválidos estão marcados nas notas.

## 15. Processamento dos dados

O comando implementado processa um único CSV segmentado definido no config:

```bash
python -m tiresias_benchmark experiment-run \
  --experiment 1 \
  --config experiments/exp01_orientation_characterization/config.yaml \
  --output experiments/exp01_orientation_characterization/metrics/exp01_metrics.json
```

Não há comandos separados implementados para processar ascending, descending,
randomized e drift individualmente. Para isso, crie configs temporários
apontando `telemetry_csv` para o CSV segmentado desejado, ou filtre manualmente
os dados.

Cálculos implementados:

- normalização `yaw mod 360`;
- erro circular assinado;
- MAE circular;
- RMSE circular;
- bias circular;
- erro absoluto máximo;
- estatísticas de intervalo de notificação;
- perda de pacotes quando `seq` existe;
- closure error por série;
- deriva se `drift.before_csv` ou `drift.after_csv` forem adicionados ao config.

Não estão implementados diretamente:

- média circular por segmento a partir do CSV bruto;
- extração automática da janela estacionária;
- desvio-padrão estacionário por segmento;
- repetibilidade agregada por ângulo;
- diferença ascending-versus-descending;
- geração de tabelas prontas por run.

Use média circular, não média aritmética, perto de 0°/360°. Use diferença
circular, não subtração comum, para evitar erros falsos de quase 360°.

## 16. Geração das figuras

Não há gerador de figuras implementado para o Experimento 1. O comando:

```bash
python -m tiresias_benchmark figures-generate
```

existe, mas aborta intencionalmente.

Figuras que ainda devem ser produzidas externamente, por notebook ou script:

| Figura | Entrada | Eixos | Saída sugerida |
|---|---|---|---|
| medido vs referência | `segmented_orientation.csv` | x referência normalizada, y yaw normalizado | `figures/measured_vs_reference.png` |
| erro circular vs referência | `segmented_orientation.csv` | x referência, y erro circular | `figures/circular_error_vs_reference.png` |
| fechamento | `exp01_metrics.json` | run, closure error | `figures/closure_comparison.png` |
| repetibilidade | segmentos por ângulo | ângulo, dispersão | `figures/repeatability.png` |
| intervalos BLE | telemetria bruta ou segmentada | intervalo ms, contagem | `figures/packet_interval_distribution.png` |
| deriva antes/depois | drift CSVs | tempo, yaw calibrado | `figures/yaw_drift_before_after.png` |

## 17. Critérios para repetir uma medição

Repita um segmento se:

- ângulo de referência foi anotado errado;
- plataforma mexeu durante a janela estacionária;
- cabo puxou a base;
- o segmento ficou curto;
- houve lacuna BLE localizada;
- quaternion ficou inválido em poucas amostras.

Repita uma série inteira se:

- tare foi feito no ângulo errado;
- BLE desconectou por longo período;
- ordem angular foi seguida incorretamente;
- 360° não retornou fisicamente ao 0°;
- arquivo bruto foi truncado.

Reinicie desde o tare se:

- a placa moveu em relação ao manequim;
- o host foi reiniciado no meio da série;
- a referência física 0° foi redefinida;
- houve tare acidental.

## 18. Solução de problemas

Tiresias não descoberto:

```bash
python -m tiresias_benchmark telemetry-record --output /tmp/ble_probe.csv --duration-s 3
```

Verifique alimentação, BLE do computador e se o nome anunciado contém
`Tiresias_DK`.

Falha de conexão BLE:

- aproxime o computador;
- reinicie o BLE do sistema;
- reinicie a placa;
- tente novamente com o mesmo comando.

Notificações não recebidas:

- confirme que o firmware expõe a característica `12345678-1234-5678-1234-56789abcdef2`
  ou a legada `12345678-1234-5678-1234-56789abcdef1`;
- confirme se o CSV tem linhas além do cabeçalho.

Ordem de quaternion errada:

- o código espera `(qw, qx, qy, qz)`;
- verifique norma do quaternion;
- se yaw parece incoerente, não corrija manualmente sem registrar a hipótese.

Yaw com sinal oposto:

- documente no campo `positive_rotation_direction`;
- o código atual não aplica inversão automática.

Yaw limitado a ±180° ou descontinuidade em 180°:

- isto é suportado pelo processamento circular;
- confira `calibrated_yaw_deg` e `reference_angle_normalized_deg`.

Tare não surtiu efeito:

- confirme que o comando começou em 0° ou 360°;
- lembre que tare ocorre no primeiro pacote de cada processo `telemetry-record`.

Arquivo não criado:

- confira permissões do diretório;
- confirme que o comando não falhou antes da conexão.

Resume não funciona:

- não há recurso de resume implementado.

Dependências Python ausentes:

```bash
python -m pip install -e ".[ble,metrics,dev]"
```

Figuras não geradas:

- não há implementação atual de figuras do Exp. 1.

0° e 360° muito diferentes:

- confira se a escala fecha fisicamente;
- confira torque dos cabos;
- confira se houve tare no ângulo errado;
- repita a série afetada.

## 19. Estimativa de tempo

Assumindo 3 s de estabilização, 10 s de aquisição e 1 s de movimentação/anotação
por posição:

- deriva antes: 120 s;
- ascending: 37 posições × 14 s = 518 s, cerca de 8,6 min;
- descending: 37 posições × 14 s = 518 s, cerca de 8,6 min;
- randomized: 37 posições × 14 s = 518 s, cerca de 8,6 min;
- deriva depois: 120 s;
- piloto e validação: 10 a 20 min;
- margem operacional: 10 min.

Tempo total prático: aproximadamente 45 a 60 min.

## 20. Checklist resumido para uso no laboratório

- [ ] Repositório aberto em `tiresias_aar_benchmark`.
- [ ] Ambiente Python ativado.
- [ ] Dependências instaladas.
- [ ] `python -m tiresias_benchmark --help` funciona.
- [ ] Configuração revisada.
- [ ] Zero físico confirmado.
- [ ] Sentido positivo confirmado.
- [ ] Tiresias rigidamente preso.
- [ ] Cabos sem torque.
- [ ] Piloto em 0° passou.
- [ ] Tare automático entendido.
- [ ] Deriva inicial gravada.
- [ ] Ascending gravado.
- [ ] Descending gravado.
- [ ] Randomized gravado.
- [ ] Fechamentos 360°/0° registrados.
- [ ] Deriva final gravada.
- [ ] CSV segmentado criado.
- [ ] Métricas processadas.
- [ ] Validação feita antes de desmontar.
- [ ] Arquivos copiados/backup feito.
