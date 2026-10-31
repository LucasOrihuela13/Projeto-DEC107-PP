"""
Secoes 1 e 2 do Relatorio da Etapa 2, a saber Introducao e Metodologia.
Importado por gera_relatorio.py. Nenhum numero e digitado, todos vem de 'd'.
"""

from gera_relatorio import num, pct, NOMES_LONGOS


def constroi_capa(rel, d):
    rel.capa(
        linhas_titulo="Universidade Estadual de Santa Cruz (UESC)",
        subtitulo=(
            "Etapa 2 — Benchmark de Geração do Conjunto de Mandelbrot "
            "(Escape-Time): Implementação paralela em memória distribuída com MPI."
        ),
        linha_academica="Relatório acadêmico — DEC107 — Processamento Paralelo",
        autores="Cibelle Sousa Rodrigues, Lucas Braga Orihuela",
        disciplina="DEC107 — Processamento Paralelo",
        data=d["data_entrega"],
    )


def constroi_introducao(rel, d):
    rel.h1("1. Introdução")

    rel.p(
        "O objetivo desta segunda etapa do projeto é avaliar o aprendizado prático "
        "dos conceitos de processamento paralelo em memória distribuída utilizando a "
        "biblioteca MPI. Enquanto a Etapa 1 explorou o paralelismo em memória "
        "compartilhada com OpenMP, em que todas as threads enxergam a mesma matriz "
        "de resultados, esta etapa parte de um cenário diferente, no qual cada "
        "processo possui o seu próprio espaço de endereçamento e nada é "
        "compartilhado implicitamente. Toda informação que precisa circular entre os "
        "processos deve ser enviada de forma explícita por troca de mensagens."
    )

    rel.p(
        "O Conjunto de Mandelbrot é definido como o conjunto de números complexos c "
        "para os quais a sequência iterativa z_{n+1} = z_n² + c, com z_0 = 0, "
        "permanece limitada. Na implementação computacional, o algoritmo de "
        "escape-time verifica cada ponto do plano complexo mapeado, iterando essa "
        "fórmula até que o valor de |z| ultrapasse um raio de escape pré-definido, "
        "que neste projeto é |z| > 2, verificado na forma equivalente |z|² > 4. O "
        "número de iterações necessárias para que o ponto escape desse raio, "
        "limitado a um teto máximo MAX_ITER, dita a sua coloração na geração da "
        "imagem fractal."
    )

    rel.p(
        "O custo computacional de cada pixel é diretamente proporcional ao seu "
        "escape-time. Pixels localizados fora do conjunto escapam em poucas "
        "iterações, ao passo que pixels situados na fronteira ou no interior do "
        "conjunto consomem o limite máximo de iterações. Essa heterogeneidade "
        "geométrica da carga é o que torna o problema interessante como benchmark, "
        "pois ele é embaraçosamente paralelo, sem nenhuma dependência de dados entre "
        "pixels, e ao mesmo tempo fortemente desbalanceado."
    )

    rel.p(
        "Em memória distribuída esse desbalanceamento ganha uma consequência "
        "adicional que não existia na Etapa 1. Em OpenMP, uma política de "
        "escalonamento dinâmica redistribui iterações entre threads a um custo de "
        "sincronização baixo, porque a fila de trabalho e a matriz de saída residem "
        "na mesma memória. Em MPI, redistribuir trabalho significa trocar mensagens, "
        "e devolver o resultado ao processo responsável pela escrita significa "
        "transferir blocos de linhas pela rede ou pela memória do sistema. A escolha "
        "da estratégia de distribuição passa, portanto, a envolver um compromisso "
        "entre dois custos que competem entre si, o custo do desbalanceamento e o "
        "custo da comunicação."
    )

    rel.p(
        "Esse compromisso justifica a estrutura do experimento desta etapa. Foram "
        "implementadas três estratégias de distribuição do domínio da imagem, com "
        "granularidades distintas, e todas foram medidas sob os mesmos parâmetros, "
        "no mesmo binário e no mesmo ambiente. A decomposição estática por faixas "
        "contíguas representa o custo de comunicação mínimo com o pior "
        "balanceamento possível. A distribuição cíclica de blocos de linhas mantém "
        "o custo de comunicação baixo e melhora o balanceamento sem nenhuma "
        "negociação em tempo de execução. O esquema master-worker adota "
        "balanceamento dinâmico, ao preço de dedicar um processo à coordenação e de "
        "gerar tráfego de mensagens proporcional ao número de tarefas."
    )

    rel.p(
        "Por fim, a análise rigorosa de desempenho em memória distribuída exige "
        "atenção a um ponto que a Etapa 1 não precisou enfrentar com o mesmo peso. "
        "Conforme registrado na Aula 03, o tempo total de execução de um programa "
        "paralelo se decompõe em tempo de computação, tempo ocioso e tempo de "
        "comunicação. Separar essas três parcelas é o que permite afirmar se uma "
        "estratégia perdeu desempenho por distribuir mal o trabalho, por deixar "
        "processos esperando, ou por pagar caro na troca de mensagens. Por isso, "
        "além das métricas obrigatórias de speedup, eficiência e fator de "
        "balanceamento de carga, este relatório reporta também a granularidade e o "
        "custo de comunicação medidos diretamente na execução."
    )


def constroi_metodologia(rel, d):
    rel.h1("2. Metodologia")

    # ---------------------------------------------------------------- 2.1
    rel.h2("2.1 Ambiente de Execução")

    rel.p(
        "Todos os experimentos foram conduzidos em um notebook com sistema "
        f"operacional Arch Linux, kernel {d['kernel']}, arquitetura x86_64. O "
        f"compilador utilizado foi {d['compilador']}, e a implementação de MPI foi "
        f"{d['mpi_versao']}. A versão paralela foi compilada com mpicc, que invoca "
        "o compilador do sistema acrescentando as bibliotecas de MPI, e a versão "
        "sequencial de referência foi compilada diretamente com gcc. Ambas usaram "
        "as flags -O3 -std=c11, mantendo exatamente as mesmas condições de "
        "otimização adotadas na Etapa 1."
    )

    rel.p(
        f"O processador é um {d['cpu']} com arquitetura híbrida, um aspecto "
        "determinante para a interpretação dos resultados:"
    )
    rel.bullet(
        ", configurando uma combinação de núcleos de performance, os P-cores, que "
        "possuem Hyper-Threading, e núcleos de eficiência, os E-cores, que não "
        "possuem Hyper-Threading.",
        negrito_ate="10 núcleos físicos e 16 CPUs lógicas",
    )
    rel.bullet(
        "Caches L1d de 416 KiB, L1i de 448 KiB, L2 de 9,5 MiB e L3 de 24 MiB em "
        "instância única, com um único nó NUMA."
    )

    rel.p(
        "Essa heterogeneidade é relevante nesta etapa por um motivo específico. "
        "Como todos os processos MPI são executados na mesma máquina física, um "
        "processo alocado em um E-core executa a mesma quantidade de trabalho em "
        "mais tempo do que um processo alocado em um P-core. O fator de "
        "balanceamento de carga passa, então, a medir dois efeitos sobrepostos, o "
        "desbalanceamento geométrico do fractal e a assimetria do hardware."
    )

    rel.p(
        "Para controle da frequência, o governador foi fixado em performance "
        "durante toda a coleta final de dados, por meio do wrapper "
        "roda_com_performance_mpi.sh, que liga o modo performance antes dos "
        "experimentos e o restaura automaticamente ao final. Essa decisão repete o "
        "procedimento adotado na Etapa 1 e é justificada empiricamente. Em uma "
        "coleta preliminar conduzida com o governador em powersave, o tempo serial "
        "de referência no input padrão ficou em torno de 7,60 s, contra "
        f"{num(d['base_strong'], 2)} s na coleta final em performance, uma diferença "
        "de aproximadamente 37%. Medir a Etapa 2 sob um governador diferente do "
        "utilizado na Etapa 1 inviabilizaria a comparação entre os dois paradigmas, "
        "que é exigida pelo enunciado. Para impedir que essa contaminação volte a "
        "ocorrer, o script de experimentos recusa-se a executar quando detecta que "
        "o governador não está em performance."
    )

    # ---------------------------------------------------------------- 2.2
    rel.h2("2.2 Implementação Sequencial de Referência")

    rel.p(
        "A implementação sequencial base foi desenvolvida na linguagem C e é a "
        "mesma utilizada na Etapa 1, sem nenhuma alteração. Ela cumpre dois papéis, "
        "serve como linha de base T(n) para o cálculo das métricas de desempenho e "
        "serve como referência de corretude para a validação das versões paralelas. "
        "O algoritmo processa a matriz da imagem linha por linha utilizando laços "
        "aninhados simples, onde a função escape_time calcula o número de iterações "
        "necessárias para cada ponto do plano complexo."
    )

    rel.p(
        "A saída do algoritmo gera um arquivo binário contendo a matriz de "
        "contagens em inteiros de 32 bits, que é comparado byte a byte com o "
        "resultado da versão paralela, e um arquivo PGM para inspeção visual. "
        "Reutilizar a mesma implementação sequencial das duas etapas garante que "
        "qualquer diferença de desempenho observada seja atribuível ao paradigma de "
        "paralelização, e não a uma mudança no núcleo de cálculo."
    )

    # ---------------------------------------------------------------- 2.3
    rel.h2("2.3 Implementação Paralela com MPI")

    rel.p(
        "A versão paralela em MPI preserva integralmente a função escape_time e o "
        "mapeamento de pixel para plano complexo da versão sequencial, incluindo a "
        "ordem das operações em ponto flutuante. Isso é o que garante igualdade bit "
        "a bit entre as saídas, e isola a diferença de desempenho na forma como o "
        "trabalho é dividido e como o resultado é coletado."
    )

    rel.p("As funções de MPI utilizadas e a justificativa de cada escolha são as seguintes:")

    rel.bullet(
        " e MPI_Finalize, que delimitam a região paralela e inicializam o ambiente "
        "de execução.",
        negrito_ate="MPI_Init",
    )
    rel.bullet(
        " e MPI_Comm_size, que informam a cada processo o seu identificador e o "
        "número total de processos, permitindo que cada um calcule sozinho qual "
        "parte do domínio lhe cabe.",
        negrito_ate="MPI_Comm_rank",
    )
    rel.bullet(
        ", utilizada para a coleta do resultado nas estratégias estáticas. A escolha "
        "por Gatherv, e não por Gather, é deliberada. Quando a altura da imagem não "
        "é múltipla do número de processos, as faixas têm tamanhos diferentes, e "
        "Gather exige blocos de tamanho idêntico. Gatherv aceita um vetor de "
        "contagens e um vetor de deslocamentos, o que permite tratar o caso geral "
        "sem exigir que a resolução seja divisível pelo número de processos.",
        negrito_ate="MPI_Gatherv",
    )
    rel.bullet(
        " na raiz da estratégia bloco, que evita uma cópia intermediária. Como o "
        "rank 0 já calcula diretamente dentro da matriz final, não faz sentido "
        "enviar esses dados para ele mesmo.",
        negrito_ate="MPI_IN_PLACE",
    )
    rel.bullet(
        " e MPI_Recv, que implementam o diálogo entre o coordenador e os "
        "trabalhadores no esquema master-worker. A recepção no coordenador usa "
        "MPI_ANY_SOURCE, pois o coordenador não sabe de antemão qual trabalhador "
        "ficará livre primeiro, e é exatamente essa indeterminação que produz o "
        "balanceamento dinâmico.",
        negrito_ate="MPI_Send",
    )
    rel.bullet(
        ", usada para alinhar todos os processos imediatamente antes do início da "
        "medição de tempo. Sem essa barreira, processos que iniciam mais cedo "
        "contaminariam o cronômetro, e a Aula 03 lista explicitamente a "
        "sincronização dos processos no início do código como etapa necessária para "
        "obter tomadas de tempo confiáveis.",
        negrito_ate="MPI_Barrier",
    )
    rel.bullet(
        ", que fornece a medição de tempo de alta resolução recomendada para "
        "programas MPI.",
        negrito_ate="MPI_Wtime",
    )
    rel.bullet(
        ", utilizada ao final para recolher na raiz os tempos individuais de "
        "computação e de comunicação de cada processo, além do número de linhas "
        "processadas. Esses vetores são a base do diagnóstico de desbalanceamento, "
        "cumprindo nesta etapa o mesmo papel que os vetores por thread cumpriram na "
        "Etapa 1.",
        negrito_ate="MPI_Gather",
    )

    rel.p(
        "Três decisões de projeto merecem registro explícito. A primeira é que a "
        "unidade de trabalho é a linha da imagem, e não o pixel. Cada linha é "
        "indivisível e atribuída a um único processo, o que reduz o volume de "
        "mensagens e mantém os blocos transferidos contíguos em memória. A segunda é "
        "que a configuração não é distribuída por broadcast. Como o mpirun entrega o "
        "mesmo argv a todos os processos, cada um realiza o próprio parse dos "
        "argumentos, o que dispensa uma rodada de comunicação na inicialização. A "
        "terceira é que a estratégia de distribuição é escolhida em tempo de "
        "execução pela opção de linha de comando -e, exatamente como a Etapa 1 "
        "escolhia a política pela variável OMP_SCHEDULE. Assim, o mesmo binário "
        "serve a todos os cenários, e nenhuma diferença de compilação pode "
        "contaminar a comparação entre estratégias."
    )

    rel.p(
        "No esquema master-worker há ainda uma otimização de protocolo que vale "
        "descrever. Cada mensagem enviada por um trabalhador ao coordenador carrega "
        "um cabeçalho com a linha inicial e a quantidade de linhas, seguido dos "
        "dados calculados. O primeiro contato de cada trabalhador vai com contagem "
        "zero, sinalizando apenas um pedido de trabalho. Dessa forma, o resultado de "
        "uma tarefa e o pedido da tarefa seguinte viajam na mesma mensagem, o que "
        "reduz pela metade o número de mensagens em relação a um protocolo que "
        "separasse entrega e requisição."
    )
