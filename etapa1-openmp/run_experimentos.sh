# ============================================================
#  Automação de experimentos — Benchmark Mandelbrot (Etapa 1)
#  DEC107 - Processamento Paralelo
#
#  Gera um CSV com: bloco, politica, chunk, threads, resolução,
#  max_iter, rep, tempo_calculo, fator_balanceamento
# ============================================================
set -u

SERIAL=./mandelbrot_serial
PARALELO=./mandelbrot_openmp

REPS=5                 # repetições por configuração
OUT=resultados.csv

# ------------------------------------------------------------
# Cabeçalho do CSV + registro do ambiente
# ------------------------------------------------------------
{
  echo "# Ambiente de execução"
  echo "# $(uname -a)"
  echo "# Compilador: $(gcc --version | head -n1)"
  echo "# CPU: $(lscpu | awk -F: '/Model name/{gsub(/^ +/,"",$2); print $2}')"
  echo "# CPUs lógicas: $(nproc)"
  echo "# Governador: $(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null || echo 'n/a')"
  echo "# Repetições por config: $REPS"
  echo ""
  echo "bloco,politica,chunk,threads,largura,altura,max_iter,rep,tempo_calculo,fator_balanceamento"
} > "$OUT"

# ------------------------------------------------------------
# Função: roda 1 experimento e imprime 1 linha CSV
#   $1 bloco   $2 politica $3 chunk   $4 threads
#   $5 largura $6 altura   $7 max_iter
#   $8 args extras (região de zoom)
# ------------------------------------------------------------
roda() {
  local bloco=$1 politica=$2 chunk=$3 threads=$4
  local largura=$5 altura=$6 max_iter=$7
  local extras=$8

  local sched="$politica"
  [ -n "$chunk" ] && sched="$politica,$chunk"

  for ((r=1; r<=REPS; r++)); do
    local linha
    linha=$(OMP_SCHEDULE="$sched" "$PARALELO" -t "$threads" \
             -w "$largura" -a "$altura" -i "$max_iter" $extras \
             -o /tmp/mb_run 2>/dev/null \
             | grep '^RESULTADO,')

    # RESULTADO,largura,altura,max_iter,threads,tempo_calc,tempo_io,fator
    local tempo fator
    tempo=$(echo "$linha" | cut -d, -f6)
    fator=$(echo "$linha" | cut -d, -f8)

    echo "$bloco,$politica,${chunk:-NA},$threads,$largura,$altura,$max_iter,$r,$tempo,$fator" >> "$OUT"
  done
}

# ------------------------------------------------------------
# 1) STRONG SCALING — resolução fixa 4096², MAX_ITER=1000
#    varia threads e política/chunk
# ------------------------------------------------------------
bloco="strong"
for threads in 1 2 4 8 16; do
  for politica in static dynamic guided; do
    case "$politica" in
      static) chunks=("" "1" "16") ;;
      dynamic) chunks=("1" "16") ;;
      guided) chunks=("1" "32") ;;
    esac
    for chunk in "${chunks[@]}"; do
      roda "$bloco" "$politica" "$chunk" "$threads" 4096 4096 1000 ""
    done
  done
done

# ------------------------------------------------------------
# 2) WEAK SCALING — trabalho por thread constante
#    dobra resolução ao dobrar threads (4096² -> 8192² -> 16384²)
#    usa política estática (round-robin) para isolar escalabilidade
# ------------------------------------------------------------
bloco="weak"
weak_pairs=("1 4096" "2 5793" "4 8192" "8 11585" "16 16384")
for pair in "${weak_pairs[@]}"; do
  threads=${pair%% *}
  largura=${pair##* }
  roda "$bloco" "static" "16" "$threads" "$largura" "$largura" 1000 ""
done

# ------------------------------------------------------------
# 3) DESBALANCEAMENTO ACENTUADO (zoom "vale dos cavalos-marinhos")
#    região fixa, MAX_ITER=5000
# ------------------------------------------------------------
bloco="zoom"
zoom_args="-x -0.743643887 -y 0.131825904 -l 3.0e-3"
for threads in 4 16; do
  for politica in static dynamic guided; do
    case "$politica" in
      static) chunks=("" "1" "16") ;;
      dynamic) chunks=("1" "16") ;;
      guided) chunks=("1" "32") ;;
    esac
    for chunk in "${chunks[@]}"; do
      roda "$bloco" "$politica" "$chunk" "$threads" 4096 4096 5000 "$zoom_args"
    done
  done
done

echo "Concluído. Resultados em: $OUT"