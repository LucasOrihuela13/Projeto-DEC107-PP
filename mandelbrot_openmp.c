/*
  Compilacao:
    gcc -O3 -std=c11 -fopenmp -o mandelbrot_openmp mandelbrot_openmp.c
 
  Uso:
    ./mandelbrot_openmp [-w largura] [-a altura] [-i max_iter]
                        [-x centro_re] [-y centro_im] [-l largura_re]
                        [-t threads] [-o prefixo_saida]
 
  Politica de escalonamento e chunk (variavel de ambiente OMP_SCHEDULE):
    OMP_SCHEDULE="static"       ./mandelbrot_openmp ...
    OMP_SCHEDULE="dynamic,16"   ./mandelbrot_openmp ...
    OMP_SCHEDULE="guided,32"    ./mandelbrot_openmp ...
 
  O numero de threads pode vir de -t OU de OMP_NUM_THREADS (-t tem prioridade).
 */

#define _POSIX_C_SOURCE 199309L

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <omp.h>

typedef struct {
    int    width;
    int    height;
    int    max_iter;
    double centro_re;
    double centro_im;
    double largura_re;
    int    threads;
    char   prefixo[256];
} config_t;

static void config_padrao(config_t *cfg) {
    cfg->width = 4096;
    cfg->height = 4096;
    cfg->max_iter = 1000;
    cfg->centro_re = -0.5;
    cfg->centro_im = 0.0;
    cfg->largura_re = 3.0;
    cfg->threads = 0;
    strncpy(cfg->prefixo, "mandelbrot_omp", sizeof(cfg->prefixo) - 1);
    cfg->prefixo[sizeof(cfg->prefixo) - 1] = '\0';
}

static void imprime_uso(const char *prog) {
    fprintf(stderr,
        "Uso: %s [-w largura] [-a altura] [-i max_iter] [-x centro_re] "
        "[-y centro_im] [-l largura_re] [-t threads] [-o prefixo_saida]\n", prog);
}

static int parse_argumentos(int argc, char **argv, config_t *cfg) {
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "-h") == 0 || strcmp(argv[i], "--help") == 0) {
            imprime_uso(argv[0]);
            exit(EXIT_SUCCESS);
        } else if (strcmp(argv[i], "-w") == 0) {
            if (++i >= argc) { imprime_uso(argv[0]); return -1; }
            cfg->width = atoi(argv[i]);
        } else if (strcmp(argv[i], "-a") == 0) {
            if (++i >= argc) { imprime_uso(argv[0]); return -1; }
            cfg->height = atoi(argv[i]);
        } else if (strcmp(argv[i], "-i") == 0) {
            if (++i >= argc) { imprime_uso(argv[0]); return -1; }
            cfg->max_iter = atoi(argv[i]);
        } else if (strcmp(argv[i], "-x") == 0) {
            if (++i >= argc) { imprime_uso(argv[0]); return -1; }
            cfg->centro_re = atof(argv[i]);
        } else if (strcmp(argv[i], "-y") == 0) {
            if (++i >= argc) { imprime_uso(argv[0]); return -1; }
            cfg->centro_im = atof(argv[i]);
        } else if (strcmp(argv[i], "-l") == 0) {
            if (++i >= argc) { imprime_uso(argv[0]); return -1; }
            cfg->largura_re = atof(argv[i]);
        } else if (strcmp(argv[i], "-t") == 0) {
            if (++i >= argc) { imprime_uso(argv[0]); return -1; }
            cfg->threads = atoi(argv[i]);
        } else if (strcmp(argv[i], "-o") == 0) {
            if (++i >= argc) { imprime_uso(argv[0]); return -1; }
            strncpy(cfg->prefixo, argv[i], sizeof(cfg->prefixo) - 1);
            cfg->prefixo[sizeof(cfg->prefixo) - 1] = '\0';
        } else {
            imprime_uso(argv[0]);
            return -1;
        }
    }
    if (cfg->width <= 0 || cfg->height <= 0 || cfg->max_iter <= 0 || cfg->largura_re <= 0.0) {
        fprintf(stderr, "Erro: largura, altura, max_iter e largura_re devem ser positivos.\n");
        return -1;
    }
    return 0;
}

static double agora(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double) ts.tv_sec + (double) ts.tv_nsec / 1e9;
}

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

static void gera_mandelbrot_omp(int *matriz, const config_t *cfg,
                                double re_min, double re_max,
                                double im_min, double im_max,
                                double *tempos_thread, long *linhas_thread,
                                int *nthreads_usadas) {
    #pragma omp parallel
    {
        int tid = omp_get_thread_num();

        #pragma omp master
        {
            *nthreads_usadas = omp_get_num_threads();
        }

        double t_ini = omp_get_wtime();
        long linhas_local = 0;

        #pragma omp for schedule(runtime) nowait
        for (int py = 0; py < cfg->height; py++) {
            double cim = im_min + (double) py * (im_max - im_min) / (double) (cfg->height - 1);
            for (int px = 0; px < cfg->width; px++) {
                double cre = re_min + (double) px * (re_max - re_min) / (double) (cfg->width - 1);
                matriz[(size_t) py * cfg->width + px] = escape_time(cre, cim, cfg->max_iter);
            }
            linhas_local++;
        }

        double t_fim = omp_get_wtime();
        tempos_thread[tid] = t_fim - t_ini;
        linhas_thread[tid] = linhas_local;
    }
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
    config_t cfg;
    config_padrao(&cfg);

    if (parse_argumentos(argc, argv, &cfg) != 0) {
        return EXIT_FAILURE;
    }
    if (cfg.threads > 0) {
        omp_set_num_threads(cfg.threads);
    }

    double aspecto = (double) cfg.height / (double) cfg.width;
    double largura_im = cfg.largura_re * aspecto;

    double re_min = cfg.centro_re - cfg.largura_re / 2.0;
    double re_max = cfg.centro_re + cfg.largura_re / 2.0;
    double im_min = cfg.centro_im - largura_im / 2.0;
    double im_max = cfg.centro_im + largura_im / 2.0;

    int max_threads = omp_get_max_threads();
    double *tempos_thread = calloc((size_t) max_threads, sizeof(double));
    long *linhas_thread = calloc((size_t) max_threads, sizeof(long));
    int nthreads_usadas = 0;

    fprintf(stderr,
        "Config: %dx%d pixels, MAX_ITER=%d, threads(max)=%d\n"
        "Regiao: Re em [%.9g, %.9g], Im em [%.9g, %.9g]\n"
        "Saida:  %s.bin / %s.pgm\n",
        cfg.width, cfg.height, cfg.max_iter, max_threads,
        re_min, re_max, im_min, im_max,
        cfg.prefixo, cfg.prefixo);

    size_t total = (size_t) cfg.width * (size_t) cfg.height;
    int *matriz = malloc(total * sizeof(int));
    if (!matriz || !tempos_thread || !linhas_thread) {
        fprintf(stderr, "Erro: falha de alocacao.\n");
        free(matriz);
        free(tempos_thread);
        free(linhas_thread);
        return EXIT_FAILURE;
    }

    double t0 = agora();
    gera_mandelbrot_omp(matriz, &cfg, re_min, re_max, im_min, im_max,
                         tempos_thread, linhas_thread, &nthreads_usadas);
    double t1 = agora();
    double tempo_calculo = t1 - t0;

    double t2 = agora();
    if (escreve_binario(matriz, &cfg) != 0 || escreve_pgm(matriz, &cfg) != 0) {
        free(matriz); free(tempos_thread); free(linhas_thread);
        return EXIT_FAILURE;
    }
    double t3 = agora();
    double tempo_io = t3 - t2;

    double soma = 0.0, maior = 0.0, menor = -1.0;
    for (int i = 0; i < nthreads_usadas; i++) {
        soma += tempos_thread[i];
        if (tempos_thread[i] > maior) maior = tempos_thread[i];
        if (menor < 0.0 || tempos_thread[i] < menor) menor = tempos_thread[i];
    }
    double media = soma / (double) nthreads_usadas;
    double fator_balanceamento = (media > 0.0) ? (maior / media) : 0.0;

    printf("Threads usadas:         %d\n", nthreads_usadas);
    printf("Tempo de calculo (s):   %.6f\n", tempo_calculo);
    printf("Tempo de I/O (s):       %.6f\n", tempo_io);
    printf("Tempo total (s):        %.6f\n", tempo_calculo + tempo_io);
    printf("Fator balanceamento:    %.4f (max/media)\n", fator_balanceamento);
    printf("Tempo max/min por thread: %.6f / %.6f\n", maior, menor);
    for (int i = 0; i < nthreads_usadas; i++) {
        printf("  thread %2d: %8.6f s, %ld linhas\n", i, tempos_thread[i], linhas_thread[i]);
    }
    printf("RESULTADO,%d,%d,%d,%d,%.6f,%.6f,%.4f\n",
           cfg.width, cfg.height, cfg.max_iter, nthreads_usadas,
           tempo_calculo, tempo_io, fator_balanceamento);

    free(matriz);
    free(tempos_thread);
    free(linhas_thread);
    return EXIT_SUCCESS;
}