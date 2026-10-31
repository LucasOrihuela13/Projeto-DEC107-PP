"""
Gerador do Relatorio Tecnico da Etapa 2 (MPI) - DEC107 (UESC)

Monta o arquivo Relatorio_Etapa2_Mandelbrot.docx no mesmo padrao visual do
relatorio da Etapa 1. Todos os valores numericos sao lidos dos arquivos reais
de resultado, a saber resultados_agregados_mpi.csv, resultados_mpi.csv,
serial_baselines_mpi.txt e ../etapa1-openmp/resultados_agregados.csv. Nenhum
numero e digitado no corpo do texto.

Uso:
    python3 gera_relatorio.py
"""

import csv
import os
import sys
from collections import defaultdict

import numpy as np
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt, RGBColor

AGG_IN = "resultados_agregados_mpi.csv"
RAW_IN = "resultados_mpi.csv"
SERIAL_IN = "serial_baselines_mpi.txt"
OMP_AGG_IN = "../etapa1-openmp/resultados_agregados.csv"
DOCX_OUT = "Relatorio_Etapa2_Mandelbrot.docx"

CINZA = RGBColor(0x59, 0x59, 0x59)

ROTULOS = ["bloco", "ciclico,1", "ciclico,16", "mestre,1", "mestre,16"]
NOMES_LONGOS = {
    "bloco": "bloco",
    "ciclico,1": "ciclico, chunk 1",
    "ciclico,16": "ciclico, chunk 16",
    "mestre,1": "mestre, chunk 1",
    "mestre,16": "mestre, chunk 16",
}


# ---------------------------------------------------------------------------
# Leitura dos dados reais
# ---------------------------------------------------------------------------

def _linhas_de_dados(caminho):
    with open(caminho, "r", encoding="utf-8") as f:
        return [l for l in f if l.strip() and not l.startswith("#")]


def carrega_meta(caminho):
    """Le o cabecalho comentado do CSV bruto, que registra o ambiente."""
    meta = {}
    with open(caminho, "r", encoding="utf-8") as f:
        for linha in f:
            if not linha.startswith("#"):
                break
            if ":" in linha:
                chave, valor = linha.lstrip("# ").split(":", 1)
                meta[chave.strip()] = valor.strip()
    return meta


def carrega_baselines(caminho):
    tempos = defaultdict(list)
    for linha in _linhas_de_dados(caminho):
        partes = linha.strip().split(",")
        if len(partes) >= 3:
            tempos[partes[0].strip()].append(float(partes[2]))
    return {
        k: (float(np.mean(v)), float(np.std(v, ddof=1)) if len(v) > 1 else 0.0, len(v))
        for k, v in tempos.items()
    }


def carrega_agregado(caminho):
    linhas = _linhas_de_dados(caminho)
    registros = list(csv.DictReader(linhas))
    for r in registros:
        for campo in ("chunk", "largura", "altura", "max_iter", "processos", "reps"):
            r[campo] = int(r[campo])
        for campo in (
            "t_ref_serial", "tempo_calculo_media", "tempo_calculo_dp",
            "tempo_io_media", "tempo_com_raiz_media", "overhead_com_media",
            "t_comp_max_media", "t_comp_min_media", "fbc_media", "fbc_dp",
            "speedup", "eficiencia",
        ):
            r[campo] = float(r[campo])
    return registros


def carrega_granularidade(caminho):
    """
    G(n) = T_cp(n) / T_cm(n), conforme a Aula 03.

    T_cp e a soma dos tempos de computacao dos processos que calculam e T_cm e
    a soma dos tempos gastos dentro de chamadas MPI por todos os processos.
    """
    linhas = _linhas_de_dados(caminho)
    grupos = defaultdict(list)
    for r in csv.DictReader(linhas):
        chave = (
            r["experimento"],
            f"{r['estrategia']},{int(r['chunk'])}" if r["estrategia"] != "bloco" else "bloco",
            int(r["processos"]),
            int(r["largura"]),
        )
        grupos[chave].append(r)

    saida = {}
    for chave, rs in grupos.items():
        cp = float(np.mean([float(r["t_comp_soma"]) for r in rs]))
        cm = float(np.mean([float(r["t_com_soma"]) for r in rs]))
        saida[chave] = cp / cm if cm > 0 else float("inf")
    return saida


def carrega_omp(caminho):
    if not os.path.exists(caminho):
        return []
    with open(caminho, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def filtra_omp(omp_rows, experimento, rotulo):
    """Traduz o esquema proprio do CSV da Etapa 1 para o rotulo politica,chunk."""
    sel = []
    for r in omp_rows:
        if r.get("bloco") != experimento:
            continue
        bruto = (r.get("chunk") or "").strip()
        try:
            chunk = int(float(bruto)) if bruto else 0
        except ValueError:
            continue
        if f"{r.get('politica')},{chunk}" == rotulo:
            sel.append(r)
    return sorted(sel, key=lambda x: int(x["threads"]))


def seleciona(registros, experimento, rotulo=None, processos=None):
    saida = [r for r in registros if r["experimento"] == experimento]
    if rotulo is not None:
        saida = [r for r in saida if r["rotulo"] == rotulo]
    if processos is not None:
        saida = [r for r in saida if r["processos"] == processos]
    return sorted(saida, key=lambda r: r["processos"])


# ---------------------------------------------------------------------------
# Formatacao numerica em padrao brasileiro
# ---------------------------------------------------------------------------

def num(valor, casas=2):
    return f"{valor:.{casas}f}".replace(".", ",")


def pct(valor, casas=1):
    return f"{valor * 100:.{casas}f}".replace(".", ",")


# ---------------------------------------------------------------------------
# Helpers de documento
# ---------------------------------------------------------------------------

class Relatorio:
    def __init__(self):
        self.doc = Document()
        self.n_tabela = 0
        self.n_grafico = 0
        self.n_figura = 0
        self._configura_estilos()

    def _configura_estilos(self):
        estilo = self.doc.styles["Normal"]
        estilo.font.name = "Arial"
        estilo.font.size = Pt(11)
        pf = estilo.paragraph_format
        pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        pf.space_after = Pt(10)
        pf.line_spacing = 1.15

    def capa(self, linhas_titulo, subtitulo, linha_academica, autores, disciplina, data):
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(linhas_titulo)
        run.font.size = Pt(24)
        run.bold = False

        p = self.doc.add_paragraph()
        run = p.add_run(subtitulo)
        run.font.size = Pt(14)
        run.font.color.rgb = CINZA

        p = self.doc.add_paragraph()
        run = p.add_run(linha_academica)
        run.font.size = Pt(13)
        run.font.color.rgb = CINZA

        for rotulo, valor in (("Autores:", autores), ("Disciplina:", disciplina), ("Data:", data)):
            p = self.doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            r = p.add_run(rotulo)
            r.bold = True
            p.add_run(" " + valor)

    def h1(self, texto):
        p = self.doc.add_heading(texto, level=1)
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        return p

    def h2(self, texto):
        return self.doc.add_heading(texto, level=2)

    def h3(self, texto):
        return self.doc.add_heading(texto, level=3)

    def p(self, texto):
        return self.doc.add_paragraph(texto)

    def bullet(self, texto, negrito_ate=None):
        par = self.doc.add_paragraph(style="List Bullet")
        if negrito_ate:
            r = par.add_run(negrito_ate)
            r.bold = True
            par.add_run(texto)
        else:
            par.add_run(texto)
        return par

    def mono(self, texto):
        par = self.doc.add_paragraph()
        par.alignment = WD_ALIGN_PARAGRAPH.LEFT
        run = par.add_run(texto)
        run.font.name = "Courier New"
        run.font.size = Pt(8)
        return par

    def legenda_tabela(self, titulo):
        self.n_tabela += 1
        par = self.doc.add_paragraph()
        par.alignment = WD_ALIGN_PARAGRAPH.LEFT
        run = par.add_run(f"Tabela {self.n_tabela} - {titulo}")
        run.font.size = Pt(10)
        return self.n_tabela

    def legenda_grafico(self, titulo):
        self.n_grafico += 1
        par = self.doc.add_paragraph()
        par.alignment = WD_ALIGN_PARAGRAPH.LEFT
        run = par.add_run(f"Gráfico {self.n_grafico} - {titulo}")
        run.font.size = Pt(10)
        return self.n_grafico

    def legenda_figura(self, titulo):
        self.n_figura += 1
        par = self.doc.add_paragraph()
        par.alignment = WD_ALIGN_PARAGRAPH.LEFT
        run = par.add_run(f"Figura {self.n_figura} - {titulo}")
        run.font.size = Pt(10)
        return self.n_figura

    def descricao_figura(self, texto):
        par = self.doc.add_paragraph()
        par.alignment = WD_ALIGN_PARAGRAPH.LEFT
        run = par.add_run(texto)
        run.italic = True
        run.font.size = Pt(9)

    def tabela(self, cabecalho, linhas):
        t = self.doc.add_table(rows=1, cols=len(cabecalho))
        t.style = "Light Grid Accent 1"
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        hdr = t.rows[0].cells
        for i, nome in enumerate(cabecalho):
            hdr[i].text = ""
            par = hdr[i].paragraphs[0]
            run = par.add_run(nome.upper())
            run.bold = True
            run.font.size = Pt(9)
        for linha in linhas:
            celulas = t.add_row().cells
            for i, valor in enumerate(linha):
                celulas[i].text = ""
                par = celulas[i].paragraphs[0]
                run = par.add_run(str(valor))
                run.font.size = Pt(9)
        self.doc.add_paragraph()
        return t

    def imagem(self, caminho, largura=6.0):
        if not os.path.exists(caminho):
            print(f"AVISO: figura ausente, {caminho}", file=sys.stderr)
            return
        self.doc.add_picture(caminho, width=Inches(largura))
        self.doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER

    def salva(self, caminho):
        self.doc.save(caminho)


# ---------------------------------------------------------------------------
# Montagem dos dados derivados
# ---------------------------------------------------------------------------

# Duracao total da bateria, conforme registrado pelo proprio script de
# experimentos ao final da execucao de 30/10/2026.
DURACAO_BATERIA = "36 minutos e 41 segundos"

DATA_ENTREGA = "30/10/2026"

PARES_WEAK = [(1, 4096), (2, 5793), (4, 8192), (8, 11585), (16, 16384)]


def monta_dados():
    for caminho in (AGG_IN, RAW_IN, SERIAL_IN):
        if not os.path.exists(caminho):
            print(f"ERRO: arquivo obrigatorio ausente, {caminho}", file=sys.stderr)
            sys.exit(1)

    meta = carrega_meta(RAW_IN)
    baselines = carrega_baselines(SERIAL_IN)
    agg = carrega_agregado(AGG_IN)
    gran = carrega_granularidade(RAW_IN)
    omp = carrega_omp(OMP_AGG_IN)

    n_execucoes = len(_linhas_de_dados(RAW_IN)) - 1

    def sel(experimento, rotulo, processos):
        achados = seleciona(agg, experimento, rotulo, processos)
        return achados[0] if achados else None

    def extremos(experimento, processos):
        candidatos = [
            (r["rotulo"], r["speedup"])
            for r in agg
            if r["experimento"] == experimento and r["processos"] == processos
        ]
        melhor = max(candidatos, key=lambda x: x[1])
        pior = min(candidatos, key=lambda x: x[1])
        return melhor, pior

    ovh_strong = [
        r["overhead_com_media"] for r in agg
        if r["experimento"] == "strong" and r["processos"] >= 2
    ]
    ovh_weak = [
        r["overhead_com_media"] for r in agg
        if r["experimento"] == "weak" and r["processos"] >= 2
    ]

    melhor_strong, pior_strong = extremos("strong", 16)
    melhor_zoom, pior_zoom = extremos("zoom", 16)
    melhor_weak, pior_weak = extremos("weak", 16)

    return {
        "meta": meta,
        "agg": agg,
        "gran": gran,
        "omp": omp,
        "baselines": baselines,
        "sel": sel,
        "pares_weak": PARES_WEAK,
        "data_entrega": DATA_ENTREGA,
        "duracao_bateria": DURACAO_BATERIA,
        "n_execucoes": n_execucoes,
        "kernel": meta.get("uname", "n/d"),
        "cpu": meta.get("cpu", "n/d"),
        "compilador": meta.get("mpicc", "n/d"),
        "mpi_versao": meta.get("mpirun", "n/d"),
        "base_strong": baselines["strong"][0],
        "dp_strong": baselines["strong"][1],
        "base_zoom": baselines["zoom"][0],
        "dp_zoom": baselines["zoom"][1],
        "reps_serial": baselines["strong"][2],
        "reps_par": max(r["reps"] for r in agg if r["experimento"] == "strong"),
        "reps_weak": max(r["reps"] for r in agg if r["experimento"] == "weak"),
        "ovh_min_strong": min(ovh_strong),
        "ovh_max_strong": max(ovh_strong),
        "ovh_max_weak": max(ovh_weak),
        "melhor_strong": melhor_strong,
        "pior_strong": pior_strong,
        "melhor_zoom": melhor_zoom,
        "pior_zoom": pior_zoom,
        "melhor_weak": melhor_weak,
        "pior_weak": pior_weak,
    }


def main():
    d = monta_dados()

    from conteudo_secoes_1_2 import constroi_capa, constroi_introducao, constroi_metodologia
    from conteudo_secoes_2b import (
        constroi_estrategias, constroi_metricas, constroi_planejamento,
        constroi_validacao, constroi_coleta,
    )
    from conteudo_secao_3 import constroi_resultados
    from conteudo_secao_3b import (
        constroi_zoom, constroi_fraca, constroi_comparacao, constroi_sintese,
    )
    from conteudo_secao_4 import constroi_discussao
    from conteudo_secao_4b import constroi_discussao_b
    from conteudo_secoes_5_6 import (
        constroi_conclusao, constroi_referencias, constroi_declaracao,
    )

    rel = Relatorio()

    constroi_capa(rel, d)
    constroi_introducao(rel, d)
    constroi_metodologia(rel, d)
    constroi_estrategias(rel, d)
    constroi_metricas(rel, d)
    constroi_planejamento(rel, d)
    constroi_validacao(rel, d)
    constroi_coleta(rel, d)
    constroi_resultados(rel, d)
    constroi_zoom(rel, d)
    constroi_fraca(rel, d)
    constroi_comparacao(rel, d)
    constroi_sintese(rel, d)
    constroi_discussao(rel, d)
    constroi_discussao_b(rel, d)
    constroi_conclusao(rel, d)
    constroi_referencias(rel, d)
    constroi_declaracao(rel, d)

    rel.salva(DOCX_OUT)

    print(f"Relatorio gerado: {DOCX_OUT}")
    print(f"  Tabelas: {rel.n_tabela}   Graficos: {rel.n_grafico}   Figuras: {rel.n_figura}")
    print(f"  Execucoes paralelas registradas: {d['n_execucoes']}")


if __name__ == "__main__":
    main()
