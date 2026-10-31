#!/usr/bin/env bash
# Esteira automatizada de experimentos da Etapa 2 (MPI) - DEC107 (UESC)
# Compila os binarios, valida a corretude bit a bit contra a versao serial
# e executa a bateria completa: Escalabilidade Forte, Zoom (Seahorse Valley)
# e Escalabilidade Fraca.
#
# Todas as metricas seguem as definicoes da Aula 03 (Caracterizacao de
# desempenho em programas paralelos):
#   S(n,p)   = T(n) / T(n,p)                      -> Speedup
#   E(n,p)   = S(n,p) / p = T(n) / (p * T(n,p))   -> Eficiencia
#   F_LB(n)  = (T_max(n) - T_min(n)) / T_max(n)   -> Fator de balanco de carga
#   G(n)     = T_cp(n) / T_cm(n)                  -> Granularidade
#   T_0(n,p) = p * T(n,p) - T(n)                  -> Sobrecarga
#
# Por isso a escalabilidade fraca mede um baseline SERIAL PROPRIO para cada
# resolucao (4096, 8192, 16384): E(n,p) exige T(n) no mesmo tamanho n do caso
# paralelo. Sem isso nao da para calcular a eficiencia pela formula do slide.
#
# Variaveis de ambiente aceitas:
#   REPS_PAR   repeticoes dos casos paralelos forte/zoom   (padrao 5)
#   REPS_SER   repeticoes dos baselines seriais forte/zoom (padrao 7)
#   REPS_WEAK  repeticoes dos casos de escalabilidade fraca (padrao 3)
#   SCRATCH    diretorio para as saidas descartaveis (padrao ~/.cache/mandelbrot-mpi)
#   USAR_BASELINE_ETAPA1=1  reaproveita os baselines seriais da Etapa 1
#                           em vez de medir de novo (ver nota abaixo)
#
# Nota sobre baselines: por padrao o serial e remedido NESTA sessao. Reaproveitar
# a medicao da Etapa 1 mistura condicoes termicas/de frequencia diferentes no
# numerador do speedup, e remedir custa poucos segundos.

set -euo pipefail

cd "$(dirname "$0")"

REPS_PAR="${REPS_PAR:-5}"
REPS_SER="${REPS_SER:-7}"
REPS_WEAK="${REPS_WEAK:-3}"
USAR_BASELINE_ETAPA1="${USAR_BASELINE_ETAPA1:-0}"
CSV_OUT="resultados_mpi.csv"
SERIAL_TXT="serial_baselines_mpi.txt"

# /tmp neste sistema tem pouco espaco livre e a escalabilidade fraca grava
# 1,25 GB por execucao em 16384x16384. Por isso a area de rascunho fica fora.
SCRATCH="${SCRATCH:-$HOME/.cache/mandelbrot-mpi}"
mkdir -p "$SCRATCH"
trap 'rm -f "$SCRATCH"/*.bin "$SCRATCH"/*.pgm 2>/dev/null || true' EXIT

# Parametros oficiais do caso de desbalanceamento acentuado (enunciado, 5.3)
ZOOM_ARGS=(-x -0.743643887 -y 0.131825904 -l 3.0e-3 -i 5000)

# Escalabilidade fraca: trabalho por processo ~constante, N^2 proporcional a p.
# N = 4096*sqrt(p). Sao os mesmos cinco pontos usados na Etapa 1, o que torna a
# comparacao MPI vs OpenMP direta, e incluem as resolucoes citadas no enunciado.
WEAK_PARES=("1 4096" "2 5793" "4 8192" "8 11585" "16 16384")

T_INICIO=$(date +%s)

# Guarda de ambiente: medir em powersave torna os numeros incomparaveis com os
# da Etapa 1, que foi coletada inteira em performance. A diferenca medida nesta
# maquina e de cerca de 37% no tempo serial, o que invalidaria a comparacao
# MPI vs OpenMP exigida pelo enunciado. Para ignorar, use IGNORA_GOVERNADOR=1.
GOV_ATUAL=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null || echo desconhecido)
if [ "${IGNORA_GOVERNADOR:-0}" != "1" ] && [ "$GOV_ATUAL" != "performance" ]; then
    echo "ERRO: governador da CPU esta em '${GOV_ATUAL}', e nao em 'performance'." >&2
    echo >&2
    echo "Medir assim produz tempos cerca de 37% mais lentos que os da Etapa 1," >&2
    echo "o que invalida a comparacao MPI vs OpenMP do relatorio." >&2
    echo >&2
    echo "Rode pelo wrapper, que fixa e restaura o governador sozinho:" >&2
    echo "    ./roda_com_performance_mpi.sh" >&2
    echo >&2
    echo "Para medir mesmo assim, use: IGNORA_GOVERNADOR=1 ./run_experimentos_mpi.sh" >&2
    exit 1
fi
echo "Governador da CPU: ${GOV_ATUAL}"

echo "=== [1/6] Compilando binarios (MPI e Serial de referencia) ==="
mpicc -O3 -std=c11 -Wall -Wextra -o mandelbrot_mpi mandelbrot_mpi.c -lm
gcc   -O3 -std=c11 -Wall -Wextra -o mandelbrot_serial ../serial/mandelbrot_serial.c -lm

# O serial imprime "Tempo de calculo (s): <valor>" em stdout (nao ha linha
# RESULTADO como no binario MPI), entao o tempo sai do campo 5.
tempo_serial() {
    ./mandelbrot_serial "$@" -o "$SCRATCH/mb_ser" 2>/dev/null | awk '/^Tempo de calculo/{print $5}'
}

echo "=== [2/6] Validacao de corretude bit a bit (cmp) ==="
./mandelbrot_serial -o "$SCRATCH/ref_padrao" > /dev/null
for est in bloco ciclico mestre; do
    np_test=4
    chunk_arg=()
    if [ "$est" = "ciclico" ]; then chunk_arg=(-c 1); fi
    if [ "$est" = "mestre" ];  then chunk_arg=(-c 16); fi
    mpirun --oversubscribe -np "$np_test" ./mandelbrot_mpi -e "$est" "${chunk_arg[@]}" -o "$SCRATCH/par_${est}" > /dev/null 2>&1
    if cmp -s "$SCRATCH/ref_padrao.bin" "$SCRATCH/par_${est}.bin"; then
        echo "  [OK] Input padrao (estrategia=${est}, p=${np_test}): IGUAIS bit a bit"
    else
        echo "  [ERRO] Divergencia detectada na estrategia ${est}!"
        exit 1
    fi
done

./mandelbrot_serial "${ZOOM_ARGS[@]}" -o "$SCRATCH/ref_zoom" > /dev/null
for est in bloco ciclico mestre; do
    np_test=4
    chunk_arg=()
    if [ "$est" = "ciclico" ]; then chunk_arg=(-c 1); fi
    if [ "$est" = "mestre" ];  then chunk_arg=(-c 16); fi
    mpirun --oversubscribe -np "$np_test" ./mandelbrot_mpi -e "$est" "${chunk_arg[@]}" \
        "${ZOOM_ARGS[@]}" -o "$SCRATCH/par_zoom_${est}" > /dev/null 2>&1
    if cmp -s "$SCRATCH/ref_zoom.bin" "$SCRATCH/par_zoom_${est}.bin"; then
        echo "  [OK] Input zoom   (estrategia=${est}, p=${np_test}): IGUAIS bit a bit"
    else
        echo "  [ERRO] Divergencia detectada no zoom (${est})!"
        exit 1
    fi
done
rm -f "$SCRATCH"/ref_padrao.* "$SCRATCH"/par_* "$SCRATCH"/ref_zoom.*

echo "=== [3/6] Baselines seriais T(n) para forte e zoom ==="
if [ "$USAR_BASELINE_ETAPA1" = "1" ] && [ -f "../etapa1-openmp/serial_baselines.txt" ]; then
    cp ../etapa1-openmp/serial_baselines.txt "$SERIAL_TXT"
    echo "  Baselines reaproveitados de ../etapa1-openmp/serial_baselines.txt"
    echo "  AVISO: medidos em outra sessao; condicoes termicas podem diferir."
else
    echo "  Medindo baselines seriais nesta sessao (${REPS_SER} repeticoes)..."
    : > "$SERIAL_TXT"
    for r in $(seq 1 "$REPS_SER"); do
        t_s=$(tempo_serial)
        echo "strong,$r,$t_s" >> "$SERIAL_TXT"
        t_z=$(tempo_serial "${ZOOM_ARGS[@]}")
        echo "zoom,$r,$t_z" >> "$SERIAL_TXT"
        echo "    rep ${r}/${REPS_SER}: strong=${t_s}s  zoom=${t_z}s"
    done
fi

echo "=== [4/6] Baselines seriais T(n) por resolucao (escalabilidade fraca) ==="
# E(n,p) = T(n)/(p*T(n,p)) exige o serial NO MESMO tamanho n de cada ponto.
for par in "${WEAK_PARES[@]}"; do
    read -r _np n <<< "$par"
    if grep -q "^weak${n}," "$SERIAL_TXT" 2>/dev/null; then
        echo "  weak${n}: ja medido, pulando."
        continue
    fi
    echo "  Medindo serial em ${n}x${n} (${REPS_WEAK} repeticoes)..."
    for r in $(seq 1 "$REPS_WEAK"); do
        t_w=$(tempo_serial -w "$n" -a "$n")
        echo "weak${n},$r,$t_w" >> "$SERIAL_TXT"
        echo "    rep ${r}/${REPS_WEAK}: ${t_w}s"
    done
done
rm -f "$SCRATCH"/mb_ser.*

# Grava metadados do ambiente ArchLinux e cabecalho do CSV
{
    echo "# data: $(date -Iseconds)"
    echo "# uname: $(uname -srm)"
    echo "# cpu: $(lscpu | awk -F: '/Model name|Nome do modelo/{gsub(/^ +/,"",$2); print $2; exit}')"
    echo "# cpus_logicas: $(nproc)"
    echo "# mpicc: $(mpicc --version | head -n1)"
    echo "# mpirun: $(mpirun --version | head -n1)"
    echo "experimento,repeticao,estrategia,chunk,largura,altura,max_iter,processos,tempo_calculo,tempo_io,fator_balanceamento,tempo_com_raiz,overhead_com,t_comp_max,t_comp_min,fbc_etapa2,t_comp_soma,t_com_soma,t_com_max"
} > "$CSV_OUT"

# Executa um caso, captura a linha RESULTADO e extrai dos relatorios por rank:
#   T_max, T_min  -> F_LB = (T_max - T_min)/T_max   (Aula 03)
#   somas de T_cp e T_cm -> G(n) = T_cp/T_cm        (Aula 03, granularidade)
# No mestre-trabalhador o rank 0 nao calcula, entao fica fora de T_cp/T_max/T_min,
# mas o tempo dele em MPI continua contando como comunicacao.
roda_caso() {
    local exp="$1"
    local rep="$2"
    local np="$3"
    local est="$4"
    local chunk="$5"
    shift 5
    local extra_args=("$@")

    local c_flag=()
    if [ "$est" != "bloco" ]; then
        c_flag=(-c "$chunk")
    fi

    local out
    out=$(mpirun --oversubscribe -np "$np" ./mandelbrot_mpi -e "$est" "${c_flag[@]}" -o "$SCRATCH/mb_mpi_run" "${extra_args[@]}" 2>/dev/null)

    local res_line
    res_line=$(echo "$out" | awk '/^RESULTADO,/{sub(/^RESULTADO,/,""); print}')

    if [ -z "$res_line" ]; then
        echo "  [ERRO] execucao sem linha RESULTADO (exp=${exp} p=${np} est=${est} chunk=${chunk})" >&2
        exit 1
    fi

    local stats
    stats=$(echo "$out" | awk -v est="$est" '
        /^[[:space:]]*rank[[:space:]]+[0-9]+:/ {
            rank_id = $2; sub(/:/, "", rank_id)
            t_comp  = $4; sub(/,/, "", t_comp)
            t_com   = $7; sub(/,/, "", t_com)

            soma_com += t_com + 0.0
            if (n_all == 0 || (t_com + 0.0) > tcom_max) tcom_max = t_com + 0.0
            n_all++

            if (est == "mestre" && (rank_id + 0) == 0) next
            val = t_comp + 0.0
            if (count == 0 || val > tmax) tmax = val
            if (count == 0 || val < tmin) tmin = val
            soma_comp += val
            count++
        }
        END {
            if (count > 0 && tmax > 0) {
                fbc = (tmax - tmin) / tmax
                printf "%.6f,%.6f,%.4f,%.6f,%.6f,%.6f", tmax, tmin, fbc, soma_comp, soma_com, tcom_max
            } else {
                printf "0.000000,0.000000,0.0000,0.000000,0.000000,0.000000"
            }
        }
    ')

    echo "${exp},${rep},${res_line},${stats}" >> "$CSV_OUT"
}

echo "=== [5/6] Escalabilidade Forte e Caso de Zoom (${REPS_PAR} repeticoes) ==="
for np in 1 2 4 8 16; do
    for r in $(seq 1 "$REPS_PAR"); do
        echo "  [strong] p=${np}, rep=${r}/${REPS_PAR}"
        roda_caso "strong" "$r" "$np" "bloco"   0
        roda_caso "strong" "$r" "$np" "ciclico" 1
        roda_caso "strong" "$r" "$np" "ciclico" 16
        if [ "$np" -ge 2 ]; then
            roda_caso "strong" "$r" "$np" "mestre" 1
            roda_caso "strong" "$r" "$np" "mestre" 16
        fi
    done
done

# Zoom no vale dos cavalos-marinhos: mesma bateria, input de desbalanceamento
# acentuado. Comeca em p=2 porque e aqui que o balanceamento importa e o
# mestre-trabalhador exige pelo menos 2 processos.
for np in 2 4 8 16; do
    for r in $(seq 1 "$REPS_PAR"); do
        echo "  [zoom] p=${np}, rep=${r}/${REPS_PAR}"
        roda_caso "zoom" "$r" "$np" "bloco"   0  "${ZOOM_ARGS[@]}"
        roda_caso "zoom" "$r" "$np" "ciclico" 1  "${ZOOM_ARGS[@]}"
        roda_caso "zoom" "$r" "$np" "ciclico" 16 "${ZOOM_ARGS[@]}"
        roda_caso "zoom" "$r" "$np" "mestre"  1  "${ZOOM_ARGS[@]}"
        roda_caso "zoom" "$r" "$np" "mestre"  16 "${ZOOM_ARGS[@]}"
    done
done

echo "=== [6/6] Escalabilidade Fraca (${REPS_WEAK} repeticoes) ==="
# Carga por processo constante: N^2 cresce junto com p (4096 -> 8192 -> 16384).
for par in "${WEAK_PARES[@]}"; do
    read -r np n <<< "$par"
    for r in $(seq 1 "$REPS_WEAK"); do
        echo "  [weak] p=${np}, ${n}x${n}, rep=${r}/${REPS_WEAK}"
        roda_caso "weak" "$r" "$np" "bloco"   0  -w "$n" -a "$n"
        roda_caso "weak" "$r" "$np" "ciclico" 1  -w "$n" -a "$n"
        roda_caso "weak" "$r" "$np" "ciclico" 16 -w "$n" -a "$n"
        if [ "$np" -ge 2 ]; then
            roda_caso "weak" "$r" "$np" "mestre" 1  -w "$n" -a "$n"
            roda_caso "weak" "$r" "$np" "mestre" 16 -w "$n" -a "$n"
        fi
    done
done

T_FIM=$(date +%s)
echo
echo "=== Concluido em $(( (T_FIM - T_INICIO) / 60 ))m $(( (T_FIM - T_INICIO) % 60 ))s ==="
echo "  Resultados brutos:  $CSV_OUT  ($(( $(wc -l < "$CSV_OUT") - 7 )) execucoes)"
echo "  Baselines seriais:  $SERIAL_TXT"
echo
echo "Proximo passo: python3 pos_processa_mpi.py"
