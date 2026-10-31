# Benchmark de Geração do Conjunto de Mandelbrot (Escape-Time)

**Disciplina:** DEC107 — Processamento Paralelo · UESC · 2026.2
**Autores:** Lucas Braga Orihuela e Cibelle Sousa Rodrigues

Gerador do conjunto de Mandelbrot pelo método de escape-time, usado como
benchmark de paralelismo ao longo das três etapas da disciplina. O problema é
embaraçosamente paralelo, mas fortemente desbalanceado em custo por pixel, e é
determinístico, o que permite validar cada versão paralela comparando bit a bit
com a saída serial.

## Etapas

| Etapa | Paradigma | Pasta | Situação |
|---|---|---|---|
| 1 | Memória compartilhada (OpenMP) | [`etapa1-openmp/`](etapa1-openmp/) | Entregue (tag `etapa1-entregue`) |
| 2 | Memória distribuída (MPI) | [`etapa2-mpi/`](etapa2-mpi/) | Entregue |
| 3 | GPU (CUDA) | — | Não iniciada |

Cada pasta tem o próprio README com compilação, uso, scripts de experimento e
o relatório da etapa.

## Estrutura

```
.
├── serial/
│   └── mandelbrot_serial.c   # versão sequencial de referência, usada por todas as etapas
├── etapa1-openmp/            # código, scripts, resultados e relatório da Etapa 1
├── etapa2-mpi/               # código, scripts, resultados e relatório da Etapa 2
└── README.md
```

Cada etapa é autocontida: traz o próprio código paralelo, os scripts de
experimento, os dados brutos e agregados, os gráficos e o relatório final.
A versão serial em `serial/` é compartilhada e nunca muda, o que garante que
as diferenças de desempenho entre as etapas venham só do paradigma de
paralelização.

## Versão serial

```bash
cd serial
gcc -O3 -std=c11 -o mandelbrot_serial mandelbrot_serial.c
./mandelbrot_serial            # input padrão: 4096x4096, MAX_ITER=1000
```

Ela grava `<prefixo>.bin` (matriz de contagens, inteiros de 32 bits, row-major)
e `<prefixo>.pgm`. A corretude de qualquer versão paralela é verificada
comparando o `.bin` dela com o da serial:

```bash
cmp ref.bin paralelo.bin && echo "IGUAIS"
```

## Métricas de desempenho

As três etapas usam exclusivamente as métricas vistas em aula, para que os
resultados sejam comparáveis entre si:

| Métrica | Fórmula |
|---|---|
| Speedup | S(n, p) = T(n) / T(n, p) |
| Eficiência | E(n, p) = S(n, p) / p = T(n) / (p · T(n, p)) |
| Fator de balanceamento de carga | F_LB(n) = (T_max − T_min) / T_max |
| Granularidade | G(n) = T_cp(n) / T_cm(n) |
| Sobrecarga | T_0(n, p) = p · T(n, p) − T(n) |

A Etapa 1 reportou o balanceamento como a razão entre o tempo máximo e o tempo
médio, cujo ideal é 1. A partir da Etapa 2 passou a ser usada a definição
acima, cujo ideal é 0. As duas medem o mesmo fenômeno em escalas diferentes e
**não são numericamente comparáveis**, então comparações de balanceamento
entre as etapas devem ser feitas pela ordenação relativa das estratégias.

## Condição obrigatória de medição

Toda coleta de tempo roda com o governador da CPU em `performance`, via o
wrapper de cada etapa. Em `powersave` os tempos ficam cerca de 37% mais lentos,
o que quebra a comparação entre etapas. O script da Etapa 2 se recusa a
executar fora de `performance`.

## Branches

- **`main`**: versões de referência, sem otimizações algorítmicas. É a base de
  todas as medições oficiais de speedup.
- **`otimizado`**: versão da Etapa 1 com early-exit por cardioide/bulbo,
  detecção de ciclo e simetria do eixo real (detalhes no README da Etapa 1).