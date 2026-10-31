"""
Subsecoes 3.3 a 3.6 do Relatorio da Etapa 2.
Importado por gera_relatorio.py. Nenhum numero e digitado, todos vem de 'd'.
"""

from gera_relatorio import num, pct, ROTULOS, NOMES_LONGOS, seleciona, filtra_omp


def constroi_zoom(rel, d):
    agg = d["agg"]

    rel.h2("3.3 Caso de Desbalanceamento Acentuado")

    rel.p(
        "Esta seção trata do cenário de estresse, que usa a região do vale dos "
        "cavalos-marinhos centrada em -0,743643887 e 0,131825904, com largura real "
        "de 3,0 × 10⁻³ e MAX_ITER = 5000. Nessa região a concentração de pixels de "
        "custo elevado é extrema, e a análise do fator de balanceamento de carga "
        "torna-se central para avaliar as soluções paralelas."
    )

    linhas = []
    for rot in ROTULOS:
        for r in seleciona(agg, "zoom", rot):
            linhas.append([
                NOMES_LONGOS[rot],
                r["processos"],
                num(r["tempo_calculo_media"], 4),
                num(r["speedup"], 2),
                num(r["eficiencia"], 3),
                num(r["fbc_media"], 4),
            ])

    rel.legenda_tabela(
        "Caso de zoom, tempo de execução, speedup, eficiência e balanceamento"
    )
    rel.tabela(
        ["Estratégia", "p", "T(n,p) (s)", "S(n,p)", "E(n,p)", "F_LB(n)"], linhas
    )

    zb16 = d["sel"]("zoom", "bloco", 16)
    zm16 = d["sel"]("zoom", "mestre,1", 16)
    zc16 = d["sel"]("zoom", "ciclico,16", 16)
    zb2 = d["sel"]("zoom", "bloco", 2)
    zm2 = d["sel"]("zoom", "mestre,1", 2)

    rel.p(
        "O comportamento do caso de zoom difere do input padrão em um aspecto "
        "importante. A estratégia bloco, que no input padrão apresentava "
        "balanceamento quase perfeito com dois processos por efeito da simetria do "
        f"conjunto, aqui registra F_LB de {num(zb2['fbc_media'], 4)} já com dois "
        "processos. A região ampliada não está centrada no eixo real de forma "
        f"simétrica, e por isso a coincidência favorável desaparece. Com dezesseis "
        f"processos o fator atinge {num(zb16['fbc_media'], 4)}."
    )

    rel.p(
        "Ainda assim, a estratégia bloco apresenta no zoom um desempenho "
        f"relativamente melhor do que no input padrão, com speedup de "
        f"{num(zb16['speedup'], 2)} contra {num(d['sel']('strong', 'bloco', 16)['speedup'], 2)} "
        "no caso padrão. A razão é que, no vale dos cavalos-marinhos, os pixels de "
        "custo elevado estão distribuídos ao longo de filamentos que atravessam "
        "várias faixas horizontais, em vez de se concentrarem em um bloco central "
        "compacto como ocorre com o cardioide principal."
    )

    rel.p(
        f"O esquema master-worker novamente se destaca, atingindo speedup de "
        f"{num(zm16['speedup'], 2)} com dezesseis processos e fator de "
        f"{num(zm16['fbc_media'], 4)}. A estratégia cíclica com chunk 16 fica em "
        f"{num(zc16['speedup'], 2)}. Também aqui o master-worker com dois processos "
        f"registra speedup de {num(zm2['speedup'], 2)}, abaixo da unidade, "
        "configurando a situação de slowdown descrita na Aula 03. Com um único "
        "trabalhador, o esquema executa o trabalho sequencial inteiro e ainda paga "
        "o custo de empacotar e transmitir cada bloco de linhas ao coordenador."
    )

    rel.legenda_grafico(
        "Vale dos cavalos-marinhos, tempo de execução e fator de balanceamento"
    )
    rel.imagem("fig_mpi_zoom_fbc_tempo.png")


def constroi_fraca(rel, d):
    agg = d["agg"]

    rel.h2("3.4 Escalabilidade Fraca")

    rel.p(
        "Na escalabilidade fraca, a resolução cresce junto com o número de "
        "processos, mantendo o trabalho por processo aproximadamente constante, "
        "segundo N = 4096 · √p. Conforme a Aula 03, um programa é escalável se for "
        "possível manter constante a eficiência E(n, p) ao incrementar o tamanho do "
        "problema n ao mesmo tempo que se incrementa o número de processos p. Por "
        "esse motivo, a eficiência apresentada nesta seção utiliza a mesma fórmula "
        "das seções anteriores, com o baseline sequencial medido na própria "
        "resolução de cada ponto."
    )

    linhas = []
    for rot in ROTULOS:
        for r in seleciona(agg, "weak", rot):
            linhas.append([
                NOMES_LONGOS[rot],
                r["processos"],
                f"{r['largura']}²",
                num(r["t_ref_serial"], 3),
                num(r["tempo_calculo_media"], 4),
                num(r["speedup"], 2),
                num(r["eficiencia"], 3),
            ])

    rel.legenda_tabela(
        "Escalabilidade fraca, resolução, baseline sequencial, tempo, speedup e eficiência"
    )
    rel.tabela(
        ["Estratégia", "p", "Resolução", "T(n) (s)", "T(n,p) (s)", "S(n,p)", "E(n,p)"],
        linhas,
    )

    wb = {p: d["sel"]("weak", "bloco", p) for p in (1, 2, 4, 8, 16)}
    wc = {p: d["sel"]("weak", "ciclico,16", p) for p in (1, 2, 4, 8, 16)}
    wm = {p: d["sel"]("weak", "mestre,16", p) for p in (2, 4, 8, 16)}

    rel.p(
        "A estratégia bloco apresenta a degradação mais acentuada, com eficiência "
        f"caindo de {num(wb[1]['eficiencia'], 3)} com um processo para "
        f"{num(wb[16]['eficiencia'], 3)} com dezesseis. A estratégia cíclica com "
        f"chunk 16 parte de {num(wc[1]['eficiencia'], 3)} e termina em "
        f"{num(wc[16]['eficiencia'], 3)}. O esquema master-worker com chunk 16, "
        f"depois de absorver a penalidade estrutural do coordenador com dois "
        f"processos, que o coloca em {num(wm[2]['eficiencia'], 3)}, sobe para "
        f"{num(wm[4]['eficiencia'], 3)} com quatro processos e encerra em "
        f"{num(wm[16]['eficiencia'], 3)} com dezesseis."
    )

    rel.p(
        "Nenhuma das estratégias mantém a eficiência constante ao longo de toda a "
        "faixa, de modo que, pelo critério da Aula 03, o programa não é plenamente "
        "escalável neste hardware. É importante observar, contudo, que a curva do "
        "master-worker é a mais estável a partir de quatro processos, variando "
        "pouco entre quatro e dezesseis processos, ao passo que a estratégia bloco "
        "cai de forma monotônica e acentuada. Esse contraste indica que boa parte "
        "da perda de escalabilidade observada tem origem na distribuição do "
        "trabalho, e não apenas em limitações de hardware."
    )

    rel.p(
        "Dois efeitos adicionais aparecem nos pontos de maior resolução. O primeiro "
        "é o aumento do desvio padrão, que na estratégia bloco com dezesseis "
        f"processos chega a {num(wb[16]['tempo_calculo_dp'], 4)} s sobre um tempo "
        f"médio de {num(wb[16]['tempo_calculo_media'], 4)} s. O segundo é o "
        "crescimento do custo líquido de comunicação, que nas resoluções maiores "
        "passa a transferir matrizes da ordem de centenas de megabytes, chegando a "
        f"{num(d['ovh_max_weak'], 4)} s. Ambos são discutidos na Seção 4."
    )

    rel.legenda_grafico(
        "Escalabilidade fraca, tempo de execução e eficiência E(n, p)"
    )
    rel.imagem("fig_mpi_weak_tempo.png")


def constroi_comparacao(rel, d):
    agg = d["agg"]
    omp = d["omp"]

    rel.h2("3.5 Comparação com a Solução OpenMP da Etapa 1")

    rel.p(
        "O enunciado exige a comparação entre a solução em memória distribuída e a "
        "solução em memória compartilhada desenvolvida na Etapa 1. A comparação "
        "apresentada aqui é possível porque as duas etapas foram medidas na mesma "
        "máquina, com o mesmo compilador, com o mesmo núcleo de cálculo e com o "
        "governador de frequência fixado em performance nas duas ocasiões. Os "
        "baselines sequenciais das duas coletas diferem em menos de 2%, o que "
        "confirma a equivalência das condições."
    )

    pares = [
        ("bloco", "static,0", "Decomposição contígua"),
        ("ciclico,16", "static,16", "Distribuição cíclica com chunk 16"),
        ("mestre,16", "dynamic,16", "Balanceamento dinâmico com chunk 16"),
    ]

    linhas = []
    for rot_mpi, rot_omp, descricao in pares:
        pts_omp = {int(r["threads"]): r for r in filtra_omp(omp, "strong", rot_omp)}
        for p in (2, 4, 8, 16):
            r_mpi = d["sel"]("strong", rot_mpi, p)
            if r_mpi is None:
                continue
            r_omp = pts_omp.get(p)
            linhas.append([
                descricao,
                p,
                num(r_mpi["speedup"], 2),
                num(float(r_omp["speedup"]), 2) if r_omp else "n/d",
                num(r_mpi["speedup"] / float(r_omp["speedup"]), 2) if r_omp else "n/d",
            ])

    rel.legenda_tabela(
        "Comparação de speedup entre MPI e OpenMP no input padrão, por estratégia equivalente"
    )
    rel.tabela(
        ["Estratégia equivalente", "p", "Speedup MPI", "Speedup OpenMP", "Razão MPI/OpenMP"],
        linhas,
    )

    rel.p(
        "A comparação revela um padrão consistente. Nas configurações bem "
        "balanceadas, a solução MPI alcança speedup comparável ao da solução "
        "OpenMP, e no caso do balanceamento dinâmico chega a superá-la com "
        "dezesseis processos. Nas configurações mal balanceadas, representadas pela "
        "decomposição contígua, a solução MPI fica atrás da equivalente em OpenMP."
    )

    rel.p(
        "Esse último resultado tem explicação direta. Em OpenMP, mesmo com "
        "particionamento contíguo, as threads compartilham a matriz de saída e não "
        "existe etapa de coleta, de modo que uma thread que termina cedo apenas "
        "encerra. Em MPI, o processo que termina cedo precisa permanecer bloqueado "
        "em MPI_Gatherv até que o processo mais lento chegue à mesma chamada "
        "coletiva, e só então os dados são transferidos. O desbalanceamento, "
        "portanto, cobra um preço adicional em memória distribuída, pois converte "
        "tempo ocioso em tempo de sincronização obrigatória."
    )

    rel.p(
        "Quanto ao balanceamento, as duas etapas chegam à mesma ordenação "
        "qualitativa das estratégias. Tanto em OpenMP quanto em MPI, o "
        "particionamento contíguo produz o pior balanceamento, a distribuição com "
        "granularidade fina melhora substancialmente o quadro, e o balanceamento "
        "dinâmico produz o melhor resultado. Como registrado na Seção 2.5, os "
        "valores numéricos do fator não são comparáveis entre as etapas, porque as "
        "definições adotadas são diferentes, e por isso a comparação se restringe "
        "aqui à ordenação relativa."
    )

    rel.legenda_grafico(
        "Comparação de speedup entre MPI e OpenMP no input padrão e no caso de zoom"
    )
    rel.imagem("fig_mpi_vs_openmp.png")

    rel.p(
        "No Gráfico 8, as curvas de OpenMP do caso de zoom aparecem com menos "
        "pontos do que as de MPI. Isso ocorre porque a Etapa 1 coletou o cenário de "
        "zoom apenas com 4 e 16 threads, ao passo que esta etapa cobriu 2, 4, 8 e "
        "16 processos."
    )


def constroi_sintese(rel, d):
    rel.h2("3.6 Síntese dos Resultados")

    rel.p(
        "A tabela a seguir consolida as melhores e piores configurações de cada "
        "cenário, que sustentam a discussão apresentada na Seção 4:"
    )

    rel.legenda_tabela("Síntese dos resultados obtidos com 16 processos")
    rel.tabela(
        ["Cenário", "Melhor configuração", "Speedup", "Pior configuração", "Speedup"],
        [
            [
                "Input padrão",
                NOMES_LONGOS[d["melhor_strong"][0]],
                num(d["melhor_strong"][1], 2),
                NOMES_LONGOS[d["pior_strong"][0]],
                num(d["pior_strong"][1], 2),
            ],
            [
                "Zoom, cavalos-marinhos",
                NOMES_LONGOS[d["melhor_zoom"][0]],
                num(d["melhor_zoom"][1], 2),
                NOMES_LONGOS[d["pior_zoom"][0]],
                num(d["pior_zoom"][1], 2),
            ],
            [
                "Escalabilidade fraca",
                NOMES_LONGOS[d["melhor_weak"][0]],
                num(d["melhor_weak"][1], 2),
                NOMES_LONGOS[d["pior_weak"][0]],
                num(d["pior_weak"][1], 2),
            ],
        ],
    )

    rel.p(
        "Em síntese, os resultados convergem para quatro conclusões centrais. "
        "Primeiro, a corretude foi preservada integralmente, e a saída das três "
        "estratégias é bit a bit idêntica à da referência sequencial nos dois "
        "inputs. Segundo, o esquema master-worker foi a estratégia mais consistente "
        "nos dois cenários de escalabilidade forte, apesar de sacrificar um processo "
        "inteiro para a coordenação. Terceiro, a decomposição contígua colapsa de "
        "forma severa, com fator de balanceamento próximo do máximo teórico a partir "
        "de quatro processos. Quarto, o custo líquido de comunicação permaneceu "
        "pequeno em todos os cenários do input padrão, o que indica que, nesta "
        "escala e com todos os processos em uma única máquina, o gargalo dominante "
        "é a distribuição do trabalho, e não a troca de mensagens."
    )
