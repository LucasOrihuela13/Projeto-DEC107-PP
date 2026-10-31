"""
Subsecoes 2.4 a 2.8 do Relatorio da Etapa 2.
Importado por gera_relatorio.py. Nenhum numero e digitado, todos vem de 'd'.
"""

from gera_relatorio import num


def constroi_estrategias(rel, d):
    rel.h2("2.4 Estratégias de Distribuição Avaliadas")

    rel.p(
        "Foram implementadas três estratégias de distribuição do domínio da imagem, "
        "selecionáveis em tempo de execução. Elas foram escolhidas para cobrir o "
        "espectro entre comunicação mínima com balanceamento ruim e balanceamento "
        "ótimo com comunicação elevada:"
    )

    rel.legenda_tabela("Estratégias de distribuição implementadas em MPI")
    rel.tabela(
        ["Estratégia", "Ideia", "Coleta do resultado", "Equivalente na Etapa 1"],
        [
            [
                "bloco",
                "Cada processo recebe uma faixa contígua de linhas, e as linhas "
                "excedentes vão para os primeiros ranks",
                "MPI_Gatherv direto na matriz final, com MPI_IN_PLACE na raiz",
                "static sem chunk",
            ],
            [
                "ciclico",
                "Blocos de chunk linhas distribuídos em round-robin entre os processos",
                "MPI_Gatherv em buffer intermediário, seguido de reordenação na raiz",
                "static com chunk",
            ],
            [
                "mestre",
                "O rank 0 apenas coordena e entrega chunk linhas a quem estiver livre",
                "Cada trabalhador devolve o resultado junto com o pedido seguinte",
                "dynamic com chunk",
            ],
        ],
    )

    rel.p(
        "A decisão de incluir chunk de valor 1 nas estratégias cíclica e "
        "master-worker é deliberada e repete o raciocínio validado na Etapa 1. A "
        "região de custo máximo do fractal é contígua e concentrada, e a "
        "granularidade fina é o mecanismo que dilui essa região entre os processos. "
        "Comparar chunk 1 contra chunk 16 permite quantificar o compromisso entre "
        "diluição da carga e custo de comunicação, que nesta etapa é mais caro do "
        "que era em memória compartilhada."
    )

    rel.p(
        "Duas propriedades estruturais do esquema master-worker precisam ser "
        "registradas desde já, porque condicionam a leitura de todos os resultados. "
        "A primeira é que o rank 0 não calcula nada, de modo que com p processos "
        "apenas p − 1 produzem trabalho útil. A segunda, que decorre da primeira, é "
        "que a estratégia exige no mínimo dois processos e por isso não aparece nos "
        "cenários com p = 1."
    )


def constroi_metricas(rel, d):
    rel.h2("2.5 Métricas de Desempenho")

    rel.p(
        "Foram adotadas exclusivamente as métricas definidas na Aula 03, "
        "Caracterização de desempenho em programas paralelos. A notação segue o "
        "material, com n representando o tamanho do problema e p o número de "
        "processos."
    )

    rel.bullet(
        " T(n, p) é o tempo total de execução, medido do instante em que o primeiro "
        "processo começa até que o último processo complete a sua última instrução. "
        "Na prática, é o tempo decorrido entre a MPI_Barrier inicial e o instante em "
        "que a matriz completa está disponível na raiz, ou seja, computação mais "
        "coleta. O tempo de escrita em disco é medido separadamente e reportado à "
        "parte, conforme exige o enunciado.",
        negrito_ate="Tempo de execução:",
    )
    rel.bullet(
        " S(n, p) = T(n) / T(n, p), onde T(n) é o tempo da versão sequencial de "
        f"referência para o mesmo tamanho de problema, medido com "
        f"{d['reps_serial']} repetições.",
        negrito_ate="Speedup:",
    )
    rel.bullet(
        " E(n, p) = S(n, p) / p = T(n) / (p · T(n, p)), que quantifica o "
        "aproveitamento de cada processo.",
        negrito_ate="Eficiência:",
    )
    rel.bullet(
        " F_LB(n) = (T_max(n) − T_min(n)) / T_max(n), onde T_max é o tempo do último "
        "processo a terminar e T_min é o tempo do primeiro. O valor 0 indica "
        "balanceamento perfeito e valores próximos de 1 indicam desbalanceamento "
        "acentuado.",
        negrito_ate="Fator de balanceamento de carga:",
    )
    rel.bullet(
        " G(n) = T_cp(n) / T_cm(n), que expressa a relação entre a quantidade de "
        "computação e a quantidade de comunicação. Valores altos indicam "
        "granularidade grossa e valores baixos indicam granularidade fina.",
        negrito_ate="Granularidade:",
    )
    rel.bullet(
        " T_0(n, p) = p · T(n, p) − T(n), que mede o trabalho adicional introduzido "
        "pela paralelização em relação ao programa sequencial equivalente.",
        negrito_ate="Sobrecarga:",
    )

    rel.p(
        "Conforme pede o modelo de relatório, é necessário indicar explicitamente o "
        "que foi considerado em cada tempo e como ele foi medido. Os critérios "
        "adotados foram os seguintes:"
    )

    rel.bullet(
        " abrange exclusivamente as chamadas à função escape_time e o laço que "
        "percorre os pixels atribuídos ao processo. Não inclui nenhuma chamada de "
        "MPI nem a escrita em disco.",
        negrito_ate="T_max, T_min e T_cp:",
    )
    rel.bullet(
        " é o tempo acumulado dentro de chamadas de MPI. É importante registrar que "
        "essa medida agrega duas das três parcelas descritas na Aula 03, o tempo de "
        "comunicação propriamente dito e o tempo ocioso de espera, pois um processo "
        "que termina cedo e bloqueia em MPI_Gatherv permanece dentro da chamada até "
        "que o processo mais lento chegue. Essa distinção é decisiva para a leitura "
        "da granularidade e será retomada na Seção 4.",
        negrito_ate="T_cm:",
    )
    rel.bullet(
        " o fator foi calculado apenas sobre os processos que efetivamente calculam. "
        "No esquema master-worker, o rank 0 coordena sem computar, e incluí-lo "
        "produziria T_min igual a zero e um fator artificialmente igual a 1 em todos "
        "os casos, o que não descreveria o balanceamento real entre os "
        "trabalhadores.",
        negrito_ate="Escopo do fator de balanceamento:",
    )
    rel.bullet(
        " definido como T(n, p) − T_max, ou seja, o que resta do tempo total depois "
        "de descontar o trabalho útil do processo mais lento. Diferentemente de "
        "T_cm, essa medida não contabiliza a espera dos processos rápidos, e por "
        "isso é a estimativa mais honesta do custo líquido de comunicação e "
        "sincronização.",
        negrito_ate="Custo líquido de comunicação:",
    )

    rel.p(
        "Cabe uma observação de continuidade metodológica. A Etapa 1 utilizou, para "
        "o fator de balanceamento, a razão entre o tempo máximo e o tempo médio "
        "entre threads, cujo valor ideal é 1. A definição adotada nesta etapa é a "
        "da Aula 03, F_LB(n) = (T_max − T_min) / T_max, cujo valor ideal é 0. As "
        "duas grandezas medem o mesmo fenômeno, porém em escalas distintas e não "
        "são numericamente comparáveis entre si. Por esse motivo, sempre que este "
        "relatório confrontar o balanceamento das duas etapas, a comparação será "
        "feita no plano qualitativo, pela ordenação relativa das estratégias, e "
        "nunca pela diferença absoluta entre os valores."
    )


def constroi_planejamento(rel, d):
    rel.h2("2.6 Planejamento dos Experimentos")

    rel.p(
        "Os experimentos cobrem os três blocos obrigatórios do enunciado, aplicados "
        "a cada uma das cinco configurações de estratégia e chunk avaliadas:"
    )

    rel.bullet(
        " resolução fixa de 4096 × 4096 e MAX_ITER = 1000, variando o número de "
        "processos em 1, 2, 4, 8 e 16.",
        negrito_ate="Escalabilidade forte:",
    )
    rel.bullet(
        " trabalho por processo aproximadamente constante, escalando a resolução "
        "junto com o número de processos segundo N = 4096 · √p. As resoluções foram "
        "4096², 5793², 8192², 11585² e 16384² para 1, 2, 4, 8 e 16 processos, "
        "respectivamente. Esses são exatamente os mesmos pontos utilizados na Etapa "
        "1, o que permite comparação direta entre os dois paradigmas, e incluem as "
        "três resoluções citadas no enunciado.",
        negrito_ate="Escalabilidade fraca:",
    )
    rel.bullet(
        " região do vale dos cavalos-marinhos, centrada em -0,743643887 e "
        "0,131825904, com largura real de 3,0 × 10⁻³ e MAX_ITER = 5000, para 2, 4, 8 "
        "e 16 processos. Essa região concentra grande quantidade de pixels de custo "
        "elevado e evidencia os problemas de distribuição de trabalho.",
        negrito_ate="Caso de desbalanceamento acentuado:",
    )

    rel.p(
        "Uma decisão importante distingue o planejamento da escalabilidade fraca "
        "nesta etapa. A métrica de eficiência definida na Aula 03 é "
        "E(n, p) = T(n) / (p · T(n, p)), e o numerador exige o tempo sequencial no "
        "mesmo tamanho de problema n do caso paralelo. Como na escalabilidade fraca "
        "o tamanho do problema muda a cada ponto, não é suficiente dispor de um "
        "único baseline sequencial em 4096². Por esse motivo, foi medido um baseline "
        "sequencial independente para cada uma das cinco resoluções, o que torna "
        "possível aplicar a mesma fórmula de eficiência em todos os cenários do "
        "relatório, sem recorrer a nenhuma definição externa ao material da "
        "disciplina."
    )

    rel.p(
        f"Cada configuração paralela dos cenários de escalabilidade forte e de zoom "
        f"foi executada {d['reps_par']} vezes, e cada configuração de escalabilidade "
        f"fraca foi executada {d['reps_weak']} vezes, reportando-se média e desvio "
        f"padrão. Os baselines sequenciais do input padrão e do zoom foram medidos "
        f"com {d['reps_serial']} repetições, e os baselines por resolução da "
        f"escalabilidade fraca com {d['reps_weak']} repetições. Ao todo foram "
        f"registradas {d['n_execucoes']} execuções paralelas."
    )


def constroi_validacao(rel, d):
    rel.h2("2.7 Validação da Corretude")

    rel.p(
        "A corretude foi validada comparando bit a bit a matriz de contagens gerada "
        "por cada estratégia paralela contra a matriz da versão sequencial de "
        "referência, tanto no input padrão quanto no caso de zoom. A comparação é "
        "feita com o utilitário cmp sobre os arquivos binários, o que detecta "
        "qualquer divergência de um único byte."
    )

    rel.p(
        "Por se tratar de problema determinístico, com contagens inteiras e "
        "aritmética idêntica por pixel, a expectativa do enunciado é de igualdade "
        "exata, admitindo-se no máximo divergência em 0,01% dos pixels de fronteira. "
        "A validação é executada automaticamente como etapa obrigatória do script de "
        "experimentos, que interrompe toda a bateria caso qualquer estratégia "
        "divirja da referência. Dessa forma, nenhum número de desempenho pode ser "
        "coletado a partir de uma implementação incorreta."
    )

    rel.p(
        "Além da validação automática da coleta final, a implementação foi testada "
        "com 1, 2, 3, 5 e 7 processos nas três estratégias, com chunks de 1, 3, 16 e "
        "1000, incluindo alturas de imagem que não são divisíveis pelo número de "
        "processos. Esse último caso é o que exercita o tratamento das linhas "
        "excedentes e justifica o uso de MPI_Gatherv no lugar de MPI_Gather."
    )


def constroi_coleta(rel, d):
    rel.h2("2.8 Procedimento de Coleta")

    rel.p(
        "O fluxo de coleta foi integralmente automatizado e executado com o "
        "governador de frequência fixado em performance, por meio do wrapper "
        "roda_com_performance_mpi.sh, na seguinte ordem:"
    )

    for i, passo in enumerate(
        [
            "Compilação do binário MPI com mpicc e do binário sequencial de "
            "referência com gcc, ambos com -O3 -std=c11.",
            "Validação de corretude bit a bit das três estratégias, no input padrão "
            "e no caso de zoom, com interrupção da bateria em caso de divergência.",
            "Medição dos baselines sequenciais T(n) do input padrão e do zoom.",
            "Medição dos baselines sequenciais T(n) para cada resolução da "
            "escalabilidade fraca.",
            "Execução da matriz de experimentos de escalabilidade forte e do caso "
            "de zoom, com saída em resultados_mpi.csv.",
            "Execução da matriz de escalabilidade fraca, com saída no mesmo arquivo.",
            "Pós-processamento e geração dos gráficos com pos_processa_mpi.py, com "
            "saída em resultados_agregados_mpi.csv.",
        ],
        start=1,
    ):
        rel.doc.add_paragraph(f"{i}. {passo}", style="List Number")

    rel.p(
        "O arquivo resultados_mpi.csv registra em seu cabeçalho as condições do "
        "ambiente, incluindo sistema operacional, compilador, versão do MPI, modelo "
        "de processador e número de CPUs lógicas, atendendo à exigência do enunciado "
        "de documentar detalhadamente o ambiente de execução. Cada execução do "
        "binário MPI emite uma linha em formato CSV com os tempos e o detalhamento "
        f"por processo, e a bateria completa levou {d['duracao_bateria']} para ser "
        "concluída."
    )
