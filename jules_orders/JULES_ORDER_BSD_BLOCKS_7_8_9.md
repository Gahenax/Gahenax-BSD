# JULES WORK ORDER: BSD Falsifiability Sweep — Blocks 7-9

> **Priority**: HIGH
> **Type**: Compute Delegation
> **Created**: 2026-03-04T07:10:00-05:00
> **Status**: PENDING
> **Repository**: https://github.com/Gahenax/Gahenax-BSD

---

## 1. Objetivo

Ejecutar los **bloques 7, 8, 9** de la campaña BSD Phase-1 falsifiability.
Estos corresponden a las familias de **alto rango (rank 3-4)** donde BSD es menos explorado computacionalmente.

Los bloques 0-6 ya fueron ejecutados localmente (3,959 curvas, 0 anomalías).
Los bloques 7-9 fueron interrumpidos por ser demasiado costosos para ejecución local.

## 2. Pre-requisitos

```bash
git clone https://github.com/Gahenax/Gahenax-BSD.git
cd Gahenax-BSD
pip install numpy sympy mpmath pytest
```

### Verificación pre-ejecución
```bash
PYTHONPATH=. pytest tests/test_bsd.py -v
# Debe dar 27 passed
```

## 3. Comandos a ejecutar

### Bloque 7 — rank3_5077a (right)
```bash
PYTHONPATH=. python jules_orders/jules_bsd_runner.py \
  --block-id 7 \
  --seed rank3_5077a \
  --radius 15 \
  --side right \
  --prime-bound 2000 \
  --precision 25 \
  --height-bound 20 \
  --output-dir evidence/run_v2
```

### Bloque 8 — rank4_mestre (left)
```bash
PYTHONPATH=. python jules_orders/jules_bsd_runner.py \
  --block-id 8 \
  --seed rank4_mestre \
  --radius 15 \
  --side left \
  --prime-bound 2000 \
  --precision 25 \
  --height-bound 20 \
  --output-dir evidence/run_v2
```

### Bloque 9 — rank4_mestre (right)
```bash
PYTHONPATH=. python jules_orders/jules_bsd_runner.py \
  --block-id 9 \
  --seed rank4_mestre \
  --radius 15 \
  --side right \
  --prime-bound 2000 \
  --precision 25 \
  --height-bound 20 \
  --output-dir evidence/run_v2
```

## 4. Output esperado por bloque

Cada bloque genera 3 archivos:
- `evidence/run_v2/verdicts_block_{id}.jsonl` — un JSON por curva evaluada
- `evidence/run_v2/manifest_block_{id}.json` — resumen con contadores  
- `evidence/run_v2/telemetry_block_{id}.jsonl` — eventos de progreso

## 5. Entregables

1. Los 3 manifests generados (`manifest_block_7.json`, `manifest_block_8.json`, `manifest_block_9.json`)
2. Los 3 archivos de verdicts 
3. **Commit y push** de los resultados al repo

## 6. Criterios de aceptación

- [ ] 27 tests pasan antes de ejecutar
- [ ] Cada bloque evalúa ~490-500 curvas
- [ ] `n_errors == 0` en cada manifest
- [ ] Resultados commiteados y pushed al repo
- [ ] Reporte breve con: total curves per block, anomaly count, wall time

## 7. Contexto científico

La conjetura de Birch y Swinnerton-Dyer (BSD) predice que el rango del grupo de puntos racionales de una curva elíptica
$E: y^2 = x^3 + ax + b$ es igual al orden del cero de $L(E,s)$ en $s=1$.

Este experimento busca **contraejemplos** escaneando vecindarios de curvas de alto rango conocidas.
Las familias de rank 3-4 (bloques 7-9) son las más interesantes porque BSD es menos verificado en este rango.

## 8. Resultados previos (bloques 0-6, locales)

| Block | Seed | Curves | Consistent | Anomalies | Inconclusive |
|:---:|:---|---:|---:|---:|---:|
| 0 | rank0_control | 495 | 282 | 0 | 213 |
| 1 | rank0_control | 494 | 273 | 0 | 221 |
| 2 | rank1_37a | 492 | 279 | 0 | 213 |
| 3 | rank1_37a | 495 | 288 | 0 | 207 |
| 4 | rank2_389a | 495 | 355 | 0 | 140 |
| 5 | rank2_389a | 496 | 376 | 0 | 120 |
| 6 | rank3_5077a | 496 | 496 | 0 | 0 |

**Total parcial: 3,463 curves, 0 anomalies.**
