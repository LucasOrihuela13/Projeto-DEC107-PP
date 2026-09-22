# mede_serial.sh — mede o baseline serial (média de N execuções)
set -u

SERIAL=${SERIAL:-./mandelbrot_serial}
REPS=${1:-7}              # número de repetições (default 7)
OUT=serial_baselines.txt

mede() {
  local bloco="$1"; shift
  local tempos=""
  for ((r=1; r<=REPS; r++)); do
    local t
    t=$("$SERIAL" "$@" 2>/dev/null | awk '/Tempo de calculo/{print $NF}')
    tempos="$tempos $t"
  done
  # média e desvio padrão via awk (sem dependência de bc)
  read media std < <(echo "$tempos" | awk '
    { n=0; s=0; s2=0;
      for(i=1;i<=NF;i++){ n++; s+=$i; s2+=$i*$i }
      m=s/n;
      v=(s2 - s*s/n)/n;
      if(v<0) v=0;
      printf "%.6f %.6f\n", m, sqrt(v) }')
  printf "%-8s media=%.6f s  std=%.6f s\n" "$bloco" "$media" "$std"
  echo "$bloco=$media" >> "$OUT"
}

# cabeçalho
{
  echo "# Baseline serial (média de $REPS execuções)"
  echo "# $(uname -a)"
  echo "# $(gcc --version | head -n1)"
} > "$OUT"

# input padrão (4096², MAX_ITER=1000) — serve de baseline para strong E weak
mede strong

# caso de desbalanceamento acentuado (zoom, MAX_ITER=5000)
mede zoom -x -0.743643887 -y 0.131825904 -l 3.0e-3 -i 5000

echo ""
echo "Baselines salvos em: $OUT"