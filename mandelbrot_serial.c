/*
  Compilacao:
    gcc -O3 -std=c11 -o mandelbrot_serial mandelbrot_serial.c -lm
 
  Uso:
    ./mandelbrot_serial [-w largura] [-a|-h altura] [-i max_iter]
                        [-x centro_re] [-y centro_im] [-l largura_re]
                        [-s 0|1] [-o prefixo_saida]
 
    -s 0  desativa a exploracao de simetria, use -s 0 para
          gerar a linha de base "sem bonus" dos experimentos de desempenho.
          . Padrao: -s 1 (ativa).

  Exemplos:
    ./mandelbrot_serial
    ./mandelbrot_serial -x -0.743643887 -y 0.131825904 -l 3.0e-3 -i 5000 -o seahorse

  O que este arquivo faz:
    Mesma referencia de corretude sequencial da branch "main", acrescida de
    tres otimizacoes que reduzem trabalho sem mudar o resultado de nenhum
    pixel: early-exit analitico para pontos dentro da cardioide/bulbo
    principal, deteccao de ciclo (Brent) e exploracao de simetria do eixo
    real. Tambem troca a imagem de saida de PGM (cinza) para PPM (colorida).
    Ver o README do repositorio para o detalhamento de cada otimizacao.
 */
#define _POSIX_C_SOURCE 199309L

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <math.h>   /* log1p(), usada na colorizacao logaritmica */

typedef struct {
    int    width;
    int    height;
    int    max_iter;
    double centro_re;
    double centro_im;
    double largura_re;
    int    simetria;   /* 1 = explora simetria do eixo real (padrao), 0 = desativa (baseline "sem bonus") */
    char   prefixo[256];
} config_t;

static void config_padrao(config_t *cfg) {
    cfg->width = 4096;
    cfg->height = 4096;
    cfg->max_iter = 1000;
    cfg->centro_re = -0.5;
    cfg->centro_im = 0.0;
    cfg->largura_re = 3.0;
    cfg->simetria = 1;
    strncpy(cfg->prefixo, "mandelbrot", sizeof(cfg->prefixo) - 1);
    cfg->prefixo[sizeof(cfg->prefixo) - 1] = '\0';
}

static void imprime_uso(const char *prog) {
    fprintf(stderr,
        "Uso: %s [-w largura] [-a|-h altura] [-i max_iter] [-x centro_re] "
        "[-y centro_im] [-l largura_re] [-s 0|1] [-o prefixo_saida]\n"
        "  -s 0 desativa a exploracao de simetria (linha de base sem bonus)\n"
        "  --help para esta ajuda (-h e altura, nao ajuda)\n", prog);
}

/* ATENCAO: diferente da branch "main", aqui "-h" significa ALTURA (alias de
   -a), nao ajuda -- a ajuda passou a ser "--help" ou "-?". Isso foi
   necessario para abrir espaco para a nova flag -s (simetria). */
static int parse_argumentos(int argc, char **argv, config_t *cfg) {
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--help") == 0 || strcmp(argv[i], "-?") == 0) {
            imprime_uso(argv[0]);
            exit(EXIT_SUCCESS);
        } else if (strcmp(argv[i], "-w") == 0) {
            if (++i >= argc) { imprime_uso(argv[0]); return -1; }
            cfg->width = atoi(argv[i]);
        } else if (strcmp(argv[i], "-a") == 0 || strcmp(argv[i], "-h") == 0) {
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
        } else if (strcmp(argv[i], "-s") == 0) {
            if (++i >= argc) { imprime_uso(argv[0]); return -1; }
            cfg->simetria = (atoi(argv[i]) != 0);
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

/* Teste analitico de pertinencia: verifica se c esta DENTRO da cardioide
   principal ou do bulbo de periodo 2 do conjunto de Mandelbrot, usando as
   formulas fechadas conhecidas para essas duas regioes (sem iterar nenhuma
   vez). Pontos dentro delas SEMPRE atingem max_iter, entao identifica-los
   de antemao evita rodar o pior caso (o loop inteiro de escape_time) para
   uma fatia grande e barata de calcular da regiao interna do conjunto.
     - Cardioide principal: q*(q + (cre-1/4)) <= 1/4 * cim^2,
       onde q = (cre-1/4)^2 + cim^2.
     - Bulbo de periodo 2: circulo de raio 1/4 centrado em (-1, 0), ou seja
       (cre+1)^2 + cim^2 <= 1/16. */
static int dentro_cardioide_ou_bulbo(double cre, double cim) {
    double cre_menos_quarto = cre - 0.25;
    double cim2 = cim * cim;
    double q = cre_menos_quarto * cre_menos_quarto + cim2;
    if (q * (q + cre_menos_quarto) <= 0.25 * cim2) {
        return 1;
    }
    double cre_mais_um = cre + 1.0;
    if (cre_mais_um * cre_mais_um + cim2 <= 0.0625) { /* 0.0625 = 1/16 = raio^2 */
        return 1;
    }
    return 0;
}

/* Mesma recorrencia z_(n+1) = z_n^2 + c da versao "main", com duas
   otimizacoes adicionadas por cima (nenhuma delas muda o valor retornado
   para nenhum ponto -- apenas evitam trabalho redundante):

   1) Early-exit geometrico: se c ja esta dentro da cardioide/bulbo
      principal, sabemos de antemao que a orbita nunca escapa -> retorna
      max_iter imediatamente, sem simular nenhuma iteracao.

   2) Deteccao de ciclo (variante do algoritmo de Brent): pontos DENTRO do
      conjunto mas FORA da cardioide/bulbo (bulbos menores, "minifractais")
      tambem nunca escapam, e sem essa deteccao rodariam as max_iter
      iteracoes completas -- o pior caso de custo por pixel. O truque:
      salva-se periodicamente um ponto de referencia (ref_re, ref_im) em
      iteracoes que sao potencias de 2 (1, 2, 4, 8, ...). Se a orbita atual
      algum dia repetir EXATAMENTE esse ponto de referencia, ela entrou em
      um ciclo e portanto e periodica -- nunca vai escapar, entao pode
      parar e retornar max_iter sem esperar o teto de iteracoes. */
static int escape_time(double cre, double cim, int max_iter) {
    if (dentro_cardioide_ou_bulbo(cre, cim)) {
        return max_iter;
    }

    double zre = 0.0, zim = 0.0;
    double ref_re = 0.0, ref_im = 0.0; /* ponto de referencia para deteccao de ciclo */
    int potencia = 1, lambda = 1;      /* proxima potencia de 2 em que ref_* sera atualizado */

    for (int i = 0; i < max_iter; i++) {
        double zre2 = zre * zre;
        double zim2 = zim * zim;
        double novo_zim = 2.0 * zre * zim + cim;
        zre = zre2 - zim2 + cre;
        zim = novo_zim;

        if (zre * zre + zim * zim > 4.0) {
            return i;
        }

        /* Comparacao exata (==) em ponto flutuante e proposital aqui: um
           ciclo verdadeiro reproduz o MESMO valor bit-a-bit, entao a
           igualdade exata e um teste correto (e muito mais barato que
           comparar distancias com uma tolerancia). */
        if (zre == ref_re && zim == ref_im) {
            return max_iter;
        }
        if (lambda == potencia) {
            ref_re = zre;
            ref_im = zim;
            potencia *= 2;
            lambda = 0;
        }
        lambda++;
    }
    return max_iter;
}

/* Verifica se a linha "py" tem, na grade discreta escolhida, um espelho
   EXATO em torno do eixo real (Im=0): a linha py_espelho = height-1-py
   corresponde ao valor -cim, bit-a-bit, e nao apenas aproximadamente.
   Isso so e garantido quando a grade e simetrica em relacao a im=0 (o que
   pode falhar por arredondamento se a regiao nao estiver centrada
   exatamente nesse eixo, ou se a altura for par/impar de forma
   inconveniente). So copiamos a linha quando esse teste e verdadeiro --
   caso contrario calculamos normalmente, sem arriscar imprecisao. */
static int espelho_exato(double im_min, double passo_y, int height, int py) {
    double cim      = im_min + (double) py * passo_y;
    double cim_espelho = im_min + (double) (height - 1 - py) * passo_y;
    return cim_espelho == -cim;
}

/* Mesmo laco duplo (linhas x colunas) da versao "main", com a exploracao de
   simetria adicionada: quando a linha py tem espelho exato e ainda nao foi
   processada (py <= py_espelho), calcula-se py normalmente e o resultado e
   copiado com memcpy para a linha py_espelho -- evitando recalcular pixel a
   pixel a metade "de baixo" da imagem. Quando py > py_espelho, a linha ja
   foi preenchida por copia a partir do espelho e o "continue" pula o
   calculo. Se -s 0 (simetria desligada), "exato" e sempre falso e o
   comportamento cai exatamente no caso sem otimizacao. */
static void gera_mandelbrot(int *matriz, const config_t *cfg,
                            double re_min, double re_max,
                            double im_min, double im_max) {
    double passo_x = (re_max - re_min) / (double) (cfg->width - 1);
    double passo_y = (im_max - im_min) / (double) (cfg->height - 1);
    int usa_sim = cfg->simetria;

    for (int py = 0; py < cfg->height; py++) {
        int py_espelho = cfg->height - 1 - py;
        int exato = usa_sim && espelho_exato(im_min, passo_y, cfg->height, py);

        if (exato && py > py_espelho) {
            continue; /* linha ja preenchida via copia do seu espelho */
        }

        double cim = im_min + (double) py * passo_y;
        int *linha = &matriz[(size_t) py * cfg->width];
        for (int px = 0; px < cfg->width; px++) {
            double cre = re_min + (double) px * passo_x;
            linha[px] = escape_time(cre, cim, cfg->max_iter);
        }

        if (exato && py_espelho != py) {
            memcpy(&matriz[(size_t) py_espelho * cfg->width], linha,
                   (size_t) cfg->width * sizeof(int));
        }
    }
}

/* Converte uma contagem de iteracoes em uma cor RGB. */
static void cor_do_pixel(int it, int max_iter,
                          unsigned char *r, unsigned char *g, unsigned char *b) {
    if (it >= max_iter) {

        *r = 3;
        *g = 6;
        *b = 16;
        return;
    }

    double base = (max_iter > 1) ? (double) (max_iter - 1) : 1.0;
    double t = log1p((double) it) / log1p(base);
    if (t < 0.0) t = 0.0;
    if (t > 1.0) t = 1.0;

    double red, green, blue;

    if (t < 0.3) {
        double f = t / 0.3;
        red   =  8.0 + f * ( 18.0 -  8.0);
        green = 22.0 + f * ( 65.0 - 22.0);
        blue  = 55.0 + f * (140.0 - 55.0);
    } else if (t < 0.7) {
        double f = (t - 0.3) / 0.4;
        red   =  18.0 + f * ( 45.0 -  18.0);
        green =  65.0 + f * (140.0 -  65.0);
        blue  = 140.0 + f * (220.0 - 140.0);
    } else if (t < 0.9) {
        double f = (t - 0.7) / 0.2;
        red   =  45.0 + f * ( 90.0 -  45.0);
        green = 140.0 + f * (220.0 - 140.0);
        blue  = 220.0 + f * (245.0 - 220.0);
    } else {
        double f = (t - 0.9) / 0.1;
        red   =  90.0 + f * (245.0 -  90.0);
        green = 220.0 + f * (252.0 - 220.0);
        blue  = 245.0 + f * (255.0 - 245.0);
    }

    *r = (unsigned char) red;
    *g = (unsigned char) green;
    *b = (unsigned char) blue;
}

/* Igual a versao "main": grava a matriz de contagens em binario cru
   (row-major, int32) -- e sobre este arquivo que a corretude e validada. */
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

/* Substitui o escreve_pgm() da versao "main" por uma imagem PPM (P6,
   colorida) usando cor_do_pixel(). Mesma logica de inversao vertical
   (py = height-1-y) explicada na versao "main", so que agora escrevendo 3
   bytes (R,G,B) por pixel em vez de 1. */
static int escreve_ppm(const int *matriz, const config_t *cfg) {
    char caminho[300];
    snprintf(caminho, sizeof(caminho), "%s.ppm", cfg->prefixo);

    FILE *f = fopen(caminho, "wb");
    if (!f) {
        perror("fopen (ppm)");
        return -1;
    }

    /* Cabecalho PPM binario: "P6", largura, altura, valor maximo por canal (255) */
    fprintf(f, "P6\n%d %d\n255\n", cfg->width, cfg->height);

    size_t total = (size_t) cfg->width * (size_t) cfg->height;
    unsigned char *linha = malloc(total * 3); /* 3 bytes (RGB) por pixel */
    if (!linha) {
        fprintf(stderr, "Erro: falha ao alocar buffer da imagem PPM.\n");
        fclose(f);
        return -1;
    }

    for (int y = 0; y < cfg->height; y++) {
        int py = cfg->height - 1 - y;
        for (int px = 0; px < cfg->width; px++) {
            int it = matriz[(size_t) py * cfg->width + px];
            unsigned char r, g, b;
            cor_do_pixel(it, cfg->max_iter, &r, &g, &b);
            size_t idx = ((size_t) y * cfg->width + px) * 3;
            linha[idx + 0] = r;
            linha[idx + 1] = g;
            linha[idx + 2] = b;
        }
    }

    size_t escritos = fwrite(linha, 1, total * 3, f);
    free(linha);
    fclose(f);

    if (escritos != total * 3) {
        fprintf(stderr, "Erro: escritos %zu de %zu bytes no PPM.\n", escritos, total * 3);
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

    double aspecto = (double) cfg.height / (double) cfg.width;
    double largura_im = cfg.largura_re * aspecto;

    double re_min = cfg.centro_re - cfg.largura_re / 2.0;
    double re_max = cfg.centro_re + cfg.largura_re / 2.0;
    double im_min = cfg.centro_im - largura_im / 2.0;
    double im_max = cfg.centro_im + largura_im / 2.0;

    fprintf(stderr,
        "Config: %dx%d pixels, MAX_ITER=%d, simetria=%s\n"
        "Regiao: Re em [%.9g, %.9g], Im em [%.9g, %.9g]\n"
        "Saida:  %s.bin / %s.ppm\n",
        cfg.width, cfg.height, cfg.max_iter, cfg.simetria ? "on" : "off",
        re_min, re_max, im_min, im_max,
        cfg.prefixo, cfg.prefixo);

    size_t total = (size_t) cfg.width * (size_t) cfg.height;
    int *matriz = malloc(total * sizeof(int));
    if (!matriz) {
        fprintf(stderr, "Erro: falha ao alocar %zu inteiros (%.2f MB).\n",
                total, (double) (total * sizeof(int)) / (1024.0 * 1024.0));
        return EXIT_FAILURE;
    }

    double t0 = agora();
    gera_mandelbrot(matriz, &cfg, re_min, re_max, im_min, im_max);
    double t1 = agora();
    double tempo_calculo = t1 - t0;

    double t2 = agora();
    if (escreve_binario(matriz, &cfg) != 0 ||
        escreve_ppm(matriz, &cfg) != 0) {
        free(matriz);
        return EXIT_FAILURE;
    }
    double t3 = agora();
    double tempo_io = t3 - t2;

    size_t pixels_no_conjunto = 0;
    for (size_t idx = 0; idx < total; idx++) {
        if (matriz[idx] >= cfg.max_iter) pixels_no_conjunto++;
    }

    printf("Tempo de calculo (s): %.6f\n", tempo_calculo);
    printf("Tempo de I/O (s):     %.6f\n", tempo_io);
    printf("Tempo total (s):      %.6f\n", tempo_calculo + tempo_io);
    printf("Pixels no conjunto:   %zu de %zu (%.4f%%)\n",
           pixels_no_conjunto, total, 100.0 * (double) pixels_no_conjunto / (double) total);

    /* Linha RESULTADO da versao serial "otimizado": mantem o mesmo prefixo
       das colunas da versao openmp (largura,altura,max_iter,threads,tempo_
       calculo,tempo_io,fator_balanceamento) com threads=1 e fator=1.0000
       fixos (nao ha paralelismo aqui), e acrescenta duas colunas extras
       "serial" (identifica a origem) e o valor de "simetria" (0/1) usado. */
    printf("RESULTADO,%d,%d,%d,1,%.6f,%.6f,1.0000,serial,%d\n",
           cfg.width, cfg.height, cfg.max_iter, tempo_calculo, tempo_io,
           cfg.simetria);

    free(matriz);
    return EXIT_SUCCESS;
}
