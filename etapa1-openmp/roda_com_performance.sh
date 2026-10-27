# roda_com_performance.sh — fixa governador em performance, roda, e reverte
set -u

GOV_ORIGINAL=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor)

configura() {
  echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor >/dev/null
}

restaura() {
  if echo "$GOV_ORIGINAL" | sudo -n tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor >/dev/null 2>&1; then
    echo "Governador restaurado para: $GOV_ORIGINAL"
  else
    echo "ERRO: não consegui restaurar o governador! Rode manualmente:"
    echo "  echo $GOV_ORIGINAL | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor"
  fi
}

# autentica uma vez e MANTÉM o timestamp do sudo vivo durante toda a execução
sudo -v || { echo "Falha ao autenticar o sudo."; exit 1; }
( while true; do sudo -v; sleep 50; done ) &
KEEPER=$!

trap 'kill $KEEPER 2>/dev/null; restaura' EXIT

echo "Governador original: $GOV_ORIGINAL"
configura
echo "Governador agora: $(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor)"

# executa os experimentos
./mede_serial.sh 7
./run_experimentos.sh

# o trap restaura o governador automaticamente ao final