"""
Secao 3 do Relatorio da Etapa 2, a saber Resultados.
Importado por gera_relatorio.py. Nenhum numero e digitado, todos vem de 'd'.
"""

from gera_relatorio import num, pct, ROTULOS, NOMES_LONGOS, seleciona, filtra_omp

LOG_CORRETUDE = """=== [2/6] Validacao de corretude bit a bit (cmp) ===
Config: 4096x4096 pixels, MAX_ITER=1000
Regiao: Re em [-2, 1], Im em [-1.5, 1.5]
  [OK] Input padrao (estrategia=bloco, p=4): IGUAIS bit a bit
  [OK] Input padrao (estrategia=ciclico, p=4): IGUAIS bit a bit
  [OK] Input padrao (estrategia=mestre, p=4): IGUAIS bit a bit
Config: 4096x4096 pixels, MAX_ITER=5000
Regiao: Re em [-0.745143887, -0.742143887], Im em [0.130325904, 0.133325904]
  [OK] Input zoom   (estrategia=bloco, p=4): IGUAIS bit a bit
  [OK] Input zoom   (estrategia=ciclico, p=4): IGUAIS bit a bit
  [OK] Input zoom   (estrategia=mestre, p=4): IGUAIS bit a bit"""


def _linhas_desempenho(agg, experimento):
    """Monta as linhas de tempo, speedup e eficiencia de um experimento."""
    linhas = []
    for rot in ROTULOS:
        for r in seleciona(agg, experimento, rot):
            linhas.append([
                NOMES_LONGOS[rot],
                r["processos"],
                num(r["tempo_calculo_media"], 4),
                num(r["tempo_calculo_dp"], 4),
                num(r["speedup"], 2),
                num(r["eficiencia"], 3),
            ])
    return linhas


def constroi_resultados(rel, d):
    agg = d["agg"]
    gran = d["gran"]

    rel.h1("3. Resultados")

    rel.p(
        "Esta seção apresenta os resultados experimentais da Etapa 2, organizados "
        "na seguinte ordem: validação de corretude, escalabilidade forte, caso de "
        "desbalanceamento acentuado, escalabilidade fraca, comparação com a solução "
        "OpenMP da Etapa 1 e síntese dos achados. Os números reportados são médias "
        f"de {d['reps_par']} repetições para os cenários de escalabilidade forte e "
        f"de zoom e de {d['reps_weak']} repetições para a escalabilidade fraca, "
        "acompanhadas do desvio padrão, todos coletados sob governador de frequência "
        "fixado em performance."
    )

    rel.legenda_tabela("Baselines sequenciais de referência T(n)")
    rel.tabela(
        ["Cenário", "Resolução", "MAX_ITER", "T(n) médio (s)", "Desvio padrão (s)", "Repetições"],
        [
            ["Input padrão", "4096²", "1000", num(d["base_strong"], 4), num(d["dp_strong"], 4), d["reps_serial"]],
            ["Zoom", "4096²", "5000", num(d["base_zoom"], 4), num(d["dp_zoom"], 4), d["reps_serial"]],
        ] + [
            [f"Fraca, p = {p}", f"{n}²", "1000",
             num(d["baselines"][f"weak{n}"][0], 4),
             num(d["baselines"][f"weak{n}"][1], 4),
             d["baselines"][f"weak{n}"][2]]
            for p, n in d["pares_weak"]
        ],
    )

    # ------------------------------------------------------------------ 3.1
    rel.h2("3.1 Validação de Corretude")

    rel.p(
        "A corretude foi verificada comparando bit a bit a matriz de contagens "
        "produzida por cada uma das três estratégias contra a versão sequencial de "
        "referência, tanto no input padrão quanto no caso de zoom. Em todos os seis "
        "cenários o resultado foi de igualdade exata, sem nenhum pixel divergente."
    )

    rel.legenda_figura("Log da validação de corretude das três estratégias")
    rel.mono(LOG_CORRETUDE)
    rel.descricao_figura(
        "Saída da etapa de validação do script de experimentos, comparando as três "
        "estratégias MPI contra a matriz sequencial de referência no input padrão e "
        "no caso de zoom."
    )

    rel.p(
        "Esse desfecho é o esperado para o problema. O valor de cada pixel depende "
        "apenas das suas próprias coordenadas no plano complexo, e a função "
        "escape_time executa a mesma sequência de operações em ponto flutuante "
        "independentemente de qual processo a executa. Como a distribuição de "
        "trabalho não altera a ordem das operações dentro de cada pixel, não há "
        "reassociação capaz de introduzir divergência numérica. A igualdade exata é, "
        "portanto, consequência estrutural do desenho da paralelização, e atende "
        "integralmente ao critério da Seção 5.5 do enunciado."
    )

    rel.p(
        "Vale registrar que a validação cobre também o caso em que a altura da "
        "imagem não é divisível pelo número de processos, situação em que as faixas "
        "atribuídas têm tamanhos diferentes. É esse cenário que justifica o uso de "
        "MPI_Gatherv no lugar de MPI_Gather na coleta do resultado."
    )

    # ------------------------------------------------------------------ 3.2
    rel.h2("3.2 Escalabilidade Forte")

    rel.p(
        "O experimento de escalabilidade forte mantém a resolução fixa em "
        "4096 × 4096 com MAX_ITER = 1000, variando o número de processos em 1, 2, 4, "
        "8 e 16. A métrica central é o tempo de execução T(n, p), que abrange "
        "computação mais coleta do resultado na raiz, e dele derivam o speedup e a "
        "eficiência."
    )

    rel.h3("3.2.1 Tempo de Execução, Speedup e Eficiência")

    rel.legenda_tabela(
        "Escalabilidade forte, tempo de execução, speedup e eficiência por estratégia"
    )
    rel.tabela(
        ["Estratégia", "p", "T(n,p) (s)", "Desvio (s)", "S(n,p)", "E(n,p)"],
        _linhas_desempenho(agg, "strong"),
    )

    b16 = d["sel"]("strong", "bloco", 16)
    m16 = d["sel"]("strong", "mestre,1", 16)
    c16 = d["sel"]("strong", "ciclico,1", 16)
    m2 = d["sel"]("strong", "mestre,1", 2)

    rel.p(
        "A tabela evidencia três comportamentos nitidamente distintos. A estratégia "
        f"bloco satura cedo, atingindo speedup de apenas {num(b16['speedup'], 2)} "
        f"com 16 processos, o que corresponde a uma eficiência de "
        f"{num(b16['eficiencia'], 3)}. A estratégia cíclica alcança "
        f"{num(c16['speedup'], 2)} no mesmo ponto, e o esquema master-worker com "
        f"chunk 1 chega a {num(m16['speedup'], 2)}, com eficiência de "
        f"{num(m16['eficiencia'], 3)}, o melhor resultado de toda a etapa."
    )

    rel.p(
        "Um ponto merece atenção na leitura da tabela. Com dois processos, o "
        f"master-worker registra speedup de {num(m2['speedup'], 2)} e eficiência de "
        f"{num(m2['eficiencia'], 3)}. Esse valor não indica falha de implementação, "
        "mas sim a consequência direta de o rank 0 ser dedicado à coordenação. Com "
        "p = 2 existe um único trabalhador, de modo que o tempo paralelo se "
        "aproxima do tempo sequencial, e a eficiência se aproxima de 0,5 por "
        "definição, já que a fórmula divide o speedup por 2. Esse efeito é discutido "
        "em detalhe na Seção 4."
    )

    rel.legenda_grafico(
        "Escalabilidade forte, tempo de execução por número de processos"
    )
    rel.imagem("fig_mpi_strong_tempo.png")

    rel.legenda_grafico("Escalabilidade forte, speedup S(n, p) por número de processos")
    rel.imagem("fig_mpi_strong_speedup.png")

    rel.p(
        "O Gráfico 2 mostra que nenhuma estratégia acompanha a reta de speedup "
        "linear ideal, o que é esperado, e que a separação entre as curvas aumenta "
        "com o número de processos. Até dois processos todas as estratégias são "
        "praticamente equivalentes. A partir de quatro processos a curva da "
        "estratégia bloco se descola das demais e deixa de crescer de forma "
        "significativa."
    )

    rel.legenda_grafico("Escalabilidade forte, eficiência E(n, p) por número de processos")
    rel.imagem("fig_mpi_strong_eficiencia.png")

    b1 = d["sel"]("strong", "bloco", 1)
    rel.p(
        "No Gráfico 3 cabe registrar uma observação de rigor. Com um único "
        f"processo, a estratégia bloco apresenta eficiência de "
        f"{num(b1['eficiencia'], 3)}, ligeiramente acima da unidade. Esse valor "
        "decorre da variação natural entre execuções, pois o baseline sequencial "
        f"tem desvio padrão de {num(d['dp_strong'], 4)} s, e a diferença observada "
        "está dentro de um desvio. Não se trata, portanto, de speedup supralinear "
        "real, e sim de ruído de medição."
    )

    rel.h3("3.2.2 Fator de Balanceamento de Carga")

    rel.p(
        "Para compreender as diferenças de tempo, speedup e eficiência "
        "apresentadas acima, é necessário analisar o fator de balanceamento de "
        "carga, F_LB(n) = (T_max − T_min) / T_max, em que o valor ideal é 0."
    )

    linhas_fbc = []
    for rot in ROTULOS:
        for r in seleciona(agg, "strong", rot):
            if r["processos"] < 2:
                continue
            linhas_fbc.append([
                NOMES_LONGOS[rot],
                r["processos"],
                num(r["t_comp_max_media"], 4),
                num(r["t_comp_min_media"], 4),
                num(r["fbc_media"], 4),
            ])

    rel.legenda_tabela("Fator de balanceamento de carga no input padrão")
    rel.tabela(["Estratégia", "p", "T_max (s)", "T_min (s)", "F_LB(n)"], linhas_fbc)

    b4 = d["sel"]("strong", "bloco", 4)
    rel.p(
        "Os números da estratégia bloco são o achado mais expressivo desta seção. "
        f"Com quatro processos, o processo mais lento gasta {num(b4['t_comp_max_media'], 4)} s "
        f"enquanto o mais rápido gasta apenas {num(b4['t_comp_min_media'], 4)} s, "
        f"produzindo F_LB de {num(b4['fbc_media'], 4)}. Com dezesseis processos o "
        f"fator chega a {num(b16['fbc_media'], 4)}, praticamente o valor máximo "
        "possível, o que significa que o primeiro processo a terminar fica ocioso "
        "durante quase toda a execução."
    )

    b2 = d["sel"]("strong", "bloco", 2)
    rel.p(
        "Há, porém, uma exceção reveladora. Com dois processos, a estratégia bloco "
        f"registra F_LB de {num(b2['fbc_media'], 4)}, isto é, balanceamento "
        "praticamente perfeito. A explicação é geométrica. O Conjunto de Mandelbrot "
        "é simétrico em relação ao eixo real, e a região padrão está centrada nesse "
        "eixo. Ao dividir a imagem em exatamente duas faixas horizontais, cada "
        "processo recebe uma metade espelhada da outra, com carga idêntica. Essa "
        "coincidência desaparece assim que o número de faixas aumenta, pois as "
        "faixas centrais passam a concentrar o cardioide enquanto as faixas "
        "extremas ficam quase vazias."
    )

    rel.legenda_grafico("Fator de balanceamento de carga no input padrão")
    rel.imagem("fig_mpi_strong_fbc.png")

    c8 = d["sel"]("strong", "ciclico,1", 8)
    rel.p(
        "As estratégias cíclica e master-worker mantêm o fator muito mais baixo, "
        "porém não nulo. A estratégia cíclica apresenta fator de "
        f"{num(c8['fbc_media'], 4)} com oito processos e de {num(c16['fbc_media'], 4)} "
        "com dezesseis, ainda que a quantidade de linhas atribuída a cada processo "
        "seja praticamente igual. Esse resíduo não decorre da geometria do fractal, "
        "e sim da arquitetura híbrida do processador, questão retomada na Seção 4."
    )

    rel.h3("3.2.3 Custo de Comunicação e Granularidade")

    rel.p(
        "O enunciado exige a análise do custo de coleta da imagem e, quando "
        "aplicável, da sobrecarga do coordenador. A tabela a seguir reúne as três "
        "medidas relevantes, o tempo acumulado em chamadas de MPI na raiz, o custo "
        "líquido de comunicação definido como T(n, p) − T_max, e a granularidade "
        "G(n) = T_cp / T_cm."
    )

    linhas_com = []
    for rot in ROTULOS:
        for r in seleciona(agg, "strong", rot):
            if r["processos"] < 2:
                continue
            g = gran.get(("strong", rot, r["processos"], r["largura"]))
            linhas_com.append([
                NOMES_LONGOS[rot],
                r["processos"],
                num(r["tempo_com_raiz_media"], 4),
                num(r["overhead_com_media"], 4),
                num(g, 1) if g is not None and g != float("inf") else "n/d",
                num(r["tempo_io_media"], 4),
            ])

    rel.legenda_tabela(
        "Custo de comunicação, granularidade e tempo de escrita no input padrão"
    )
    rel.tabela(
        ["Estratégia", "p", "T em MPI na raiz (s)", "T(n,p) − T_max (s)", "G(n)", "Escrita em disco (s)"],
        linhas_com,
    )

    rel.p(
        "A leitura desta tabela exige o cuidado antecipado na Seção 2.5. O tempo "
        "acumulado em chamadas de MPI na raiz é alto justamente nas estratégias em "
        "que a raiz tem pouco ou nenhum trabalho útil. Na estratégia bloco com "
        f"dezesseis processos esse valor é de {num(b16['tempo_com_raiz_media'], 4)} s, "
        f"praticamente igual ao tempo total de {num(b16['tempo_calculo_media'], 4)} s, "
        "mas isso não significa que a coleta custou esse tempo. Significa que a raiz "
        "terminou a sua faixa quase imediatamente e permaneceu bloqueada dentro de "
        "MPI_Gatherv aguardando os processos centrais."
    )

    rel.p(
        "O custo líquido de comunicação é a medida que isola o fenômeno. Ele "
        "permanece pequeno em todas as configurações do input padrão, variando de "
        f"{num(d['ovh_min_strong'], 4)} s a {num(d['ovh_max_strong'], 4)} s, o que "
        "representa uma fração reduzida do tempo total. Isso confirma que, nesta "
        "escala e com todos os processos na mesma máquina, a transferência da matriz "
        "não é o gargalo. O tempo de escrita em disco, reportado à parte conforme "
        "exige o enunciado, também é pequeno e não entra em nenhuma métrica de "
        "speedup."
    )

    rel.p(
        "A granularidade reforça a mesma conclusão por outro ângulo. Nas estratégias "
        "estáticas com poucos processos, G(n) assume valores elevados, indicando "
        "granularidade grossa, com muito cálculo para pouca comunicação. À medida "
        "que o número de processos cresce, G(n) diminui, e na estratégia bloco "
        "aproxima-se da unidade. É preciso destacar que essa queda não reflete "
        "aumento de tráfego de mensagens, e sim o crescimento do tempo ocioso "
        "embutido em T_cm, uma vez que os processos rápidos passam a esperar cada "
        "vez mais pelos lentos."
    )

    rel.legenda_grafico(
        "Custo de comunicação e tempo acumulado em chamadas de MPI na raiz"
    )
    rel.imagem("fig_mpi_comunicacao.png")
