"""
Secao 4 do Relatorio da Etapa 2, a saber Discussao.
Importado por gera_relatorio.py. Nenhum numero e digitado, todos vem de 'd'.
"""

from gera_relatorio import num, NOMES_LONGOS


def constroi_discussao(rel, d):
    rel.h1("4. Discussão")

    rel.p(
        "Esta seção interpreta os resultados da Seção 3 à luz dos conceitos "
        "teóricos da Introdução e das decisões metodológicas registradas na Seção 2. "
        "A discussão está organizada em torno de nove eixos: a corretude, a "
        "comparação entre a versão sequencial e as paralelas, a resposta de cada "
        "estratégia ao desbalanceamento, o custo estrutural do coordenador, o custo "
        "de comunicação e a granularidade, os limites de Amdahl e da arquitetura, a "
        "escalabilidade fraca e Gustafson, a comparação com OpenMP e, por fim, os "
        "demais gargalos e as sugestões de melhoria."
    )

    # ------------------------------------------------------------------ 4.1
    rel.h2("4.1 Análise da Corretude")

    rel.p(
        "A corretude foi validada por comparação bit a bit entre a matriz de "
        "contagens produzida por cada estratégia e a da versão sequencial de "
        "referência, nos dois inputs. Em todos os seis cenários o resultado foi de "
        "igualdade exata, sem nenhum pixel divergente."
    )

    rel.p(
        "Esse desfecho é consequência estrutural do desenho da paralelização. O "
        "Mandelbrot por escape-time é embaraçosamente paralelo, cada pixel é "
        "computado de forma independente, e a função escape_time executa exatamente "
        "a mesma sequência de operações em ponto flutuante qualquer que seja o "
        "processo que a execute. Como a atribuição de trabalho não altera a ordem "
        "das operações dentro de cada pixel, não há reassociação capaz de produzir "
        "divergência de fronteira."
    )

    rel.p(
        "Em memória distribuída há um risco adicional que não existia na Etapa 1 e "
        "que merece registro. Além de calcular corretamente, é preciso remontar a "
        "matriz na ordem certa, pois cada processo devolve apenas um subconjunto das "
        "linhas. Na estratégia cíclica, as linhas de um mesmo processo não são "
        "contíguas na imagem final, o que exige uma etapa explícita de reordenação "
        "na raiz. Um erro nessa remontagem não produziria valores numericamente "
        "errados, e sim uma imagem com linhas embaralhadas, que passaria despercebida "
        "em uma inspeção superficial do tempo de execução. A validação bit a bit "
        "cobre também esse risco, e o fato de a estratégia cíclica produzir saída "
        "idêntica confirma que o mapeamento de índices está correto."
    )

    # ------------------------------------------------------------------ 4.2
    rel.h2("4.2 Comparação Entre a Versão Sequencial e as Versões Paralelas")

    m16 = d["sel"]("strong", "mestre,1", 16)
    b16 = d["sel"]("strong", "bloco", 16)

    rel.p(
        f"Com dezesseis processos e o baseline sequencial de "
        f"{num(d['base_strong'], 3)} s no input padrão, os resultados variam de um "
        f"speedup de {num(b16['speedup'], 2)} na decomposição contígua até "
        f"{num(m16['speedup'], 2)} no esquema master-worker com chunk 1. Em outras "
        "palavras, para o mesmo problema, o mesmo hardware e o mesmo núcleo de "
        "cálculo, a escolha da estratégia de distribuição mais do que triplica o "
        "ganho obtido."
    )

    rel.p(
        "Esse contraste é a lição central da etapa e reforça o que a Etapa 1 já "
        "havia indicado em memória compartilhada. Paralelizar, por si só, não "
        "garante desempenho. Como as versões paralelas são estruturalmente idênticas "
        "à sequencial no núcleo de cálculo, toda a diferença observada decorre "
        "exclusivamente da forma como o trabalho foi dividido e de como o resultado "
        "foi coletado."
    )

    # ------------------------------------------------------------------ 4.3
    rel.h2("4.3 Por Que o Problema é Desbalanceado e a Resposta de Cada Estratégia")

    rel.p(
        "O tempo necessário para processar cada ponto é proporcional ao número de "
        "iterações do laço de escape. A vasta maioria dos pixels situados em regiões "
        "afastadas do fractal escapa rapidamente do raio pré-definido, exigindo "
        "pouco processamento, enquanto os pixels no interior ou na fronteira do "
        "conjunto demandam as 1000 iterações completas no input padrão, e até 5000 "
        "iterações no caso de zoom. Como essa disparidade é geograficamente "
        "concentrada, qualquer divisão que respeite a vizinhança espacial herda a "
        "concentração."
    )

    b2 = d["sel"]("strong", "bloco", 2)
    b4 = d["sel"]("strong", "bloco", 4)

    rel.p(
        "A estratégia bloco é a tradução direta dessa armadilha. Ao atribuir faixas "
        "contíguas de linhas, os processos que recebem a região central herdam o "
        "cardioide principal, ao passo que os processos das extremidades recebem "
        f"regiões quase vazias. Com quatro processos o fator de balanceamento salta "
        f"para {num(b4['fbc_media'], 4)}, e com dezesseis chega a "
        f"{num(b16['fbc_media'], 4)}. O processo mais rápido conclui a sua faixa em "
        f"{num(b16['t_comp_min_media'], 4)} s, enquanto o mais lento gasta "
        f"{num(b16['t_comp_max_media'], 4)} s, e permanece ocioso durante "
        "praticamente toda a execução."
    )

    rel.p(
        "O caso de dois processos merece atenção especial, porque é um resultado "
        "que poderia ser lido erroneamente como evidência de que a decomposição "
        f"contígua funciona bem. Com p = 2 o fator é de apenas {num(b2['fbc_media'], 4)}, "
        "praticamente ideal. Esse valor, contudo, não decorre de mérito da "
        "estratégia, e sim da simetria do Conjunto de Mandelbrot em relação ao eixo "
        "real combinada com o fato de a região padrão estar centrada nesse eixo. "
        "Ao dividir a imagem em duas faixas horizontais, cada processo recebe uma "
        "metade espelhada da outra. A coincidência é destruída assim que o número de "
        "faixas aumenta, e desaparece por completo no caso de zoom, em que a região "
        f"ampliada não é simétrica e o fator com dois processos já é de "
        f"{num(d['sel']('zoom', 'bloco', 2)['fbc_media'], 4)}."
    )

    rel.p(
        "As demais estratégias atacam o problema por caminhos distintos, com "
        "resultados que convém comparar diretamente:"
    )

    c16 = d["sel"]("strong", "ciclico,16", 16)
    c1_16 = d["sel"]("strong", "ciclico,1", 16)

    rel.bullet(
        " ao distribuir blocos de linhas em round-robin, a estratégia quebra a "
        "contiguidade espacial e faz com que cada processo receba amostras de todas "
        "as regiões da imagem, tanto das caras quanto das baratas. O resultado é uma "
        f"queda expressiva do fator, que com dezesseis processos fica em "
        f"{num(c1_16['fbc_media'], 4)} com chunk 1 e em {num(c16['fbc_media'], 4)} "
        "com chunk 16, contra um valor próximo da unidade na decomposição contígua. "
        "Tudo isso sem nenhuma negociação em tempo de execução, pois a atribuição "
        "continua sendo calculada por fórmula, com custo de escalonamento nulo.",
        negrito_ate="Distribuição cíclica:",
    )
    m16_c16 = d["sel"]("strong", "mestre,16", 16)
    rel.bullet(
        " ao entregar tarefas sob demanda, o esquema adapta a distribuição ao custo "
        "real de cada bloco, em vez de supor que a amostragem cíclica será "
        f"suficiente. Com dezesseis processos o fator cai para "
        f"{num(m16['fbc_media'], 4)} com chunk 1 e para "
        f"{num(m16_c16['fbc_media'], 4)} com chunk 16, os dois menores valores "
        "entre todas as configurações com esse número de processos no input padrão. "
        "O preço é o tráfego de mensagens proporcional ao número de tarefas e a "
        "dedicação integral de um processo à coordenação.",
        negrito_ate="Master-worker:",
    )

    rel.p(
        "Chama atenção que, no input padrão, a diferença entre chunk 1 e chunk 16 "
        "seja pequena nas duas estratégias dinâmicas. Isso difere do observado na "
        "Etapa 1, em que a granularidade fina foi decisiva. A explicação está no "
        "custo relativo. Em memória compartilhada, reduzir o chunk custa apenas "
        "sincronização em uma fila local. Em memória distribuída, reduzir o chunk "
        "multiplica o número de mensagens, e esse custo compensa parte do ganho de "
        "balanceamento. O resultado é que, em MPI, o ponto ótimo de granularidade é "
        "mais grosso do que em OpenMP."
    )

    # ------------------------------------------------------------------ 4.4
    rel.h2("4.4 O Custo Estrutural do Coordenador no Master-Worker")

    m2 = d["sel"]("strong", "mestre,1", 2)
    m4 = d["sel"]("strong", "mestre,1", 4)
    zm2 = d["sel"]("zoom", "mestre,1", 2)

    rel.p(
        "O esquema master-worker implementado dedica o rank 0 exclusivamente à "
        "coordenação, de modo que com p processos apenas p − 1 produzem trabalho "
        "útil. Essa decisão tem uma consequência direta sobre as métricas que "
        "precisa ser explicitada, sob pena de os números serem mal interpretados."
    )

    rel.p(
        "A fórmula de eficiência da Aula 03 divide o speedup pelo número de "
        "processos p, e não pelo número de processos que calculam. Com dois "
        f"processos, o master-worker registra eficiência de {num(m2['eficiencia'], 3)} "
        "no input padrão, um valor que parece indicar falha grave, mas que é "
        "simplesmente o teto estrutural da configuração. Com um único trabalhador, o "
        "tempo paralelo não pode ser inferior ao sequencial, e o speedup máximo "
        "alcançável é 1, o que produz eficiência de 0,5 por definição."
    )

    rel.p(
        f"No caso de zoom a situação é ainda mais clara, pois o speedup com dois "
        f"processos é de {num(zm2['speedup'], 2)}, abaixo da unidade. Trata-se "
        "exatamente da situação de slowdown descrita na Aula 03, em que a sobrecarga "
        "da paralelização supera o ganho. O único trabalhador executa todo o "
        "trabalho sequencial e ainda paga o custo de empacotar cada bloco de linhas "
        "e transmiti-lo ao coordenador."
    )

    m8 = d["sel"]("strong", "mestre,1", 8)
    rel.p(
        f"A penalidade se dilui rapidamente conforme p cresce, pois a fração de "
        f"processos desperdiçada é 1/p. Com quatro processos a eficiência já sobe "
        f"para {num(m4['eficiencia'], 3)}, atinge o seu máximo de "
        f"{num(m8['eficiencia'], 3)} com oito processos e recua levemente para "
        f"{num(m16['eficiencia'], 3)} com dezesseis, ponto em que ainda assim se "
        f"registra o maior speedup de toda a etapa, de {num(m16['speedup'], 2)}. "
        "Ou seja, o investimento de um processo em coordenação só compensa quando "
        "há trabalhadores suficientes para que o balanceamento dinâmico recupere "
        "mais do que o processo sacrificado custou. Neste experimento, o ponto de "
        "virada situa-se entre dois e quatro processos, e o recuo final da "
        "eficiência reflete os limites arquiteturais discutidos na Seção 4.6."
    )

    rel.p(
        "Uma alternativa de projeto seria fazer o coordenador também calcular nos "
        "intervalos entre atendimentos, o que eliminaria o desperdício. Essa "
        "variante não foi implementada porque exigiria recepção não bloqueante para "
        "evitar que um trabalhador ficasse esperando enquanto o coordenador "
        "calculasse, o que aumentaria a complexidade sem alterar a conclusão "
        "principal sobre balanceamento. Ela fica registrada entre as sugestões de "
        "melhoria."
    )

    # ------------------------------------------------------------------ 4.5
    rel.h2("4.5 Custo de Comunicação e Granularidade")

    rel.p(
        "A separação entre tempo de comunicação e tempo ocioso, antecipada na Seção "
        "2.5, é o que permite responder com precisão se a troca de mensagens foi ou "
        "não um gargalo nesta etapa. A resposta é que não foi."
    )

    rel.p(
        "O tempo acumulado em chamadas de MPI na raiz é elevado justamente nas "
        "configurações em que a raiz tem pouco trabalho útil, e isso é um artefato "
        "de medição, não um custo real de transferência. Na estratégia bloco com "
        f"dezesseis processos, esse tempo é de {num(b16['tempo_com_raiz_media'], 4)} s "
        f"sobre um tempo total de {num(b16['tempo_calculo_media'], 4)} s. A raiz "
        "recebe a primeira faixa da imagem, que é quase vazia, conclui o seu cálculo "
        "quase imediatamente e permanece bloqueada dentro de MPI_Gatherv até que os "
        "processos centrais terminem. O que esse número mede é ociosidade imposta "
        "pelo desbalanceamento, e não largura de banda."
    )

    rel.p(
        "O custo líquido de comunicação, definido como T(n, p) − T_max, isola o "
        "fenômeno porque desconta o trabalho útil do processo mais lento. No input "
        f"padrão esse custo permanece entre {num(d['ovh_min_strong'], 4)} s e "
        f"{num(d['ovh_max_strong'], 4)} s em todas as configurações, o que "
        "representa uma fração pequena do tempo total mesmo nas execuções mais "
        "rápidas. A conclusão é que, nesta escala e com todos os processos "
        "executando na mesma máquina física, a transferência da matriz pela memória "
        "do sistema é barata, e o gargalo dominante é a distribuição do trabalho."
    )

    rel.p(
        "A granularidade G(n) = T_cp / T_cm confirma a mesma leitura e, ao mesmo "
        "tempo, ilustra por que a métrica precisa ser interpretada com cuidado "
        "neste problema. Nas estratégias estáticas com poucos processos, G(n) "
        "assume valores de várias dezenas ou centenas, indicando granularidade "
        "grossa, com muito cálculo para pouca comunicação, exatamente o regime "
        "desejável. Conforme p cresce, G(n) diminui, e na estratégia bloco "
        "aproxima-se da unidade. Como o denominador T_cm agrega comunicação e "
        "espera, essa queda não indica aumento de tráfego, e sim que o tempo ocioso "
        "passou a rivalizar com o tempo de cálculo. A granularidade, nesse caso, "
        "está medindo o colapso do balanceamento por via indireta."
    )

    rel.p(
        "Cabe ainda registrar o efeito das estratégias sobre o custo de coleta. A "
        "estratégia bloco permite que a raiz escreva diretamente na matriz final, "
        "usando MPI_IN_PLACE, sem cópia intermediária. A estratégia cíclica, por "
        "distribuir linhas não contíguas, exige um buffer intermediário e uma etapa "
        "de reordenação na raiz, custo que foi deliberadamente contabilizado dentro "
        "do tempo de comunicação para não favorecer artificialmente essa "
        "estratégia. O master-worker dispensa a coleta coletiva, pois cada bloco já "
        "chega acompanhado da sua posição de destino e é copiado diretamente para o "
        "lugar certo."
    )
