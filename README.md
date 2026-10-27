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
| 2 | Memória distribuída (MPI) | [`etapa2-mpi/`](etapa2-mpi/) | Em andamento |
| 3 | GPU (CUDA) | — | Não iniciada |

Cada pasta tem o próprio README com compilação, uso, scripts de experimento e
o relatório da etapa.

## Estrutura

```
.
├── serial/
│   └── mandelbrot_serial.c   # versão sequencial de referência, usada por todas as etapas
├── etapa1-openmp/            # código, scripts, resultados e relatório da Etapa 1
├── etapa2-mpi/               # código e relatório da Etapa 2
└── README.md
```

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

## Branches

- **`main`**: versões de referência, sem otimizações algorítmicas. É a base de
  todas as medições oficiais de speedup.
- **`otimizado`**: versão da Etapa 1 com early-exit por cardioide/bulbo,
  detecção de ciclo e simetria do eixo real (detalhes no README da Etapa 1).
