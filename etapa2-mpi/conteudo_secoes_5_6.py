"""
Secoes 5 e 6 do Relatorio da Etapa 2, mais a Declaracao de Transparencia.
Importado por gera_relatorio.py. Nenhum numero e digitado, todos vem de 'd'.
"""

from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

from gera_relatorio import num, NOMES_LONGOS


def constroi_conclusao(rel, d):
    rel.h1("5. Conclusão")

    m16 = d["sel"]("strong", "mestre,1", 16)
    b16 = d["sel"]("strong", "bloco", 16)
    zm16 = d["sel"]("zoom", "mestre,1", 16)

    rel.p(
        "A Etapa 2 do projeto cumpriu o objetivo proposto, que era implementar, "
        "validar e comparar experimentalmente estratégias de distribuição do "
        "domínio da imagem em memória distribuída com MPI, isolando o efeito dessas "
        "estratégias sobre o desbalanceamento de carga inerente ao Conjunto de "
        "Mandelbrot. A corretude foi preservada em todos os cenários testados, e a "
        "matriz de contagens das três estratégias foi bit a bit idêntica à "
        "referência sequencial tanto no input padrão quanto no caso de zoom."
    )

    rel.p(
        "O principal aprendizado desta etapa não foi que a paralelização em memória "
        "distribuída reduz o tempo de execução, o que já era esperado, mas sim que "
        "o custo do desbalanceamento muda de natureza quando se sai da memória "
        "compartilhada. Em OpenMP, uma thread mal servida apenas termina cedo e "
        "fica ociosa. Em MPI, o processo que termina cedo fica bloqueado dentro de "
        "uma chamada coletiva, impedindo que a coleta do resultado comece antes que "
        "o último processo chegue. O desbalanceamento deixa de ser apenas "
        "desperdício e passa a ser atraso imposto a todos."
    )

    rel.p(
        "Os números tornam esse ponto concreto. Com dezesseis processos no input "
        f"padrão, a decomposição contígua atingiu speedup de {num(b16['speedup'], 2)} "
        f"com fator de balanceamento de {num(b16['fbc_media'], 4)}, ao passo que o "
        f"esquema master-worker alcançou {num(m16['speedup'], 2)} com fator de "
        f"{num(m16['fbc_media'], 4)}. No caso de desbalanceamento acentuado a "
        f"ordenação se manteve, com o master-worker atingindo "
        f"{num(zm16['speedup'], 2)}. Para o mesmo problema, o mesmo hardware e o "
        "mesmo núcleo de cálculo, a escolha da estratégia de distribuição mais do "
        "que triplicou o ganho obtido."
    )

    rel.p(
        "A análise do custo de comunicação trouxe uma conclusão que inicialmente "
        "contrariava a expectativa. Esperava-se que a coleta da imagem fosse um "
        "gargalo relevante em memória distribuída, especialmente nas resoluções "
        "maiores. O custo líquido de comunicação, porém, permaneceu pequeno em "
        "todos os cenários do input padrão. O que parecia custo de comunicação, "
        "quando medido pelo tempo acumulado em chamadas de MPI, revelou-se tempo "
        "ocioso de espera causado pelo próprio desbalanceamento. Separar essas duas "
        "parcelas, conforme a decomposição apresentada na Aula 03, foi o que "
        "permitiu diagnosticar corretamente o gargalo em vez de atribuí-lo à "
        "infraestrutura de troca de mensagens."
    )

    rel.p(
        "Um achado metodológico merece destaque por ter valor além desta etapa. O "
        "fator de balanceamento das estratégias estáticas não chegou a zero mesmo "
        "quando a quantidade de trabalho atribuída a cada processo era "
        "praticamente idêntica. Como a carga era equivalente, a diferença de tempo "
        "só podia vir da velocidade do núcleo em que cada processo foi alocado. "
        "Isso evidenciou que, em um processador híbrido, o balanceamento dinâmico "
        "opera em dois níveis ao mesmo tempo, diluindo a heterogeneidade do "
        "problema e compensando automaticamente a heterogeneidade do hardware. "
        "Nenhuma estratégia estática é capaz do segundo efeito, pois decide a "
        "atribuição antes de a execução começar."
    )

    rel.p(
        "A escalabilidade fraca, por sua vez, mostrou que o programa não é "
        "plenamente escalável neste hardware pelo critério de Gustafson adotado na "
        "disciplina, uma vez que nenhuma estratégia manteve a eficiência constante "
        "ao longo de toda a faixa. A dispersão entre as estratégias no mesmo ponto, "
        "contudo, indicou que a parcela dominante dessa perda tem origem na "
        "distribuição do trabalho, e que a limitação arquitetural atua como um piso "
        "adicional e não como causa única."
    )

    rel.p(
        "Do ponto de vista metodológico, três decisões se mostraram determinantes "
        "para a confiabilidade dos resultados. A primeira foi fixar o governador de "
        "frequência em performance, sem a qual os tempos ficaram cerca de 37% mais "
        "lentos e incomparáveis com os da Etapa 1. A segunda foi medir um baseline "
        "sequencial próprio para cada resolução da escalabilidade fraca, sem o qual "
        "não seria possível aplicar a fórmula de eficiência da disciplina nesse "
        "cenário. A terceira foi instrumentar o tempo de computação e o tempo em "
        "MPI por processo, o que permitiu ir além do tempo total e diagnosticar "
        "efetivamente onde o desbalanceamento acontece. Sem essa granularidade de "
        "medição, teria sido fácil concluir apenas que uma estratégia é mais rápida "
        "que outra, sem compreender o porquê."
    )


def constroi_referencias(rel, d):
    rel.h1("6. Referências")

    referencias = [
        "UESC, Universidade Estadual de Santa Cruz. Notas de aula e enunciado da "
        "disciplina DEC107, Processamento Paralelo, 2026.2. Em especial a Aula 02, "
        "Introdução ao Processamento Paralelo, a Aula 03, Caracterização de "
        "desempenho em programas paralelos, e as Aulas 10 e 11, MPI.",

        "ETVORELLANA. RepoDEC107-PP-2026_2, Exemplos e exercícios da disciplina "
        "DEC107-PP. GitHub, 2026. Disponível em: "
        "https://github.com/etvorellana/RepoDEC107-PP-2026_2.",

        "MESSAGE PASSING INTERFACE FORUM. MPI: A Message-Passing Interface "
        "Standard. Disponível em: https://www.mpi-forum.org/docs/.",

        "THE OPEN MPI PROJECT. Open MPI Documentation. Disponível em: "
        "https://docs.open-mpi.org/.",

        "AMDAHL, G. Validity of the single processor approach to achieving large "
        "scale computing capabilities. Proceedings of the April 18-20, 1967, Spring "
        "Joint Computer Conference, p. 483-485, 1967.",

        "GUSTAFSON, J. L. Reevaluating Amdahl's law. Communications of the ACM, "
        "v. 31, n. 5, p. 532-533, 1988.",

        "PEITGEN, H.-O.; JÜRGENS, H.; SAUPE, D. Chaos and Fractals: New Frontiers "
        "of Science. 2. ed. New York: Springer, 2004. Referência de apoio aos "
        "conceitos teóricos do Conjunto de Mandelbrot e do método de escape-time "
        "apresentados na Introdução.",

        "RODRIGUES, C. S.; ORIHUELA, L. B. Relatório da Etapa 1, Benchmark de "
        "Geração do Conjunto de Mandelbrot, Implementação sequencial e paralela em "
        "memória compartilhada com OpenMP. DEC107, UESC, 2026.2. Fonte dos dados de "
        "OpenMP utilizados na comparação entre paradigmas apresentada na Seção 3.5.",
    ]

    for ref in referencias:
        p = rel.doc.add_paragraph(ref, style="List Bullet")
        p.paragraph_format.space_after = Pt(8)


def constroi_declaracao(rel, d):
    rel.doc.add_page_break()

    p = rel.doc.add_paragraph()
    run = p.add_run("DECLARAÇÃO DE TRANSPARÊNCIA E USO DE INTELIGÊNCIA ARTIFICIAL")
    run.bold = True
    run.font.size = Pt(13)

    rel.p(
        "Eu, Cibelle Sousa Rodrigues, e eu, Lucas Braga Orihuela, regularmente "
        "matriculados no curso de Ciência da Computação, declaramos para os devidos "
        "fins que, na elaboração do trabalho intitulado \"Benchmark de Geração do "
        "Conjunto de Mandelbrot (Escape-Time): Etapa 2, MPI\", submetido como "
        "requisito para a disciplina DEC107, Processamento Paralelo, adotamos as "
        "seguintes práticas em relação ao uso de ferramentas de Inteligência "
        "Artificial generativa:"
    )

    rel.p("(Assinale a opção aplicável)")
    rel.p(
        "( ) Não utilizei ferramentas de Inteligência Artificial na concepção, "
        "desenvolvimento, programação ou redação deste trabalho."
    )
    rel.p(
        "( X ) Utilizei ferramentas de Inteligência Artificial (ex: ChatGPT, GitHub "
        "Copilot, Claude, etc.) como recursos de apoio."
    )

    rel.p(
        "Detalhamento do Uso: A ferramenta utilizada foi Claude, da Anthropic. O uso "
        "se deu exclusivamente nas seguintes etapas do projeto:"
    )

    usos = [
        "Apoio na finalização do script de automação dos experimentos, "
        "especificamente na implementação dos laços do caso de zoom e da "
        "escalabilidade fraca.",
        "Revisão metodológica da coleta, que identificou a necessidade de medir um "
        "baseline sequencial próprio para cada resolução da escalabilidade fraca e "
        "a necessidade de fixar o governador de frequência em performance para "
        "manter a comparabilidade com a Etapa 1.",
        "Auxílio na depuração do script de pós-processamento, incluindo a correção "
        "da leitura do arquivo de resultados agregados da Etapa 1 e do cálculo da "
        "eficiência na escalabilidade fraca.",
        "Apoio na estruturação e na redação do presente relatório, a partir dos "
        "dados experimentais coletados pela dupla.",
    ]
    for uso in usos:
        rel.doc.add_paragraph(uso, style="List Bullet")

    rel.p(
        "Termo de Responsabilidade: Declaramos estar cientes de que ferramentas de "
        "IA não são isentas de erros, vieses ou alucinações. Sendo assim, atestamos "
        "que toda a responsabilidade pela autoria, integridade, originalidade e "
        "exatidão do conteúdo submetido é exclusivamente nossa. Confirmamos que todo "
        "o código-fonte, dados de testes e textos gerados ou modificados com o "
        "auxílio de IA foram rigorosamente revisados, testados e validados por nós, "
        "garantindo que os resultados refletem o nosso próprio entendimento e "
        "esforço intelectual, sem incorrer em plágio intelectual ou acadêmico."
    )

    rel.p(f"Ilhéus - BA, {d['data_entrega']}")

    rel.doc.add_paragraph()
    for nome, matricula in (
        ("Cibelle Sousa Rodrigues", "202310768"),
        ("Lucas Braga Orihuela", "202311125"),
    ):
        p = rel.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.add_run(nome)
        p.add_run("\n")
        p.add_run(f"Matrícula: {matricula}")
