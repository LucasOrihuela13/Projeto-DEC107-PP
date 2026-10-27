/*
  Compilacao:
    mpicc -O3 -std=c11 -o mandelbrot_mpi mandelbrot_mpi.c

  Uso:
    mpirun -np P ./mandelbrot_mpi [-w largura] [-a altura] [-i max_iter]
                                  [-x centro_re] [-y centro_im] [-l largura_re]
                                  [-e estrategia] [-c chunk] [-o prefixo_saida]

  Estrategias de distribuicao (-e):
    bloco    faixas contiguas de linhas, uma por processo (decomposicao estatica)
    ciclico  blocos de 'chunk' linhas distribuidos em round-robin entre os processos
    mestre   mestre-trabalhador: o rank 0 so coordena e entrega 'chunk' linhas
             por vez para quem estiver livre (balanceamento dinamico)

  O chunk (-c) so vale para ciclico (padrao 1) e mestre (padrao 16).
  A estrategia mestre precisa de pelo menos 2 processos.

  Exemplos:
    mpirun -np 4 ./mandelbrot_mpi -e bloco
    mpirun -np 4 ./mandelbrot_mpi -e ciclico -c 1
    mpirun -np 8 ./mandelbrot_mpi -e mestre -c 8
    mpirun -np 4 ./mandelbrot_mpi -e mestre -c 4 -x -0.743643887 -y 0.131825904 -l 3.0e-3 -i 5000 -o seahorse_mpi

  A ultima linha da saida (RESULTADO,...) e em CSV para facilitar a coleta:
    RESULTADO,estrategia,chunk,largura,altura,max_iter,processos,
              tempo_calculo,tempo_io,fator_balanceamento,tempo_com_raiz,overhead_com
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <mpi.h>

#define EST_BLOCO   0
#define EST_CICLICO 1
#define EST_MESTRE  2

#define TAG_RESULTADO 1
#define TAG_TAREFA    2

typedef struct {
    int    width;
    int    height;
    int    max_iter;
    double centro_re;
    double centro_im;
    double largura_re;
    int    estrategia;
    int    chunk;
    char   prefixo[256];
} config_t;

static const char *nome_estrategia[] = { "bloco", "ciclico", "mestre" };

static void config_padrao(config_t *cfg) {
    cfg->width = 4096;
    cfg->height = 4096;
    cfg->max_iter = 1000;
    cfg->centro_re = -0.5;
    cfg->centro_im = 0.0;
    cfg->largura_re = 3.0;
    cfg->estrategia = EST_BLOCO;
    cfg->chunk = 0;
    strncpy(cfg->prefixo, "mandelbrot_mpi", sizeof(cfg->prefixo) - 1);
    cfg->prefixo[sizeof(cfg->prefixo) - 1] = '\0';
}

static void imprime_uso(const char *prog) {
    fprintf(stderr,
        "Uso: mpirun -np P %s [-w largura] [-a altura] [-i max_iter] [-x centro_re] "
        "[-y centro_im] [-l largura_re] [-e bloco|ciclico|mestre] [-c chunk] "
        "[-o prefixo_saida]\n", prog);
}

/*
  Todos os ranks recebem o mesmo argv do mpirun, entao cada um faz o proprio
  parse e ninguem precisa de Bcast da configuracao. So o rank 0 imprime erro.
  Retorno: 0 ok, 1 pediu ajuda, -1 erro.
 */
static int parse_argumentos(int argc, char **argv, config_t *cfg, int rank) {
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "-h") == 0 || strcmp(argv[i], "--help") == 0) {
            if (rank == 0) imprime_uso(argv[0]);
            return 1;
        }
        if (i + 1 >= argc) {
            if (rank == 0) imprime_uso(argv[0]);
            return -1;
        }
        const char *op = argv[i];
        const char *val = argv[++i];

        if (strcmp(op, "-w") == 0) cfg->width = atoi(val);
        else if (strcmp(op, "-a") == 0) cfg->height = atoi(val);
        else if (strcmp(op, "-i") == 0) cfg->max_iter = atoi(val);
        else if (strcmp(op, "-x") == 0) cfg->centro_re = atof(val);
        else if (strcmp(op, "-y") == 0) cfg->centro_im = atof(val);
        else if (strcmp(op, "-l") == 0) cfg->largura_re = atof(val);
        else if (strcmp(op, "-c") == 0) cfg->chunk = atoi(val);
        else if (strcmp(op, "-o") == 0) {
            strncpy(cfg->prefixo, val, sizeof(cfg->prefixo) - 1);
            cfg->prefixo[sizeof(cfg->prefixo) - 1] = '\0';
        } else if (strcmp(op, "-e") == 0) {
            if (strcmp(val, "bloco") == 0) cfg->estrategia = EST_BLOCO;
            else if (strcmp(val, "ciclico") == 0) cfg->estrategia = EST_CICLICO;
            else if (strcmp(val, "mestre") == 0) cfg->estrategia = EST_MESTRE;
            else {
                if (rank == 0) fprintf(stderr, "Erro: estrategia '%s' desconhecida.\n", val);
                return -1;
            }
        } else {
            if (rank == 0) imprime_uso(argv[0]);
            return -1;
        }
    }

    if (cfg->chunk == 0) {
        cfg->chunk = (cfg->estrategia == EST_MESTRE) ? 16 : 1;
    }

    if (cfg->width <= 0 || cfg->height <= 0 || cfg->max_iter <= 0 ||
        cfg->largura_re <= 0.0 || cfg->chunk <= 0) {
        if (rank == 0)
            fprintf(stderr, "Erro: largura, altura, max_iter, largura_re e chunk devem ser positivos.\n");
        return -1;
    }
    return 0;
}

/* Mesma funcao da versao serial, sem nenhuma alteracao, para garantir igualdade bit a bit. */
static int escape_time(double cre, double cim, int max_iter) {
    double zre = 0.0, zim = 0.0;

    for (int i = 0; i < max_iter; i++) {
        double zre2 = zre * zre;
        double zim2 = zim * zim;
        double novo_zim = 2.0 * zre * zim + cim;
        zre = zre2 - zim2 + cre;
        zim = novo_zim;

        if (zre * zre + zim * zim > 4.0) {
            return i;
        }
    }
    return max_iter;
}

typedef struct {
    double re_min, re_max, im_min, im_max;
} regiao_t;

/*
  Calcula as linhas [py_ini, py_fim) e grava em sequencia no buffer destino.
  O mapeamento pixel -> plano usa exatamente a mesma expressao da versao serial.
 */
static void calcula_linhas(int *destino, int py_ini, int py_fim,
                           const config_t *cfg, const regiao_t *r) {
    for (int py = py_ini; py < py_fim; py++) {
        double cim = r->im_min + (double) py * (r->im_max - r->im_min) / (double) (cfg->height - 1);
        int *linha = destino + (size_t) (py - py_ini) * cfg->width;
        for (int px = 0; px < cfg->width; px++) {
            double cre = r->re_min + (double) px * (r->re_max - r->re_min) / (double) (cfg->width - 1);
            linha[px] = escape_time(cre, cim, cfg->max_iter);
        }
    }
}

/* Faixa contigua do rank na decomposicao por blocos. As linhas que sobram vao para os primeiros ranks. */
static void faixa_bloco(int rank, int nprocs, int height, int *ini, int *fim) {
    int base = height / nprocs;
    int resto = height % nprocs;
    *ini = rank * base + (rank < resto ? rank : resto);
    *fim = *ini + base + (rank < resto ? 1 : 0);
}

/* Quantas linhas um rank recebe no ciclico: blocos de 'chunk' linhas, bloco b vai para o rank b % nprocs. */
static int linhas_ciclico(int rank, int nprocs, int height, int chunk) {
    int total = 0;
    for (int ini = rank * chunk; ini < height; ini += nprocs * chunk) {
        int fim = ini + chunk < height ? ini + chunk : height;
        total += fim - ini;
    }
    return total;
}

typedef struct {
    double t_comp;   /* tempo gasto so calculando escape_time */
    double t_com;    /* tempo dentro de chamadas MPI (inclui espera) */
    double linhas;   /* double para poder juntar tudo num unico Gather */
} metricas_t;

static void executa_bloco(int *matriz, const config_t *cfg, const regiao_t *reg,
                          int rank, int nprocs, metricas_t *m) {
    int ini, fim;
    faixa_bloco(rank, nprocs, cfg->height, &ini, &fim);
    int n = (fim - ini) * cfg->width;

    /* A raiz calcula direto dentro da matriz final e usa MPI_IN_PLACE, sem copia extra. */
    int *local = (rank == 0) ? matriz : malloc((size_t) n * sizeof(int));
    if (!local && n > 0) {
        fprintf(stderr, "Erro: rank %d sem memoria para o buffer local.\n", rank);
        MPI_Abort(MPI_COMM_WORLD, 1);
    }

    double t0 = MPI_Wtime();
    calcula_linhas(local + (rank == 0 ? (size_t) ini * cfg->width : 0), ini, fim, cfg, reg);
    double t1 = MPI_Wtime();

    int *counts = NULL, *displs = NULL;
    if (rank == 0) {
        counts = malloc((size_t) nprocs * sizeof(int));
        displs = malloc((size_t) nprocs * sizeof(int));
        for (int r = 0; r < nprocs; r++) {
            int a, b;
            faixa_bloco(r, nprocs, cfg->height, &a, &b);
            counts[r] = (b - a) * cfg->width;
            displs[r] = a * cfg->width;
        }
        MPI_Gatherv(MPI_IN_PLACE, 0, MPI_INT, matriz, counts, displs, MPI_INT, 0, MPI_COMM_WORLD);
    } else {
        MPI_Gatherv(local, n, MPI_INT, NULL, NULL, NULL, MPI_INT, 0, MPI_COMM_WORLD);
    }
    double t2 = MPI_Wtime();

    m->t_comp = t1 - t0;
    m->t_com = t2 - t1;
    m->linhas = fim - ini;

    if (rank == 0) { free(counts); free(displs); }
    else free(local);
}

static void executa_ciclico(int *matriz, const config_t *cfg, const regiao_t *reg,
                            int rank, int nprocs, metricas_t *m) {
    int chunk = cfg->chunk;
    int passo = nprocs * chunk;
    int nlin = linhas_ciclico(rank, nprocs, cfg->height, chunk);
    int *local = malloc((size_t) nlin * cfg->width * sizeof(int) + 1);
    if (!local) {
        fprintf(stderr, "Erro: rank %d sem memoria para o buffer local.\n", rank);
        MPI_Abort(MPI_COMM_WORLD, 1);
    }

    /* As linhas do rank ficam empacotadas em sequencia no buffer local. */
    double t0 = MPI_Wtime();
    int *pos = local;
    for (int ini = rank * chunk; ini < cfg->height; ini += passo) {
        int fim = ini + chunk < cfg->height ? ini + chunk : cfg->height;
        calcula_linhas(pos, ini, fim, cfg, reg);
        pos += (size_t) (fim - ini) * cfg->width;
    }
    double t1 = MPI_Wtime();

    /*
      Como as linhas de cada rank nao sao contiguas na imagem, a raiz recebe tudo
      num buffer intermediario e depois devolve cada linha para o lugar certo.
      Esse reordenamento entra no tempo de comunicacao da raiz.
     */
    int *counts = NULL, *displs = NULL, *staging = NULL;
    if (rank == 0) {
        counts = malloc((size_t) nprocs * sizeof(int));
        displs = malloc((size_t) nprocs * sizeof(int));
        staging = malloc((size_t) cfg->width * cfg->height * sizeof(int));
        if (!counts || !displs || !staging) {
            fprintf(stderr, "Erro: raiz sem memoria para o buffer de coleta.\n");
            MPI_Abort(MPI_COMM_WORLD, 1);
        }
        int acum = 0;
        for (int r = 0; r < nprocs; r++) {
            counts[r] = linhas_ciclico(r, nprocs, cfg->height, chunk) * cfg->width;
            displs[r] = acum;
            acum += counts[r];
        }
    }

    MPI_Gatherv(local, nlin * cfg->width, MPI_INT,
                staging, counts, displs, MPI_INT, 0, MPI_COMM_WORLD);

    if (rank == 0) {
        for (int r = 0; r < nprocs; r++) {
            int *orig = staging + displs[r];
            for (int ini = r * chunk; ini < cfg->height; ini += passo) {
                int fim = ini + chunk < cfg->height ? ini + chunk : cfg->height;
                size_t qtd = (size_t) (fim - ini) * cfg->width;
                memcpy(matriz + (size_t) ini * cfg->width, orig, qtd * sizeof(int));
                orig += qtd;
            }
        }
        free(counts); free(displs); free(staging);
    }
    double t2 = MPI_Wtime();

    m->t_comp = t1 - t0;
    m->t_com = t2 - t1;
    m->linhas = nlin;
    free(local);
}

/*
  Mestre-trabalhador. Cada mensagem do trabalhador para o mestre carrega um
  cabecalho [linha_ini, n_linhas] seguido dos dados das linhas calculadas.
  O primeiro pedido vai com n_linhas = 0 (so pedindo trabalho). O mestre responde
  com [linha_ini, n_linhas]; n_linhas = 0 significa que acabou.
  Assim o resultado de uma tarefa e o pedido da proxima viajam na mesma mensagem.
 */
static void executa_mestre(int *matriz, const config_t *cfg, const regiao_t *reg,
                           int rank, int nprocs, metricas_t *m) {
    int chunk = cfg->chunk;
    size_t tam_buf = 2 + (size_t) chunk * cfg->width;
    int *buf = malloc(tam_buf * sizeof(int));
    if (!buf) {
        fprintf(stderr, "Erro: rank %d sem memoria para o buffer de mensagens.\n", rank);
        MPI_Abort(MPI_COMM_WORLD, 1);
    }

    m->t_comp = 0.0;
    m->t_com = 0.0;
    m->linhas = 0;

    if (rank == 0) {
        int proxima = 0;
        int ativos = nprocs - 1;
        int tarefa[2];
        MPI_Status st;

        while (ativos > 0) {
            double a = MPI_Wtime();
            MPI_Recv(buf, (int) tam_buf, MPI_INT, MPI_ANY_SOURCE, TAG_RESULTADO, MPI_COMM_WORLD, &st);
            double b = MPI_Wtime();
            m->t_com += b - a;

            if (buf[1] > 0) {
                memcpy(matriz + (size_t) buf[0] * cfg->width, buf + 2,
                       (size_t) buf[1] * cfg->width * sizeof(int));
            }

            if (proxima < cfg->height) {
                tarefa[0] = proxima;
                tarefa[1] = (proxima + chunk <= cfg->height) ? chunk : cfg->height - proxima;
                proxima += tarefa[1];
            } else {
                tarefa[0] = -1;
                tarefa[1] = 0;
                ativos--;
            }
            a = MPI_Wtime();
            MPI_Send(tarefa, 2, MPI_INT, st.MPI_SOURCE, TAG_TAREFA, MPI_COMM_WORLD);
            m->t_com += MPI_Wtime() - a;
        }
    } else {
        int tarefa[2];
        int enviar = 2;
        buf[0] = -1;
        buf[1] = 0;

        for (;;) {
            double a = MPI_Wtime();
            MPI_Send(buf, enviar, MPI_INT, 0, TAG_RESULTADO, MPI_COMM_WORLD);
            MPI_Recv(tarefa, 2, MPI_INT, 0, TAG_TAREFA, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
            double b = MPI_Wtime();
            m->t_com += b - a;

            if (tarefa[1] == 0) break;

            calcula_linhas(buf + 2, tarefa[0], tarefa[0] + tarefa[1], cfg, reg);
            m->t_comp += MPI_Wtime() - b;
            m->linhas += tarefa[1];

            buf[0] = tarefa[0];
            buf[1] = tarefa[1];
            enviar = 2 + tarefa[1] * cfg->width;
        }
    }
    free(buf);
}

static int escreve_binario(const int *matriz, const config_t *cfg) {
    char caminho[300];
    snprintf(caminho, sizeof(caminho), "%s.bin", cfg->prefixo);

    FILE *f = fopen(caminho, "wb");
    if (!f) { perror("fopen (binario)"); return -1; }

    size_t total = (size_t) cfg->width * (size_t) cfg->height;
    size_t escritos = fwrite(matriz, sizeof(int), total, f);
    fclose(f);

    if (escritos != total) {
        fprintf(stderr, "Erro: escritos %zu de %zu inteiros no binario.\n", escritos, total);
        return -1;
    }
    return 0;
}

static int escreve_pgm(const int *matriz, const config_t *cfg) {
    char caminho[300];
    snprintf(caminho, sizeof(caminho), "%s.pgm", cfg->prefixo);

    FILE *f = fopen(caminho, "wb");
    if (!f) { perror("fopen (pgm)"); return -1; }

    fprintf(f, "P5\n%d %d\n255\n", cfg->width, cfg->height);

    size_t total = (size_t) cfg->width * (size_t) cfg->height;
    unsigned char *linha = malloc(total);
    if (!linha) {
        fprintf(stderr, "Erro: falha ao alocar buffer da imagem PGM.\n");
        fclose(f);
        return -1;
    }

    for (int y = 0; y < cfg->height; y++) {
        int py = cfg->height - 1 - y;
        for (int px = 0; px < cfg->width; px++) {
            int it = matriz[(size_t) py * cfg->width + px];
            linha[(size_t) y * cfg->width + px] = (it >= cfg->max_iter) ? 0 : (unsigned char) (255.0 * (double) it / (double) cfg->max_iter);
        }
    }

    size_t escritos = fwrite(linha, 1, total, f);
    free(linha);
    fclose(f);

    if (escritos != total) {
        fprintf(stderr, "Erro: escritos %zu de %zu bytes no PGM.\n", escritos, total);
        return -1;
    }
    return 0;
}

int main(int argc, char **argv) {
    MPI_Init(&argc, &argv);

    int rank, nprocs;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &nprocs);

    config_t cfg;
    config_padrao(&cfg);

    int rc = parse_argumentos(argc, argv, &cfg, rank);
    if (rc != 0) {
        MPI_Finalize();
        return rc > 0 ? EXIT_SUCCESS : EXIT_FAILURE;
    }
    if (cfg.estrategia == EST_MESTRE && nprocs < 2) {
        if (rank == 0) fprintf(stderr, "Erro: a estrategia mestre precisa de pelo menos 2 processos.\n");
        MPI_Finalize();
        return EXIT_FAILURE;
    }

    double aspecto = (double) cfg.height / (double) cfg.width;
    double largura_im = cfg.largura_re * aspecto;

    regiao_t reg;
    reg.re_min = cfg.centro_re - cfg.largura_re / 2.0;
    reg.re_max = cfg.centro_re + cfg.largura_re / 2.0;
    reg.im_min = cfg.centro_im - largura_im / 2.0;
    reg.im_max = cfg.centro_im + largura_im / 2.0;

    size_t total = (size_t) cfg.width * (size_t) cfg.height;
    int *matriz = NULL;
    if (rank == 0) {
        fprintf(stderr,
            "Config: %dx%d pixels, MAX_ITER=%d, processos=%d\n"
            "Estrategia: %s (chunk=%d)\n"
            "Regiao: Re em [%.9g, %.9g], Im em [%.9g, %.9g]\n"
            "Saida:  %s.bin / %s.pgm\n",
            cfg.width, cfg.height, cfg.max_iter, nprocs,
            nome_estrategia[cfg.estrategia],
            cfg.estrategia == EST_BLOCO ? 0 : cfg.chunk,
            reg.re_min, reg.re_max, reg.im_min, reg.im_max,
            cfg.prefixo, cfg.prefixo);

        matriz = malloc(total * sizeof(int));
        if (!matriz) {
            fprintf(stderr, "Erro: falha ao alocar %zu inteiros (%.2f MB).\n",
                    total, (double) (total * sizeof(int)) / (1024.0 * 1024.0));
            MPI_Abort(MPI_COMM_WORLD, 1);
        }
    }

    metricas_t m;

    /* A barreira alinha todos os processos para o cronometro comecar junto. */
    MPI_Barrier(MPI_COMM_WORLD);
    double t0 = MPI_Wtime();

    if (cfg.estrategia == EST_BLOCO)
        executa_bloco(matriz, &cfg, &reg, rank, nprocs, &m);
    else if (cfg.estrategia == EST_CICLICO)
        executa_ciclico(matriz, &cfg, &reg, rank, nprocs, &m);
    else
        executa_mestre(matriz, &cfg, &reg, rank, nprocs, &m);

    /* Na raiz, aqui a matriz ja esta completa: calculo + coleta. */
    double t1 = MPI_Wtime();
    double tempo_calculo = t1 - t0;

    double *todas = NULL;
    if (rank == 0) todas = malloc((size_t) nprocs * 3 * sizeof(double));
    double minhas[3] = { m.t_comp, m.t_com, m.linhas };
    MPI_Gather(minhas, 3, MPI_DOUBLE, todas, 3, MPI_DOUBLE, 0, MPI_COMM_WORLD);

    if (rank == 0) {
        double t2 = MPI_Wtime();
        if (escreve_binario(matriz, &cfg) != 0 || escreve_pgm(matriz, &cfg) != 0) {
            free(matriz); free(todas);
            MPI_Abort(MPI_COMM_WORLD, 1);
        }
        double tempo_io = MPI_Wtime() - t2;

        /* No mestre-trabalhador o rank 0 nao calcula, entao fica fora do fator. */
        int primeiro = (cfg.estrategia == EST_MESTRE) ? 1 : 0;
        int n_calc = nprocs - primeiro;
        double soma = 0.0, maior = 0.0, menor = -1.0;
        for (int r = primeiro; r < nprocs; r++) {
            double tc = todas[3 * r];
            soma += tc;
            if (tc > maior) maior = tc;
            if (menor < 0.0 || tc < menor) menor = tc;
        }
        double media = soma / (double) n_calc;
        double fator = (media > 0.0) ? (maior / media) : 0.0;

        /* O que sobra do tempo total depois do processo mais lento e custo de comunicacao/sincronizacao. */
        double overhead = tempo_calculo - maior;
        double t_com_raiz = todas[1];

        printf("Processos:                %d\n", nprocs);
        printf("Estrategia:               %s (chunk=%d)\n", nome_estrategia[cfg.estrategia],
               cfg.estrategia == EST_BLOCO ? 0 : cfg.chunk);
        printf("Tempo de calculo (s):     %.6f\n", tempo_calculo);
        printf("Tempo de I/O (s):         %.6f\n", tempo_io);
        printf("Tempo total (s):          %.6f\n", tempo_calculo + tempo_io);
        printf("Tempo em MPI na raiz (s): %.6f\n", t_com_raiz);
        printf("Overhead de comunicacao:  %.6f s (tempo_calculo - maior computo)\n", overhead);
        printf("Fator balanceamento:      %.4f (max/media)\n", fator);
        printf("Computo max/min por rank: %.6f / %.6f\n", maior, menor);
        for (int r = 0; r < nprocs; r++) {
            printf("  rank %2d: computo %8.6f s, MPI %8.6f s, %ld linhas%s\n",
                   r, todas[3 * r], todas[3 * r + 1], (long) todas[3 * r + 2],
                   (cfg.estrategia == EST_MESTRE && r == 0) ? "  (mestre)" : "");
        }
        printf("RESULTADO,%s,%d,%d,%d,%d,%d,%.6f,%.6f,%.4f,%.6f,%.6f\n",
               nome_estrategia[cfg.estrategia],
               cfg.estrategia == EST_BLOCO ? 0 : cfg.chunk,
               cfg.width, cfg.height, cfg.max_iter, nprocs,
               tempo_calculo, tempo_io, fator, t_com_raiz, overhead);

        free(matriz);
        free(todas);
    }

    MPI_Finalize();
    return EXIT_SUCCESS;
}
