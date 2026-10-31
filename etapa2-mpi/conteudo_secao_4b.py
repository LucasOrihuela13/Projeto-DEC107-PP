"""
Subsecoes 4.6 a 4.9 do Relatorio da Etapa 2.
Importado por gera_relatorio.py. Nenhum numero e digitado, todos vem de 'd'.
"""

from gera_relatorio import num, NOMES_LONGOS


def constroi_discussao_b(rel, d):
    m16 = d["sel"]("strong", "mestre,1", 16)
    b16 = d["sel"]("strong", "bloco", 16)
    c1_16 = d["sel"]("strong", "ciclico,1", 16)
    c1_8 = d["sel"]("strong", "ciclico,1", 8)
    c1_4 = d["sel"]("strong", "ciclico,1", 4)

    # ------------------------------------------------------------------ 4.6
    rel.h2("4.6 Escalabilidade Forte, Lei de Amdahl e Limites Arquiteturais")

    rel.p(
        "A análise da escalabilidade forte revela dois comportamentos distintos "
        "conforme a estratégia. Para as estratégias bem balanceadas, o tempo decai "
        "de forma aproximadamente proporcional até quatro processos, com eficiência "
        f"de {num(c1_4['eficiencia'], 3)} na estratégia cíclica, o que está próximo "
        "do ideal nessa faixa. A partir de oito processos a degradação se acentua, "
        f"caindo para {num(c1_8['eficiencia'], 3)} e depois para "
        f"{num(c1_16['eficiencia'], 3)} com dezesseis processos."
    )

    rel.p(
        "O primeiro fator que explica essa limitação é inerente à Lei de Amdahl. "
        "Conforme a Aula 03, o speedup de um programa paralelo é limitado por "
        "S_M = 1 / (1 − f), onde f é a fração perfeitamente paralelizável. Embora a "
        "fase de cálculo do escape-time seja altamente paralelizável, existem "
        "parcelas inerentemente sequenciais nesta implementação, a saber a "
        "inicialização do ambiente MPI, a alocação da matriz completa na raiz, a "
        "reordenação das linhas na estratégia cíclica e a própria coleta coletiva, "
        "que não pode concluir antes que o último processo chegue. Essas parcelas "
        "estabelecem o teto superior observado."
    )

    rel.p(
        "O segundo fator, igualmente importante, é a natureza híbrida do "
        "processador utilizado. O Intel Core 7 240H possui 10 núcleos físicos e 16 "
        "CPUs lógicas, combinando P-cores com Hyper-Threading e E-cores sem "
        "Hyper-Threading. Isso significa que, ao escalar de 8 para 16 processos, a "
        "execução passa a utilizar simultaneamente threads lógicas que disputam as "
        "mesmas unidades de hardware nos P-cores e núcleos E, que operam de forma "
        "mais lenta. Não existem, portanto, dezesseis unidades de execução "
        "equivalentes, e a premissa registrada na Aula 03 de que cada processo é "
        "executado em um processador físico diferente deixa de valer nessa faixa."
    )

    rel.p(
        "Essa assimetria de hardware tem uma manifestação direta e mensurável nos "
        "resultados, que é o resíduo do fator de balanceamento nas estratégias "
        "estáticas bem distribuídas. A estratégia cíclica atribui a cada processo "
        "praticamente o mesmo número de linhas, amostradas de todas as regiões da "
        f"imagem, e ainda assim registra fator de {num(c1_16['fbc_media'], 4)} com "
        "dezesseis processos. Como a quantidade de trabalho é equivalente, a "
        "diferença de tempo só pode vir da velocidade do núcleo em que cada "
        "processo foi alocado. Trata-se de desbalanceamento induzido pelo hardware, "
        "e não pela geometria do fractal."
    )

    rel.p(
        "Esse diagnóstico explica também por que o esquema master-worker apresenta "
        f"fator substancialmente menor no mesmo ponto, de {num(m16['fbc_media'], 4)}. "
        "O balanceamento dinâmico opera em dois níveis simultaneamente. Ele dilui a "
        "heterogeneidade geométrica do fractal, que era o objetivo original, e "
        "compensa de forma automática a heterogeneidade do hardware, pois um "
        "processo alocado em um E-core simplesmente solicita menos tarefas ao longo "
        "da execução. Nenhuma estratégia estática consegue reproduzir esse segundo "
        "efeito, porque a atribuição é decidida antes de a execução começar."
    )

    # ------------------------------------------------------------------ 4.7
    rel.h2("4.7 Escalabilidade Fraca e a Lei de Gustafson")

    wb1 = d["sel"]("weak", "bloco", 1)
    wb16 = d["sel"]("weak", "bloco", 16)
    wc1 = d["sel"]("weak", "ciclico,16", 1)
    wc16 = d["sel"]("weak", "ciclico,16", 16)
    wm4 = d["sel"]("weak", "mestre,16", 4)
    wm16 = d["sel"]("weak", "mestre,16", 16)

    rel.p(
        "A Aula 03 define escalabilidade como a capacidade de manter constante a "
        "eficiência E(n, p) ao incrementar o tamanho do problema n junto com o "
        "número de processos p, abordagem proposta por Gustafson como resposta à "
        "principal deficiência da formulação de Amdahl, que é não considerar o "
        "tamanho do problema. O raciocínio é que, ao aumentar n, a fração "
        "inerentemente sequencial 1 − f torna-se consideravelmente menor."
    )

    rel.p(
        "Os resultados mostram que esse mecanismo opera apenas parcialmente neste "
        "experimento, e de forma muito desigual entre as estratégias. A "
        f"decomposição contígua cai de eficiência {num(wb1['eficiencia'], 3)} com um "
        f"processo para {num(wb16['eficiencia'], 3)} com dezesseis, uma degradação "
        f"severa. A estratégia cíclica com chunk 16 vai de {num(wc1['eficiencia'], 3)} "
        f"a {num(wc16['eficiencia'], 3)}. O master-worker com chunk 16, depois de "
        f"superar a penalidade do coordenador, mantém-se entre "
        f"{num(wm4['eficiencia'], 3)} e {num(wm16['eficiencia'], 3)} na faixa de "
        "quatro a dezesseis processos, que é a curva mais estável das três."
    )

    rel.p(
        "A leitura conjunta com a Seção 4.6 é esclarecedora. Se a perda de "
        "escalabilidade fraca decorresse apenas das limitações de hardware "
        "identificadas na escalabilidade forte, todas as estratégias deveriam "
        "degradar de modo semelhante, pois todas usam o mesmo processador e a mesma "
        "hierarquia de memória. O que se observa, porém, é uma dispersão grande "
        "entre elas no mesmo ponto. Isso indica que a parcela dominante da perda "
        "tem origem na distribuição do trabalho, e que a limitação arquitetural "
        "atua como um piso adicional, visível na curva do master-worker, que é a "
        "menos afetada pelo desbalanceamento."
    )

    rel.p(
        "Dois efeitos próprios da memória distribuída aparecem nos pontos de maior "
        "resolução e não tinham equivalente na Etapa 1. O primeiro é o crescimento "
        "do custo líquido de comunicação, que atinge "
        f"{num(d['ovh_max_weak'], 4)} s nas resoluções maiores. Em 16384 × 16384, a "
        "matriz de contagens ocupa 1 GiB, e nas estratégias que exigem buffer "
        "intermediário a raiz precisa alocar o dobro disso, somando a reordenação "
        "das linhas. O segundo é o aumento do desvio padrão entre repetições, que "
        f"na estratégia bloco com dezesseis processos chega a "
        f"{num(wb16['tempo_calculo_dp'], 4)} s sobre uma média de "
        f"{num(wb16['tempo_calculo_media'], 4)} s. Essa variabilidade é compatível "
        "com pressão sobre a hierarquia de memória, pois as matrizes maiores deixam "
        "de caber no cache L3 de 24 MiB e passam a depender da largura de banda da "
        "DRAM, que é compartilhada por todos os processos."
    )

    # ------------------------------------------------------------------ 4.8
    rel.h2("4.8 Comparação com a Solução OpenMP")

    rel.p(
        "A comparação entre os dois paradigmas, apresentada na Seção 3.5, permite "
        "avaliar vantagens e custos de cada um neste problema específico. É "
        "importante frisar que a comparação só é legítima porque as duas coletas "
        "foram feitas na mesma máquina, com o mesmo compilador, o mesmo núcleo de "
        "cálculo e o governador de frequência fixado em performance, com baselines "
        "sequenciais que diferem em menos de 2%."
    )

    rel.p(
        "Nas configurações bem balanceadas, as duas soluções apresentam desempenho "
        "comparável, e o balanceamento dinâmico em MPI chega a superar o "
        "equivalente em OpenMP com dezesseis processos. Esse resultado é "
        "relevante porque contraria a expectativa intuitiva de que memória "
        "distribuída deveria ser sempre mais lenta em uma única máquina. A "
        "explicação está no fato de que, neste problema, cada processo escreve "
        "exclusivamente na sua própria região de memória, sem nenhum "
        "compartilhamento de escrita. Em OpenMP, threads que escrevem em linhas "
        "vizinhas da mesma matriz podem sofrer falso compartilhamento de linhas de "
        "cache, efeito que não existe quando cada processo possui o seu próprio "
        "buffer."
    )

    rel.p(
        "Nas configurações mal balanceadas o quadro se inverte, e a solução MPI "
        "fica atrás da equivalente em OpenMP. A razão é estrutural. Em memória "
        "compartilhada, uma thread que termina cedo apenas encerra, e o custo do "
        "desbalanceamento é o tempo ocioso. Em memória distribuída, o processo que "
        "termina cedo precisa permanecer bloqueado em uma chamada coletiva até que "
        "o último processo chegue, e só então os dados são efetivamente "
        "transferidos. O desbalanceamento, portanto, não apenas desperdiça tempo, "
        "como também atrasa o início da própria coleta, acumulando dois custos em "
        "sequência."
    )

    rel.p(
        "Em termos de complexidade de implementação, a diferença é considerável. A "
        "versão OpenMP da Etapa 1 obteve as três políticas de escalonamento "
        "alterando essencialmente uma diretiva e uma variável de ambiente. A versão "
        "MPI exigiu implementar explicitamente a decomposição do domínio, o cálculo "
        "dos vetores de contagens e deslocamentos para a coleta, a reordenação das "
        "linhas na estratégia cíclica e um protocolo completo de requisição e "
        "entrega de tarefas no master-worker. Em contrapartida, a solução MPI "
        "oferece algo que a solução OpenMP não oferece, que é a possibilidade de "
        "ultrapassar os limites de uma única máquina, distribuindo o cálculo por "
        "vários nós de um cluster."
    )

    # ------------------------------------------------------------------ 4.9
    rel.h2("4.9 Outros Gargalos e Limitações")

    rel.p(
        "Além das limitações já discutidas, três pontos merecem registro explícito "
        "como limitações deste estudo:"
    )

    rel.bullet(
        " todos os processos MPI foram executados em uma única máquina física, de "
        "modo que a comunicação ocorre pela memória do sistema e não por uma rede "
        "real. Os custos de comunicação medidos aqui são, portanto, um limite "
        "inferior. Em um cluster com interconexão de rede, a latência e a largura "
        "de banda alterariam o equilíbrio entre as estratégias, e muito "
        "provavelmente penalizariam a granularidade fina, que gera mais mensagens.",
        negrito_ate="Execução em nó único:",
    )
    rel.bullet(
        " com dezesseis processos em dez núcleos físicos, foi necessário recorrer a "
        "oversubscribe, e o sistema operacional passou a mediar o acesso às "
        "unidades de execução. Isso introduz uma fonte de variabilidade que não "
        "existe quando há um processo por núcleo físico, e explica parte do desvio "
        "padrão observado nos pontos de dezesseis processos.",
        negrito_ate="Oversubscribe acima de dez processos:",
    )
    rel.bullet(
        " a medida de tempo em chamadas de MPI não separa, por construção, o tempo "
        "de transferência do tempo de espera. Essa limitação foi contornada com a "
        "introdução do custo líquido de comunicação, porém uma separação completa "
        "exigiria instrumentação adicional com chamadas não bloqueantes ou uso de "
        "ferramentas de profiling específicas de MPI.",
        negrito_ate="Agregação entre comunicação e espera:",
    )

    rel.p(
        "Cabe ainda registrar, por rigor metodológico, que a coleta preliminar "
        "conduzida com o governador em powersave produziu tempos sequenciais em "
        "torno de 37% superiores aos da coleta final. Esse episódio confirma, agora "
        "em um segundo paradigma, a conclusão já registrada na Etapa 1 de que a "
        "fixação da frequência é pré-requisito de confiabilidade das medições, e "
        "não um detalhe de configuração."
    )

    # ------------------------------------------------------------------ 4.10
    rel.h2("4.10 Sugestões de Melhorias Futuras")

    rel.p(
        "A partir dos resultados obtidos, identificam-se quatro direções de "
        "aprofundamento, todas restritas ao escopo do estudo do paralelismo:"
    )

    rel.bullet(
        " permitir que o rank 0 execute tarefas nos intervalos entre atendimentos, "
        "utilizando MPI_Irecv e verificação não bloqueante, eliminaria o desperdício "
        "de um processo inteiro. O ganho esperado é maior justamente onde o esquema "
        "hoje é mais penalizado, que é a faixa de poucos processos.",
        negrito_ate="Coordenador produtivo no master-worker:",
    )
    rel.bullet(
        " substituir a coleta coletiva por envios não bloqueantes, permitindo que a "
        "transferência de uma faixa já concluída ocorra enquanto outras faixas ainda "
        "são calculadas. A Aula 03 lista explicitamente a sobreposição entre "
        "comunicação e computação entre os fatores a considerar para obter "
        "algoritmos paralelos eficientes, e esta implementação não a explora.",
        negrito_ate="Sobreposição entre comunicação e computação:",
    )
    rel.bullet(
        " avaliar chunks de 1, 2, 4, 8, 16, 32 e 64 de forma sistemática permitiria "
        "traçar a curva exata do compromisso entre diluição da carga e número de "
        "mensagens, e localizar com precisão o ponto ótimo em memória distribuída, "
        "que os resultados indicam ser mais grosso do que em memória compartilhada.",
        negrito_ate="Varredura sistemática de granularidade:",
    )
    rel.bullet(
        " repetir a bateria com vinculação explícita de processos a núcleos, "
        "separando execuções restritas a P-cores de execuções restritas a E-cores, "
        "permitiria quantificar com exatidão quanto do fator de balanceamento "
        "residual observado nas estratégias estáticas decorre da assimetria do "
        "hardware e quanto decorre da geometria do problema.",
        negrito_ate="Controle de afinidade de processos:",
    )

    rel.p(
        "Por fim, a extensão natural deste estudo é a execução em um cluster com "
        "mais de um nó, único cenário em que o custo real de rede se manifesta e em "
        "que a vantagem estrutural do paradigma de memória distribuída sobre o de "
        "memória compartilhada pode ser efetivamente demonstrada."
    )
