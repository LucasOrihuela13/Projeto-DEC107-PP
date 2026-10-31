# Benchmark de Geração do Conjunto de Mandelbrot (Escape-Time) — Etapa 2

**Disciplina:** DEC107 — Processamento Paralelo · UESC · 2026.2
**Etapa:** 2 de 3 — Memória Distribuída (MPI)
**Autores:** Cibelle Sousa Rodrigues e Lucas Braga Orihuela

Versão em MPI do gerador de Mandelbrot. O núcleo de cálculo (`escape_time` e o
mapeamento pixel → plano complexo) é idêntico ao da versão serial em
`../serial/`, então a matriz de saída tem que bater bit a bit com a da
referência. O que muda é como as linhas da imagem são divididas entre
processos e como o resultado volta para o rank 0.

## Sumário

- [Estrutura da pasta](#estrutura-da-pasta)
- [Estratégias de distribuição](#estratégias-de-distribuição)
- [Pré-requisitos](#pré-requisitos)
- [Compilação](#compilação)
- [Uso](#uso)
- [Métricas reportadas](#métricas-reportadas)
- [Reproduzindo os experimentos oficiais](#reproduzindo-os-experimentos-oficiais)
- [Formato dos arquivos de resultado](#formato-dos-arquivos-de-resultado)
- [Validação de corretude](#validação-de-corretude)
- [Resultados principais](#resultados-principais)
- [Nota de transparência sobre uso de IA](#nota-de-transparência-sobre-uso-de-ia)

## Estrutura da pasta

```
etapa2-mpi/
├── mandelbrot_mpi.c              # implementação paralela com MPI, três estratégias
├── roda_com_performance_mpi.sh   # wrapper que fixa o governador em performance
├── run_experimentos_mpi.sh       # bateria completa: corretude, baselines e experimentos
├── pos_processa_mpi.py           # agrega resultados, calcula métricas e gera os gráficos
├── resultados_mpi.csv            # dados brutos, uma linha por execução
├── resultados_agregados_mpi.csv  # médias, desvios e métricas derivadas
├── serial_baselines_mpi.txt      # T(n) sequencial do input padrão, do zoom e por resolução
├── fig_mpi_*.png                 # oito gráficos usados no relatório
├── Relatorio_Etapa2_Mandelbrot.pdf   # relatório final entregue
└── README.md
```

## Estratégias de distribuição

A estratégia é escolhida em tempo de execução com `-e`, do mesmo jeito que a
Etapa 1 usava `OMP_SCHEDULE`, então o mesmo binário serve para todos os
experimentos.

| `-e` | Ideia | Coleta do resultado | Equivalente na Etapa 1 |
|---|---|---|---|
| `bloco` | Cada processo recebe uma faixa contígua de linhas (as que sobram vão para os primeiros ranks) | `MPI_Gatherv` direto na matriz final; a raiz usa `MPI_IN_PLACE` | `static` sem chunk |
| `ciclico` | Blocos de `chunk` linhas distribuídos em round-robin | `MPI_Gatherv` em um buffer intermediário + reordenação na raiz | `static,chunk` |
| `mestre` | O rank 0 só coordena e entrega `chunk` linhas para quem estiver livre | Cada trabalhador devolve o resultado junto com o pedido da próxima tarefa | `dynamic,chunk` |

O chunk (`-c`) vale para `ciclico` (padrão 1) e `mestre` (padrão 16). No
`mestre`, o rank 0 não calcula nada, então com `P` processos só `P-1`
trabalham, e a estratégia precisa de pelo menos 2 processos.

## Pré-requisitos

- Uma implementação de MPI com `mpicc` e `mpirun` (testado com Open MPI 5.0.11).
  No Arch Linux: `sudo pacman -S openmpi`.
- GCC (o `mpicc` usa o compilador do sistema por baixo).
- Para o pós-processamento e o relatório: `python-docx`, `numpy` e `matplotlib`.
  No Arch Linux: `sudo pacman -S python-docx python-numpy python-matplotlib`.

## Compilação

De dentro de `etapa2-mpi/`:

```bash
mpicc -O3 -std=c11 -o mandelbrot_mpi mandelbrot_mpi.c
gcc -O3 -std=c11 -o mandelbrot_serial ../serial/mandelbrot_serial.c
```

Os dois binários também são recompilados automaticamente pelo script de
experimentos.

## Uso

```
mpirun -np P ./mandelbrot_mpi [-w largura] [-a altura] [-i max_iter]
                              [-x centro_re] [-y centro_im] [-l largura_re]
                              [-e bloco|ciclico|mestre] [-c chunk]
                              [-o prefixo_saida]
```

As flags de região e resolução são as mesmas da serial e da Etapa 1, com os
mesmos valores padrão (input oficial: 4096×4096, `MAX_ITER=1000`,
`Re ∈ [-2,1]`, `Im ∈ [-1.5,1.5]`).

Exemplos:

```bash
mpirun -np 4 ./mandelbrot_mpi -e bloco
mpirun -np 4 ./mandelbrot_mpi -e ciclico -c 1
mpirun -np 8 ./mandelbrot_mpi -e mestre -c 8

# vale dos cavalos-marinhos
mpirun -np 8 ./mandelbrot_mpi -e mestre -c 4 \
  -x -0.743643887 -y 0.131825904 -l 3.0e-3 -i 5000 -o cavalos_mestre
```

Se o `mpirun` reclamar que não há slots suficientes (pedindo mais processos do
que núcleos físicos), acrescente `--oversubscribe`.

## Métricas reportadas

O tempo é medido com `MPI_Wtime`, a partir de uma `MPI_Barrier` que alinha
todos os processos. As métricas seguem exclusivamente as definições vistas em
aula:

| Métrica | Fórmula |
|---|---|
| Speedup | S(n, p) = T(n) / T(n, p) |
| Eficiência | E(n, p) = S(n, p) / p = T(n) / (p · T(n, p)) |
| Fator de balanceamento de carga | F_LB(n) = (T_max − T_min) / T_max, ideal 0 |
| Granularidade | G(n) = T_cp(n) / T_cm(n) |
| Sobrecarga | T_0(n, p) = p · T(n, p) − T(n) |

Na saída de cada execução aparecem:

- **Tempo de cálculo**: do início até a matriz estar completa na raiz, ou seja,
  cálculo mais coleta. É o T(n, p) usado no speedup.
- **Tempo de I/O**: escrita do `.bin` e do `.pgm`, reportada à parte e fora de
  qualquer métrica de desempenho.
- **Tempo em MPI na raiz**: tempo que o rank 0 passou dentro de chamadas MPI.
  Atenção, essa medida **agrega comunicação e espera**, porque um processo que
  termina cedo fica bloqueado dentro da chamada coletiva.
- **Overhead de comunicação**: tempo de cálculo menos o cômputo do processo
  mais lento. É a estimativa limpa do custo de comunicação, sem a ociosidade.
- **Fator de balanceamento**: (T_max − T_min) / T_max, calculado apenas sobre
  os processos que calculam. No `mestre`, o rank 0 fica de fora, senão T_min
  seria zero e o fator daria 1 em todos os casos.
- Por rank: tempo de cômputo, tempo em MPI e número de linhas processadas.

## Reproduzindo os experimentos oficiais

**Sempre pelo wrapper**, que fixa o governador da CPU em `performance` e o
restaura ao final:

```bash
./roda_com_performance_mpi.sh
python3 pos_processa_mpi.py
```

Medir em `powersave` produz tempos cerca de 37% mais lentos e torna os números
incomparáveis com os da Etapa 1, o que invalidaria a comparação entre
paradigmas exigida pelo enunciado. Por isso `run_experimentos_mpi.sh` se recusa
a rodar fora de `performance`. Para forçar assim mesmo, use
`IGNORA_GOVERNADOR=1`.

A bateria cobre, em cada uma das cinco configurações de estratégia e chunk:

- **Escalabilidade forte**: 4096×4096, `MAX_ITER=1000`, com p em 1, 2, 4, 8, 16.
- **Caso de zoom**: vale dos cavalos-marinhos, `MAX_ITER=5000`, com p em 2, 4, 8, 16.
- **Escalabilidade fraca**: N = 4096·√p, ou seja 4096², 5793², 8192², 11585² e
  16384² para p em 1, 2, 4, 8 e 16. São os mesmos pontos da Etapa 1.

Como E(n, p) exige T(n) no mesmo tamanho de problema, a escalabilidade fraca
mede um **baseline serial próprio para cada resolução**. Um único baseline em
4096² não permitiria aplicar a fórmula da disciplina nesse cenário.

Variáveis de ambiente aceitas: `REPS_PAR` (padrão 5), `REPS_SER` (padrão 7),
`REPS_WEAK` (padrão 3), `SCRATCH` (padrão `~/.cache/mandelbrot-mpi`) e
`USAR_BASELINE_ETAPA1` (padrão 0, que remede o serial nesta sessão).

A bateria completa levou 36 minutos e 41 segundos na máquina de referência e
registrou 284 execuções paralelas.

## Formato dos arquivos de resultado

Cada execução do binário MPI termina com uma linha em CSV:

```
RESULTADO,estrategia,chunk,largura,altura,max_iter,processos,tempo_calculo,tempo_io,fator_balanceamento,tempo_com_raiz,overhead_com
```

O `run_experimentos_mpi.sh` acrescenta a essa linha o experimento, a repetição
e as estatísticas por rank, produzindo as 19 colunas de `resultados_mpi.csv`:

```
experimento,repeticao,estrategia,chunk,largura,altura,max_iter,processos,
tempo_calculo,tempo_io,fator_balanceamento,tempo_com_raiz,overhead_com,
t_comp_max,t_comp_min,fbc_etapa2,t_comp_soma,t_com_soma,t_com_max
```

As três últimas colunas permitem calcular a granularidade G(n). O cabeçalho do
arquivo registra sistema operacional, compilador, versão do MPI, CPU e número
de CPUs lógicas. No `bloco` a coluna de chunk sai como `0`.

## Validação de corretude

Roda automaticamente como etapa obrigatória da bateria, que aborta se qualquer
estratégia divergir. Manualmente:

```bash
./mandelbrot_serial -o ref
mpirun -np 4 ./mandelbrot_mpi -e ciclico -c 1 -o par
cmp ref.bin par.bin && echo "IGUAIS" || echo "DIFERENTES"
```

Testado com 1, 2, 3, 5 e 7 processos, nas três estratégias, com chunks 1, 3,
16 e 1000, usando uma altura que não divide pelo número de processos, tanto no
input padrão quanto no zoom: todas as saídas idênticas à serial.


## Resultados principais

Com 16 processos no input padrão, contra baseline serial de 5,6583 s:

| Estratégia | Speedup | Eficiência | F_LB(n) |
|---|---|---|---|
| `bloco` | 3,59 | 0,224 | 0,9969 |
| `ciclico,1` | 9,18 | 0,574 | 0,2755 |
| `ciclico,16` | 9,17 | 0,573 | 0,3185 |
| `mestre,1` | **11,35** | 0,709 | 0,0262 |
| `mestre,16` | 11,20 | 0,700 | **0,0145** |

Três achados que o relatório desenvolve:

- O `bloco` com 2 processos dá F_LB de 0,0005, quase perfeito, por efeito da
  simetria do conjunto em relação ao eixo real. Com 4 processos salta para
  0,9718. A coincidência some no zoom, onde já começa em 0,3380.
- O tempo em MPI na raiz do `bloco` com 16 processos é 1,5715 s sobre um total
  de 1,5765 s, mas isso é **ociosidade**, não custo de transferência. O custo
  líquido fica entre 0,0065 s e 0,0448 s no input padrão.
- O F_LB residual do `ciclico` com carga igual por processo vem da assimetria
  entre P-cores e E-cores, não da geometria do fractal.

## Nota de transparência sobre uso de IA

Conforme declarado no relatório desta etapa, foi utilizada a ferramenta Claude,
da Anthropic, como recurso de apoio, nas seguintes frentes: depuração do
código-fonte, geração do README do repositório e apoio na revisão e comentário
do código, revisão dos resultados da Seção 3 em relação aos experimentos feitos
na máquina, apoio no entendimento desses resultados, apoio na produção dos
scripts de automatização dos experimentos, revisão metodológica da coleta,
que identificou a necessidade de medir um baseline sequencial próprio para cada
resolução da escalabilidade fraca e a necessidade de fixar o governador de
frequência em performance para manter a comparabilidade com a Etapa 1, e apoio
na estruturação e na redação do presente relatório, a partir dos dados
experimentais coletados pela dupla.

Toda a responsabilidade pela autoria, integridade e exatidão do conteúdo é da
dupla, e todo o código, dados e textos foram revisados, testados e validados
pelos autores.
