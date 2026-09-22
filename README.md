# Benchmark de Geração do Conjunto de Mandelbrot (Escape-Time) — Etapa 1

**Disciplina:** DEC107 — Processamento Paralelo · UESC · 2026.2
**Etapa:** 1 de 3 — Memória Compartilhada (OpenMP)
**Autores:** Lucas Braga Orihuela e Cibelle Sousa Rodrigues

Implementação sequencial de referência e implementação paralela em OpenMP do
gerador do conjunto de Mandelbrot pelo método de escape-time, conforme o
enunciado da disciplina. O problema é usado como benchmark de paralelismo por
ser embaraçosamente paralelo, fortemente desbalanceado em custo por pixel e
determinístico (o que permite validar corretude por comparação exata com a
saída serial).

## Sumário

- [Estrutura do repositório](#estrutura-do-repositório)
- [Comparação entre as branches](#comparação-entre-as-branches)
- [Pré-requisitos](#pré-requisitos)
- [Compilação](#compilação)
- [Uso](#uso)
- [A variável `OMP_SCHEDULE`](#a-variável-omp_schedule)
- [Formato de saída](#formato-de-saída)
- [Métricas reportadas](#métricas-reportadas)
- [Reproduzindo os experimentos oficiais](#reproduzindo-os-experimentos-oficiais)
- [Validação de corretude](#validação-de-corretude)
- [Otimizações da branch `otimizado`](#otimizações-da-branch-otimizado)
- [Nota de transparência sobre uso de IA](#nota-de-transparência-sobre-uso-de-ia)

## Estrutura do repositório

Cada branch contém os dois arquivos-fonte na raiz:

```
.
├── mandelbrot_serial.c   # implementação sequencial (referência de corretude)
├── mandelbrot_openmp.c   # implementação paralela com OpenMP
└── README.md
```

Este repositório mantém duas branches com o mesmo par de arquivos, em estágios
diferentes de otimização:

- **`main`** — implementação de referência, direta, que atende aos requisitos
  mínimos da Etapa 1.
- **`otimizado`** — mesma implementação acrescida de otimizações de
  desempenho (ver [seção dedicada](#otimizações-da-branch-otimizado)), usadas
  como base para o item de bônus "otimizações criativas" do enunciado.

## Comparação entre as branches

| Recurso | `main` | `otimizado` |
|---|:---:|:---:|
| Early-exit por cardioide/bulbo principal | ❌ | ✅ |
| Detecção de ciclo (Brent) | ❌ | ✅ |
| Exploração de simetria do eixo real (`-s`) | ❌ | ✅ (padrão ligado) |
| Diagnóstico do schedule efetivo + aviso se `OMP_SCHEDULE` não definido | ❌ | ✅ |
| Escrita da imagem final em paralelo | ❌ | ✅ (`#pragma omp parallel for` na etapa de PPM) |
| Formato da imagem de saída | `.pgm` (cinza, escala linear) | `.ppm` (colorida, escala logarítmica) |
| Linha `RESULTADO` (CSV) no stdout | Só no binário OpenMP | Serial **e** OpenMP, com colunas extras |
| Flag `-h` | ajuda (`--help`) | **altura** (alias de `-a`) — ajuda passou a ser `--help`/`-?` |
| Precisa linkar `-lm` | Não | Sim (`log1p` na colorização) |

> ⚠️ **Atenção ao trocar de branch:** `-h` muda de significado entre `main`
> (ajuda) e `otimizado` (altura). Sempre confira `--help` antes de rodar um
> experimento novo.

## Pré-requisitos

- GCC com suporte a OpenMP (`libgomp`) — qualquer versão razoavelmente
  recente (OpenMP 2.0+ é suficiente; o `schedule(runtime)` usado é portátil).
- `libm` (biblioteca matemática padrão do C), já presente em qualquer
  toolchain GCC — necessária apenas na branch `otimizado`.
- Não há dependência de `-march=native` nem de flags específicas de CPU: os
  experimentos oficiais precisam rodar nos computadores pessoais de cada
  dupla (regra do enunciado), então o binário foi mantido portátil de
  propósito.

## Compilação

**Branch `main`:**
```bash
gcc -O3 -std=c11 -o mandelbrot_serial mandelbrot_serial.c
gcc -O3 -std=c11 -fopenmp -o mandelbrot_openmp mandelbrot_openmp.c
```

**Branch `otimizado`:**
```bash
gcc -O3 -std=c11 -o mandelbrot_serial mandelbrot_serial.c -lm
gcc -O3 -std=c11 -fopenmp -o mandelbrot_openmp mandelbrot_openmp.c -lm
```

## Uso

```
./mandelbrot_serial [-w largura] [-a altura] [-i max_iter]
                     [-x centro_re] [-y centro_im] [-l largura_re]
                     [-o prefixo_saida]

./mandelbrot_openmp  [-w largura] [-a altura] [-i max_iter]
                     [-x centro_re] [-y centro_im] [-l largura_re]
                     [-t threads] [-o prefixo_saida]
```
Na branch `otimizado`, ambos os binários também aceitam `-s 0|1` (liga/desliga
a exploração de simetria; padrão `1`) e usam `-a`/`-h` como sinônimos para
altura.

| Flag | Significado | Padrão |
|---|---|---|
| `-w` | Largura da imagem em pixels | `4096` |
| `-a` (`-h` em `otimizado`) | Altura da imagem em pixels | `4096` |
| `-i` | `MAX_ITER` | `1000` |
| `-x` | Parte real do centro da região | `-0.5` |
| `-y` | Parte imaginária do centro da região | `0.0` |
| `-l` | Largura da região no eixo real | `3.0` |
| `-t` | Threads OpenMP (só `mandelbrot_openmp`); se omitido, usa `OMP_NUM_THREADS` | ambiente |
| `-s` | Liga/desliga simetria (só `otimizado`) | `1` |
| `-o` | Prefixo dos arquivos de saída | `mandelbrot` / `mandelbrot_omp` |

A altura da região imaginária é derivada automaticamente a partir da razão de
aspecto da imagem (`largura_im = largura_re * altura / largura`), então basta
informar o centro e a largura em `Re` para enquadrar corretamente qualquer
zoom.

## A variável `OMP_SCHEDULE`

Os dois arquivos OpenMP usam `schedule(runtime)`, ou seja, a política de
escalonamento (`static`, `dynamic`, `guided`) e o tamanho de chunk são
definidos em tempo de execução pela variável de ambiente `OMP_SCHEDULE`:

```bash
OMP_SCHEDULE="static"     ./mandelbrot_openmp ...
OMP_SCHEDULE="dynamic,16" ./mandelbrot_openmp ...
OMP_SCHEDULE="guided,32"  ./mandelbrot_openmp ...
```

Isso é o que permite comparar as três políticas pedidas no relatório sem
recompilar. **Nunca rode um experimento oficial sem definir `OMP_SCHEDULE`
explicitamente**: o valor default de `run-sched-var` é definido pela
implementação (no `libgomp`/GCC, medido como `dynamic,1`, que não é
`static`), então resultados sem a variável definida não são reprodutíveis
entre máquinas. A branch `otimizado` já imprime no `stderr` o schedule
efetivo detectado e avisa quando a variável não foi definida; a `main` não
faz essa checagem, então redobre a atenção ao rodá-la.

## Formato de saída

Todo binário grava dois arquivos com o prefixo escolhido em `-o`:

- **`<prefixo>.bin`** — a matriz canônica de contagens de iteração, em
  inteiros de 32 bits (`int`), ordem *row-major*, sem cabeçalho. É sobre esse
  arquivo que a corretude deve ser validada (Seção 5.5 do enunciado).
- **Imagem para inspeção visual:**
  - `main`: `<prefixo>.pgm` (P5, escala de cinza, mapeamento linear de
    `it/MAX_ITER`, interior do conjunto em preto).
  - `otimizado`: `<prefixo>.ppm` (P6, colorida, mapeamento **logarítmico**
    de `it` via `log1p`, paleta "Glacier / Azul Abissal": azul-marinho →
    safira → ciano elétrico → branco-gelo no exterior; interior em um tom
    quase preto, `RGB(3,6,16)`). A escala log melhora o contraste perto da
    fronteira fractal em relação ao mapeamento linear.

## Métricas reportadas

Ambos os binários imprimem no `stdout` o tempo de cálculo, o tempo de E/S e o
tempo total. Os binários OpenMP também imprimem o fator de balanceamento de
carga (`tempo_max / tempo_médio` entre threads) e a decomposição por thread
(tempo e nº de linhas processadas).

Além disso, uma linha `RESULTADO` em CSV é emitida para facilitar agregação
automática dos resultados em planilhas/scripts. **O formato difere entre
arquivos e branches:**

| Origem | Formato da linha `RESULTADO` |
|---|---|
| `main` / `mandelbrot_serial` | *(não emite linha `RESULTADO`)* |
| `main` / `mandelbrot_openmp` | `RESULTADO,largura,altura,max_iter,threads,tempo_calc,tempo_io,fator_bal` |
| `otimizado` / `mandelbrot_serial` | `RESULTADO,largura,altura,max_iter,1,tempo_calc,tempo_io,1.0000,serial,simetria` |
| `otimizado` / `mandelbrot_openmp` | `RESULTADO,largura,altura,max_iter,threads,tempo_calc,tempo_io,fator_bal,schedule,simetria` |

`simetria` é `1`/`0`; `schedule` é a string efetiva detectada em tempo de
execução (ex.: `dynamic:16`).

## Reproduzindo os experimentos oficiais

**Input padrão (obrigatório, Seção 5.2)** — os valores padrão de fábrica já
correspondem exatamente à região oficial (`Re ∈ [-2,1]`, `Im ∈ [-1.5,1.5]`,
4096×4096, `MAX_ITER=1000`), então basta:
```bash
OMP_SCHEDULE="static" ./mandelbrot_openmp -t 8 -o resultado_static
```

**Escalabilidade forte** — resolução fixa, variando threads:
```bash
for t in 1 2 4 8 16; do
  OMP_SCHEDULE="static" ./mandelbrot_openmp -t $t -o forte_t$t
done
```

**Escalabilidade fraca** — resolução crescendo com os recursos (ex.: 4096²,
8192², 16384² para 1, 4 e 16 threads, respectivamente):
```bash
OMP_SCHEDULE="static" ./mandelbrot_openmp -t 1  -w 4096  -a 4096  -o fraca_1
OMP_SCHEDULE="static" ./mandelbrot_openmp -t 4  -w 8192  -a 8192  -o fraca_4
OMP_SCHEDULE="static" ./mandelbrot_openmp -t 16 -w 16384 -a 16384 -o fraca_16
```

**Caso de desbalanceamento acentuado (obrigatório, Seção 5.3)** — zoom no
"vale dos cavalos-marinhos":
```bash
OMP_SCHEDULE="dynamic,16" ./mandelbrot_openmp \
  -x -0.743643887 -y 0.131825904 -l 3.0e-3 -i 5000 \
  -t 8 -o cavalos_dynamic16
```

Na branch `otimizado`, adicione `-s 0` a qualquer um dos comandos acima para
gerar a "linha de base sem bônus" (sem simetria) exigida ao comparar
resultados com/sem as otimizações.

## Validação de corretude

Como o cálculo é determinístico, compare os arquivos `.bin` gerados pela
versão serial e pela versão OpenMP (mesma região, mesmo `MAX_ITER`):
```bash
./mandelbrot_serial -o ref
OMP_SCHEDULE="dynamic,16" ./mandelbrot_openmp -t 8 -o omp_dynamic16
cmp ref.bin omp_dynamic16.bin && echo "OK — matrizes idênticas"
```
Isso também vale entre as branches `main` e `otimizado`, e entre `-s 1` e
`-s 0`: as otimizações da branch `otimizado` (early-exit no cardioide/bulbo,
detecção de ciclo e mirror de simetria) apenas evitam recalcular pixels cujo
resultado (`MAX_ITER`) já é conhecido analiticamente ou já foi calculado para
a linha espelhada — nenhuma delas altera o valor produzido para um pixel.
A cópia por simetria só é feita quando o espelho é **numericamente exato**
(`cim_espelho == -cim` em ponto flutuante), então a saída deve ser
bit-idêntica à versão sem simetria, sem necessidade de tolerância.

## Otimizações da branch `otimizado`

- **Early-exit por cardioide/bulbo principal:** testa analiticamente se `c`
  pertence à cardioide principal ou ao bulbo de período 2 antes de iterar;
  se sim, retorna `MAX_ITER` sem simular a órbita — evita o pior caso (custo
  máximo) para a maior parte da região interna do conjunto.
- **Detecção de ciclo (Brent):** durante a iteração, compara periodicamente
  o ponto atual com um ponto de referência salvo em potências de 2; se
  houver repetição exata, a órbita é periódica e nunca escapará, então
  retorna `MAX_ITER` sem consumir o restante das iterações.
- **Simetria do eixo real (`-s`):** o conjunto de Mandelbrot é simétrico em
  relação ao eixo real; quando a grade discreta cai em um espelho exato,
  calcula-se apenas uma das duas linhas e copia-se o resultado (`memcpy`)
  para a outra, reduzindo o trabalho em até ~50%. Fica dentro do laço
  paralelo `#pragma omp for`, então cada thread ainda decide seu próprio
  espelho.
- **Escrita colorida em paralelo:** a etapa de colorização do PPM (que hoje
  é O(width×height) com uma chamada a `log1p` por pixel) roda em
  `#pragma omp parallel for schedule(static)`, evitando que a E/S vire um
  gargalo serial desproporcional após o cálculo paralelo da matriz.
- **Diagnóstico de schedule:** imprime no `stderr` a política e o chunk
  efetivamente resolvidos por `schedule(runtime)` e avisa quando
  `OMP_SCHEDULE` não foi definido — protege contra experimentos
  não-reprodutíveis por dependerem do default específico da implementação.
- **Portabilidade deliberada:** compilado só com `-O3 -std=c11 -fopenmp`,
  sem `-march=native`, para garantir que o binário rode sem falhas de
  instrução em qualquer computador pessoal usado pela dupla nos testes
  (exigência do enunciado).

## Nota de transparência sobre uso de IA

Declaramos que este projeto contou com o auxílio das ferramentas de IA
**Claude (Anthropic)** e **Gemini (Google)**, exclusivamente para as
seguintes tarefas:

- Sugestão de estratégias de otimização de desempenho para a versão OpenMP
  (Claude), posteriormente implementadas e testadas pela dupla.
- Apoio na depuração (debugging) do código-fonte quando necessário (Claude).
- Geração deste README e apoio na revisão/comentário do código-fonte
  (Gemini).

Como autores, atestamos que revisamos, testamos e validamos criticamente
todo o conteúdo gerado, assumindo total e exclusiva responsabilidade pela
correção lógica do código, precisão dos relatórios de desempenho e
integridade acadêmica do material entregue.

Lucas Braga Orihuela e Cibelle Sousa Rodrigues — [21/09/2026]
