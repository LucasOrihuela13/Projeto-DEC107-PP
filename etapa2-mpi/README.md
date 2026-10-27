# Benchmark de Geração do Conjunto de Mandelbrot (Escape-Time) — Etapa 2

**Disciplina:** DEC107 — Processamento Paralelo · UESC · 2026.2
**Etapa:** 2 de 3 — Memória Distribuída (MPI)
**Autores:** Lucas Braga Orihuela e Cibelle Sousa Rodrigues

Versão em MPI do gerador de Mandelbrot. O núcleo de cálculo (`escape_time` e o
mapeamento pixel → plano complexo) é idêntico ao da versão serial em
`../serial/`, então a matriz de saída tem que bater bit a bit com a da
referência. O que muda é como as linhas da imagem são divididas entre
processos e como o resultado volta para o rank 0.

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

- Uma implementação de MPI com `mpicc` e `mpirun` (testado com Open MPI 4.1).
  No Arch Linux: `sudo pacman -S openmpi`.
- GCC (o `mpicc` usa o compilador do sistema por baixo).

## Compilação

De dentro de `etapa2-mpi/`:

```bash
mpicc -O3 -std=c11 -o mandelbrot_mpi mandelbrot_mpi.c
gcc -O3 -std=c11 -o mandelbrot_serial ../serial/mandelbrot_serial.c
```

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
todos os processos. Na saída aparecem:

- **Tempo de cálculo**: do início até a matriz estar completa na raiz, ou seja,
  cálculo mais coleta. É o tempo usado no speedup.
- **Tempo de I/O**: escrita do `.bin` e do `.pgm`, reportada à parte.
- **Tempo em MPI na raiz**: tempo que o rank 0 passou dentro de chamadas MPI,
  incluindo espera.
- **Overhead de comunicação**: tempo de cálculo menos o cômputo do processo
  mais lento. É o que sobra depois de descontar o trabalho útil do gargalo, ou
  seja, custo de comunicação e sincronização.
- **Fator de balanceamento**: maior tempo de cômputo dividido pela média entre
  os processos que calculam (no `mestre`, o rank 0 fica de fora).
- Por rank: tempo de cômputo, tempo em MPI e número de linhas processadas.

A última linha é em CSV, para facilitar a coleta automatizada:

```
RESULTADO,estrategia,chunk,largura,altura,max_iter,processos,tempo_calculo,tempo_io,fator_balanceamento,tempo_com_raiz,overhead_com
```

No `bloco` a coluna de chunk sai como `0`.

## Validação de corretude

```bash
./mandelbrot_serial -o ref
mpirun -np 4 ./mandelbrot_mpi -e ciclico -c 1 -o par
cmp ref.bin par.bin && echo "IGUAIS" || echo "DIFERENTES"
```

Testado com 1, 2, 3, 5 e 7 processos, nas três estratégias, com chunks 1, 3,
16 e 1000, usando uma altura que não divide pelo número de processos, tanto no
input padrão quanto no zoom: todas as saídas idênticas à serial.
