/*
  Compilacao:
    gcc -O3 -std=c11 -o mandelbrot_serial mandelbrot_serial.c
 
  Uso:
    ./mandelbrot_serial [-w largura] [-a altura] [-i max_iter]
                        [-x centro_re] [-y centro_im] [-l largura_re]
                        [-o prefixo_saida]
 
  Exemplos:
    ./mandelbrot_serial
    ./mandelbrot_serial -x -0.743643887 -y 0.131825904 -l 3.0e-3 -i 5000 -o seahorse

  O que este arquivo faz:
    Implementacao SEQUENCIAL (sem paralelismo) do gerador do conjunto de
    Mandelbrot por escape-time. Serve como REFERENCIA DE CORRETUDE: a saida
    binaria (a matriz de contagens de iteracao) produzida aqui deve ser
    identica, pixel a pixel, a saida da versao OpenMP (mandelbrot_openmp.c).
 */

/* Necessario para expor clock_gettime()/CLOCK_MONOTONIC do <time.h>,
   que nao fazem parte do C11 puro (sao extensoes POSIX). */
#define _POSIX_C_SOURCE 199309L

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

/* Agrupa todos os parametros configuraveis via linha de comando.
   Mantendo tudo em uma struct, e facil passar a configuracao inteira
   para as funcoes auxiliares com um unico ponteiro. */
typedef struct {
    int    width;        /* largura da imagem em pixels */
    int    height;       /* altura da imagem em pixels */
    int    max_iter;     /* MAX_ITER: teto de iteracoes antes de considerar "nao escapou" */
    double centro_re;    /* parte real do centro da regiao do plano complexo */
    double centro_im;    /* parte imaginaria do centro da regiao */
    double largura_re;   /* largura da regiao no eixo real (a altura em Im e derivada disso) */
    char   prefixo[256]; /* prefixo usado para nomear os arquivos de saida (.bin/.pgm) */
} config_t;

/* Valores padrao == exatamente o "input padrao" obrigatorio do enunciado
   (Secao 5.2): 4096x4096, MAX_ITER=1000, regiao Re em [-2,1], Im em [-1.5,1.5].
   Isso e o que garante que rodar o programa sem nenhuma flag ja reproduz o
   experimento oficial de referencia. */
static void config_padrao(config_t *cfg) {
    cfg->width = 4096;
    cfg->height = 4096;
    cfg->max_iter = 1000;
    cfg->centro_re = -0.5;
    cfg->centro_im = 0.0;
    cfg->largura_re = 3.0;
    strncpy(cfg->prefixo, "mandelbrot", sizeof(cfg->prefixo) - 1);
    cfg->prefixo[sizeof(cfg->prefixo) - 1] = '\0';
}

static void imprime_uso(const char *prog) {
    fprintf(stderr,
        "Uso: %s [-w largura] [-a altura] [-i max_iter] [-x centro_re] "
        "[-y centro_im] [-l largura_re] [-o prefixo_saida]\n", prog);
}

/* Parser manual de argumentos (sem getopt) para manter o binario 100%
   portavel entre sistemas. Cada flag consome o proprio token e o seguinte
   (o valor); qualquer flag desconhecida ou valor faltando aborta com uso. */
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
        } else if (strcmp(argv[i], "-o") == 0) {
            if (++i >= argc) { imprime_uso(argv[0]); return -1; }
            strncpy(cfg->prefixo, argv[i], sizeof(cfg->prefixo) - 1);
            cfg->prefixo[sizeof(cfg->prefixo) - 1] = '\0';
        } else {
            imprime_uso(argv[0]);
            return -1;
        }
    }
    /* Validacao basica: dimensoes e MAX_ITER precisam ser positivos, senao
       o calculo de indices e a alocacao da matriz nao fazem sentido. */
    if (cfg->width <= 0 || cfg->height <= 0 || cfg->max_iter <= 0 || cfg->largura_re <= 0.0) {
        fprintf(stderr, "Erro: largura, altura, max_iter e largura_re devem ser positivos.\n");
        return -1;
    }
    return 0;
}

/* Relogio monotonico (CLOCK_MONOTONIC) em vez de time()/clock(): nao sofre
   saltos por ajuste de horario do sistema e tem resolucao de nanossegundos,
   o que e essencial para medir tempos de execucao confiaveis. */
static double agora(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double) ts.tv_sec + (double) ts.tv_nsec / 1e9;
}

/* Nucleo do algoritmo: aplica a recorrencia z_(n+1) = z_n^2 + c, comecando
   de z_0 = 0, e conta quantas iteracoes sao necessarias ate |z| > 2 (o
   "raio de escape"). Compara |z|^2 > 4 em vez de sqrt(|z|^2) > 2 para evitar
   uma raiz quadrada por iteracao -- resultado matematicamente identico, mais
   barato. Se o ponto nao escapar dentro de max_iter iteracoes, e considerado
   parte do conjunto e a funcao retorna max_iter. */
static int escape_time(double cre, double cim, int max_iter) {
    double zre = 0.0, zim = 0.0;

    for (int i = 0; i < max_iter; i++) {
        double zre2 = zre * zre;
        double zim2 = zim * zim;
        /* novo Im(z) precisa ser calculado antes de sobrescrever zre,
           pois depende do zre "antigo" (2*Re(z)*Im(z) + Im(c)) */
        double novo_zim = 2.0 * zre * zim + cim;
        zre = zre2 - zim2 + cre;   /* Re(z^2 + c) = Re(z)^2 - Im(z)^2 + Re(c) */
        zim = novo_zim;

        if (zre * zre + zim * zim > 4.0) {
            return i; /* escapou na iteracao i */
        }
    }
    return max_iter; /* nao escapou: considerado dentro do conjunto */
}

/* Varre todos os pixels da imagem em ordem row-major (linha a linha) e
   preenche a matriz de saida. Para cada pixel (px, py), o ponto complexo c
   correspondente e obtido por interpolacao linear entre os limites da
   regiao (re_min..re_max, im_min..im_max). */
static void gera_mandelbrot(int *matriz, const config_t *cfg,
                            double re_min, double re_max,
                            double im_min, double im_max) {
    for (int py = 0; py < cfg->height; py++) {
        double cim = im_min + (double) py * (im_max - im_min) / (double) (cfg->height - 1);
        for (int px = 0; px < cfg->width; px++) {
            double cre = re_min + (double) px * (re_max - re_min) / (double) (cfg->width - 1);
            /* indice row-major: linha * largura + coluna; size_t evita
               overflow de "int" em imagens grandes (ex.: 4096*4096 > 16M) */
            matriz[(size_t) py * cfg->width + px] = escape_time(cre, cim, cfg->max_iter);
        }
    }
}

/* Grava a matriz de contagens em binario cru: inteiros de 32 bits, ordem
   row-major, sem cabecalho -- exatamente o formato canonico pedido no
   enunciado (Secao 5.4), usado depois para validar corretude entre versoes. */
static int escreve_binario(const int *matriz, const config_t *cfg) {
    char caminho[300];
    snprintf(caminho, sizeof(caminho), "%s.bin", cfg->prefixo);

    FILE *f = fopen(caminho, "wb");
    if (!f) {
        perror("fopen (binario)");
        return -1;
    }
    size_t total = (size_t) cfg->width * (size_t) cfg->height;
    size_t escritos = fwrite(matriz, sizeof(int), total, f);
    fclose(f);

    if (escritos != total) {
        fprintf(stderr, "Erro: escritos %zu de %zu inteiros no binario.\n", escritos, total);
        return -1;
    }
    return 0;
}

/* Gera uma imagem PGM (P5 = escala de cinza binaria) apenas para conferencia
   visual humana; a validacao de corretude usa o .bin, nunca esta imagem. */
static int escreve_pgm(const int *matriz, const config_t *cfg) {
    char caminho[300];
    snprintf(caminho, sizeof(caminho), "%s.pgm", cfg->prefixo);

    FILE *f = fopen(caminho, "wb");
    if (!f) {
        perror("fopen (pgm)");
        return -1;
    }

    /* Cabecalho PGM binario: "P5", largura, altura, valor maximo por pixel (255) */
    fprintf(f, "P5\n%d %d\n255\n", cfg->width, cfg->height);

    size_t total = (size_t) cfg->width * (size_t) cfg->height;
    unsigned char *linha = malloc(total);
    if (!linha) {
        fprintf(stderr, "Erro: falha ao alocar buffer da imagem PGM.\n");
        fclose(f);
        return -1;
    }

    /* A matriz e calculada com py=0 correspondendo a im_min (base da regiao),
       mas por convencao de imagem o topo do arquivo deve ser o Im mais alto.
       Por isso o loop le a matriz de baixo para cima (py = height-1-y)
       enquanto escreve o buffer de cima para baixo (y crescente). */
    for (int y = 0; y < cfg->height; y++) {
        int py = cfg->height - 1 - y;
        for (int px = 0; px < cfg->width; px++) {
            int it = matriz[(size_t) py * cfg->width + px];
            /* Escala linear simples: it=0 -> pixel escuro, it=max_iter -> 0 (preto,
               convencionando "dentro do conjunto" = preto); mapeamento linear
               (sem log) e suficiente para a inspecao visual desta versao. */
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

    /* A regiao no eixo imaginario e derivada da largura no eixo real e da
       razao de aspecto da imagem, garantindo pixels "quadrados" (sem
       distorcer o fractal) mesmo se width != height. */
    double aspecto = (double) cfg.height / (double) cfg.width;
    double largura_im = cfg.largura_re * aspecto;

    double re_min = cfg.centro_re - cfg.largura_re / 2.0;
    double re_max = cfg.centro_re + cfg.largura_re / 2.0;
    double im_min = cfg.centro_im - largura_im / 2.0;
    double im_max = cfg.centro_im + largura_im / 2.0;

    fprintf(stderr,
        "Config: %dx%d pixels, MAX_ITER=%d\n"
        "Regiao: Re em [%.9g, %.9g], Im em [%.9g, %.9g]\n"
        "Saida:  %s.bin / %s.pgm\n",
        cfg.width, cfg.height, cfg.max_iter,
        re_min, re_max, im_min, im_max,
        cfg.prefixo, cfg.prefixo);

    size_t total = (size_t) cfg.width * (size_t) cfg.height;
    int *matriz = malloc(total * sizeof(int));
    if (!matriz) {
        fprintf(stderr, "Erro: falha ao alocar %zu inteiros (%.2f MB).\n",
                total, (double) (total * sizeof(int)) / (1024.0 * 1024.0));
        return EXIT_FAILURE;
    }

    /* Tempo de calculo medido separadamente do tempo de E/S, conforme
       pedido no enunciado (metricas obrigatorias). */
    double t0 = agora();
    gera_mandelbrot(matriz, &cfg, re_min, re_max, im_min, im_max);
    double t1 = agora();
    double tempo_calculo = t1 - t0;

    double t2 = agora();
    if (escreve_binario(matriz, &cfg) != 0 || escreve_pgm(matriz, &cfg) != 0) {
        free(matriz);
        return EXIT_FAILURE;
    }
    double t3 = agora();
    double tempo_io = t3 - t2;

    /* Contagem informativa de quantos pixels pertencem ao conjunto (it >=
       max_iter), util para conferir rapidamente se os parametros de regiao
       fazem sentido (ex.: um valor de 0% pode indicar regiao/centro errados). */
    size_t pixels_no_conjunto = 0;
    for (size_t idx = 0; idx < total; idx++) {
        if (matriz[idx] >= cfg.max_iter) pixels_no_conjunto++;
    }

    printf("Tempo de calculo (s): %.6f\n", tempo_calculo);
    printf("Tempo de I/O (s):     %.6f\n", tempo_io);
    printf("Tempo total (s):      %.6f\n", tempo_calculo + tempo_io);
    printf("Pixels no conjunto:   %zu de %zu (%.4f%%)\n",
           pixels_no_conjunto, total, 100.0 * (double) pixels_no_conjunto / (double) total);

    free(matriz);
    return EXIT_SUCCESS;
}
