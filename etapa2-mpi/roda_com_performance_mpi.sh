#!/usr/bin/env bash
# roda_com_performance_mpi.sh - fixa governador em performance, roda a bateria
# da Etapa 2, e reverte o governador ao final.
#
# Motivo: a Etapa 1 coletou todos os numeros dela com o governador em
# performance. Medir a Etapa 2 em powersave tornaria a comparacao MPI vs OpenMP
# invalida, porque o relogio da CPU seria diferente nas duas etapas. Em
# powersave o serial em 4096x4096 mede cerca de 7,8 s contra cerca de 5,5 s em
# performance, ou seja, aproximadamente 40% de diferenca.
#
# Mesma estrutura do ../etapa1-openmp/roda_com_performance.sh.

set -u

cd "$(dirname "$0")"

GOV_ORIGINAL=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor)

configura() {
  echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor >/dev/null
}

restaura() {
  if echo "$GOV_ORIGINAL" | sudo -n tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor >/dev/null 2>&1; then
    echo "Governador restaurado para: $GOV_ORIGINAL"
  else
    echo "ERRO: nao consegui restaurar o governador! Rode manualmente:"
    echo "  echo $GOV_ORIGINAL | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor"
  fi
}

# autentica uma vez e MANTEM o timestamp do sudo vivo durante toda a execucao
sudo -v || { echo "Falha ao autenticar o sudo."; exit 1; }
( while true; do sudo -v; sleep 50; done ) &
KEEPER=$!

trap 'kill $KEEPER 2>/dev/null; restaura' EXIT

echo "Governador original: $GOV_ORIGINAL"
configura
echo "Governador agora: $(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor)"

# executa a bateria completa da Etapa 2
./run_experimentos_mpi.sh

# o trap restaura o governador automaticamente ao final
