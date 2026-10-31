"""
Script de pos-processamento e geracao de graficos da Etapa 2 (MPI) - DEC107 (UESC)
Le resultados_mpi.csv, serial_baselines_mpi.txt e ../etapa1-openmp/resultados_agregados.csv,
calcula as metricas oficiais (Speedup, Eficiencia e FBC = (T_max - T_min) / T_max),
salva resultados_agregados_mpi.csv, imprime tabelas-resumo no terminal e gera os graficos PNG.
"""

import os
import sys
import csv
import math
from collections import defaultdict
import numpy as np
import matplotlib.pyplot as plt

plt.rcParams.update({
    "figure.dpi": 150,
    "savefig.dpi": 300,
    "font.size": 10,
    "axes.titlesize": 11,
    "axes.labelsize": 10,
    "legend.fontsize": 8.5,
    "grid.alpha": 0.3,
})

CSV_IN = "resultados_mpi.csv"
SERIAL_IN = "serial_baselines_mpi.txt"
OMP_AGG_IN = "../etapa1-openmp/resultados_agregados.csv"
CSV_AGG_OUT = "resultados_agregados_mpi.csv"


def rotulo_estrategia(est, chunk):
    if est == "bloco":
        return "bloco"
    return f"{est},{chunk}"


def carrega_serial(caminho):
    tempos = defaultdict(list)
    if not os.path.exists(caminho):
        return {}
    with open(caminho, "r", encoding="utf-8") as f:
        for linha in f:
            linha = linha.strip()
            if not linha or linha.startswith("#"):
                continue
            partes = linha.split(",")
            if len(partes) >= 3:
                exp = partes[0].strip()
                t = float(partes[2])
                tempos[exp].append(t)
    return {k: (float(np.mean(v)), float(np.std(v, ddof=1)) if len(v) > 1 else 0.0) for k, v in tempos.items()}


def carrega_mpi_csv(caminho):
    if not os.path.exists(caminho):
        print(f"Erro: arquivo '{caminho}' nao encontrado.", file=sys.stderr)
        sys.exit(1)

    linhas_validas = []
    with open(caminho, "r", encoding="utf-8") as f:
        for linha in f:
            if not linha.strip() or linha.startswith("#"):
                continue
            linhas_validas.append(linha)

    leitor = csv.DictReader(linhas_validas)
    grupos = defaultdict(list)
    for row in leitor:
        chave = (
            row["experimento"].strip(),
            row["estrategia"].strip(),
            int(row["chunk"]),
            int(row["largura"]),
            int(row["altura"]),
            int(row["max_iter"]),
            int(row["processos"]),
        )
        grupos[chave].append(row)
    return grupos


def agrega_resultados(grupos, baselines_serial):
    t_serial_strong = baselines_serial.get("strong", (None, None))[0]
    t_serial_zoom = baselines_serial.get("zoom", (None, None))[0]

    # Fallback: se nao houver arquivo de baseline serial, usa media de (bloco, p=1) no strong
    if t_serial_strong is None:
        for (exp, est, ch, w, h, it, p), rows in grupos.items():
            if exp == "strong" and est == "bloco" and p == 1:
                t_serial_strong = float(np.mean([float(r["tempo_calculo"]) for r in rows]))
                break

    # Baseline da escalabilidade fraca: um T(n) serial POR RESOLUCAO.
    # E(n,p) = T(n)/(p*T(n,p)) exige o serial no mesmo tamanho n do caso
    # paralelo, entao nao da para usar um unico baseline de 4096x4096.
    t_serial_weak = {}
    for chave, (media, _dp) in baselines_serial.items():
        if chave.startswith("weak"):
            try:
                t_serial_weak[int(chave[4:])] = media
            except ValueError:
                continue

    agregados = []
    for chave in sorted(grupos.keys(), key=lambda x: (x[0], x[1], x[2], x[6])):
        exp, est, chunk, w, h, max_iter, p = chave
        rows = grupos[chave]

        t_calc = np.array([float(r["tempo_calculo"]) for r in rows])
        t_io = np.array([float(r["tempo_io"]) for r in rows])
        t_com_raiz = np.array([float(r["tempo_com_raiz"]) for r in rows])
        ovh = np.array([float(r["overhead_com"]) for r in rows])
        tmax = np.array([float(r.get("t_comp_max", 0.0)) for r in rows])
        tmin = np.array([float(r.get("t_comp_min", 0.0)) for r in rows])

        # Garante o calculo de FBC = (T_max - T_min) / T_max
        fbc_vals = []
        for r in rows:
            tx = float(r.get("t_comp_max", 0.0))
            tn = float(r.get("t_comp_min", 0.0))
            if tx > 0.0:
                fbc_vals.append((tx - tn) / tx)
            else:
                fbc_vals.append(float(r["fator_balanceamento"]))
        fbc = np.array(fbc_vals)

        media_calc = float(np.mean(t_calc))
        dp_calc = float(np.std(t_calc, ddof=1)) if len(t_calc) > 1 else 0.0

        if exp == "strong" and t_serial_strong:
            t_ref = t_serial_strong
            speedup = t_ref / media_calc
            eficiencia = speedup / p
        elif exp == "zoom" and t_serial_zoom:
            t_ref = t_serial_zoom
            speedup = t_ref / media_calc
            eficiencia = speedup / p
        elif exp == "weak" and t_serial_weak.get(w):
            # Mesmas formulas da Aula 03, com T(n) medido na resolucao w x h:
            # S(n,p) = T(n)/T(n,p) e E(n,p) = S(n,p)/p. A escalabilidade fraca
            # se verifica observando se E(n,p) permanece constante.
            t_ref = t_serial_weak[w]
            speedup = t_ref / media_calc
            eficiencia = speedup / p
        else:
            t_ref = media_calc
            speedup = 1.0
            eficiencia = 1.0 / p

        agregados.append({
            "experimento": exp,
            "estrategia": est,
            "chunk": chunk,
            "rotulo": rotulo_estrategia(est, chunk),
            "largura": w,
            "altura": h,
            "max_iter": max_iter,
            "processos": p,
            "reps": len(rows),
            "t_ref_serial": t_ref,
            "tempo_calculo_media": media_calc,
            "tempo_calculo_dp": dp_calc,
            "tempo_io_media": float(np.mean(t_io)),
            "tempo_com_raiz_media": float(np.mean(t_com_raiz)),
            "overhead_com_media": float(np.mean(ovh)),
            "t_comp_max_media": float(np.mean(tmax)),
            "t_comp_min_media": float(np.mean(tmin)),
            "fbc_media": float(np.mean(fbc)),
            "fbc_dp": float(np.std(fbc, ddof=1)) if len(fbc) > 1 else 0.0,
            "speedup": speedup,
            "eficiencia": eficiencia,
        })

    return agregados


def salva_csv_agregado(agregados, caminho):
    if not agregados:
        return
    campos = list(agregados[0].keys())
    with open(caminho, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        for r in agregados:
            w.writerow(r)


def imprime_tabelas(agregados, baselines):
    print("\n" + "=" * 95)
    print("BASELINES SERIAIS DE REFERENCIA")
    print("=" * 95)
    for k, (m, dp) in baselines.items():
        print(f"  {k:<10}: {m:.6f} s (dp = {dp:.6f} s)")

    for exp_nome, titulo in [
        ("strong", "ESCALABILIDADE FORTE (4096x4096, MAX_ITER=1000)"),
        ("zoom", "CASO DE ZOOM - VALE DOS CAVALOS-MARINHOS (4096x4096, MAX_ITER=5000)"),
        ("weak", "ESCALABILIDADE FRACA (CARGA POR PROCESSO CONSTANTE)"),
    ]:
        sub = [r for r in agregados if r["experimento"] == exp_nome]
        if not sub:
            continue
        print("\n" + "=" * 95)
        print(titulo)
        print("=" * 95)
        cab = (
            f"{'Estrategia':<12} {'p':>3} {'Res':>11} {'T_calc(s)':>10} {'DP(s)':>8} "
            f"{'Speedup':>8} {'Efic.':>7} {'T_max(s)':>9} {'T_min(s)':>9} {'FBC':>7} "
            f"{'T_MPI_r0':>9} {'Ovh(s)':>8}"
        )
        print(cab)
        print("-" * 95)
        for r in sub:
            res_str = f"{r['largura']}x{r['altura']}"
            print(
                f"{r['rotulo']:<12} {r['processos']:>3d} {res_str:>11} "
                f"{r['tempo_calculo_media']:>10.4f} {r['tempo_calculo_dp']:>8.4f} "
                f"{r['speedup']:>8.2f} {r['eficiencia']:>7.3f} "
                f"{r['t_comp_max_media']:>9.4f} {r['t_comp_min_media']:>9.4f} "
                f"{r['fbc_media']:>7.4f} {r['tempo_com_raiz_media']:>9.4f} "
                f"{r['overhead_com_media']:>8.4f}"
            )


def filtra_omp(omp_rows, experimento, rotulo):
    """
    Seleciona as linhas da Etapa 1 de um experimento e de uma politica.

    O CSV agregado da Etapa 1 usa um esquema proprio, com a coluna do
    experimento chamada 'bloco', a politica em 'politica' e o chunk gravado
    como float, por exemplo '16.000000'. Esta funcao traduz esse esquema para
    o rotulo 'politica,chunk' usado nas comparacoes.

    O schedule 'static' sem chunk explicito aparece na Etapa 1 com a coluna
    chunk vazia, e corresponde ao rotulo 'static,0'.
    """
    selecionadas = []
    for r in omp_rows:
        if r.get("bloco") != experimento:
            continue
        bruto = (r.get("chunk") or "").strip()
        try:
            chunk = int(float(bruto)) if bruto else 0
        except ValueError:
            continue
        if f"{r.get('politica')},{chunk}" == rotulo:
            selecionadas.append(r)
    return sorted(selecionadas, key=lambda x: int(x["threads"]))


def plota_graficos(agregados):
    estilo = {
        "bloco":      {"color": "#1f77b4", "marker": "o", "ls": "-",  "label": "bloco (estático)"},
        "ciclico,1":  {"color": "#ff7f0e", "marker": "s", "ls": "--", "label": "cíclico (chunk=1)"},
        "ciclico,16": {"color": "#2ca02c", "marker": "^", "ls": "-",  "label": "cíclico (chunk=16)"},
        "mestre,1":   {"color": "#d62728", "marker": "v", "ls": "--", "label": "mestre-trabalhador (chunk=1)"},
        "mestre,16":  {"color": "#9467bd", "marker": "D", "ls": "-",  "label": "mestre-trabalhador (chunk=16)"},
    }

    strong = [r for r in agregados if r["experimento"] == "strong"]
    if strong:
        # 1. Tempo Strong
        fig, ax = plt.subplots(figsize=(7, 4.5))
        for rot, cfg in estilo.items():
            pts = sorted([r for r in strong if r["rotulo"] == rot], key=lambda x: x["processos"])
            if not pts:
                continue
            xs = [r["processos"] for r in pts]
            ys = [r["tempo_calculo_media"] for r in pts]
            es = [r["tempo_calculo_dp"] for r in pts]
            ax.errorbar(xs, ys, yerr=es, capsize=3, **cfg)
        ax.set_title("Escalabilidade Forte MPI — Tempo de Execução (4096×4096, MAX_ITER=1000)")
        ax.set_xlabel("Número de processos MPI (p)")
        ax.set_ylabel("Tempo de cálculo + coleta (s)")
        ax.set_xticks([1, 2, 4, 8, 16])
        ax.grid(True)
        ax.legend()
        fig.tight_layout()
        fig.savefig("fig_mpi_strong_tempo.png")
        plt.close(fig)

        # 2. Speedup Strong
        fig, ax = plt.subplots(figsize=(7, 4.5))
        ax.plot([1, 2, 4, 8, 16], [1, 2, 4, 8, 16], "k:", label="Speedup linear ideal S(n,p) = p")
        for rot, cfg in estilo.items():
            pts = sorted([r for r in strong if r["rotulo"] == rot], key=lambda x: x["processos"])
            if not pts:
                continue
            xs = [r["processos"] for r in pts]
            ys = [r["speedup"] for r in pts]
            ax.plot(xs, ys, **cfg)
        ax.set_title("Escalabilidade Forte MPI — Speedup S(n,p) (4096×4096, MAX_ITER=1000)")
        ax.set_xlabel("Número de processos MPI (p)")
        ax.set_ylabel("Speedup S(n,p) = T(n) / T(n,p)")
        ax.set_xticks([1, 2, 4, 8, 16])
        ax.grid(True)
        ax.legend()
        fig.tight_layout()
        fig.savefig("fig_mpi_strong_speedup.png")
        plt.close(fig)

        # 3. Eficiencia Strong
        fig, ax = plt.subplots(figsize=(7, 4.5))
        ax.axhline(1.0, color="k", ls=":", label="Eficiência linear ideal E(n,p) = 1")
        for rot, cfg in estilo.items():
            pts = sorted([r for r in strong if r["rotulo"] == rot], key=lambda x: x["processos"])
            if not pts:
                continue
            xs = [r["processos"] for r in pts]
            ys = [r["eficiencia"] for r in pts]
            ax.plot(xs, ys, **cfg)
        ax.set_title("Escalabilidade Forte MPI — Eficiência E(n,p) (4096×4096, MAX_ITER=1000)")
        ax.set_xlabel("Número de processos MPI (p)")
        ax.set_ylabel("Eficiência E(n,p) = S(n,p) / p")
        ax.set_xticks([1, 2, 4, 8, 16])
        ax.grid(True)
        ax.legend()
        fig.tight_layout()
        fig.savefig("fig_mpi_strong_eficiencia.png")
        plt.close(fig)

        # 4. FBC Strong
        fig, ax = plt.subplots(figsize=(7, 4.5))
        for rot, cfg in estilo.items():
            pts = sorted([r for r in strong if r["rotulo"] == rot and r["processos"] >= 2], key=lambda x: x["processos"])
            if not pts:
                continue
            xs = [r["processos"] for r in pts]
            ys = [r["fbc_media"] for r in pts]
            ax.plot(xs, ys, **cfg)
        ax.set_title("Fator de Balanceamento de Carga no Input Padrão — FBC = (T_max - T_min) / T_max")
        ax.set_xlabel("Número de processos MPI (p)")
        ax.set_ylabel("FBC (0 = balanceamento perfeito)")
        ax.set_xticks([2, 4, 8, 16])
        ax.set_ylim(-0.02, 1.05)
        ax.grid(True)
        ax.legend()
        fig.tight_layout()
        fig.savefig("fig_mpi_strong_fbc.png")
        plt.close(fig)

        # 5. Custo de Comunicacao / Overhead Strong
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.3))
        for rot, cfg in estilo.items():
            pts = sorted([r for r in strong if r["rotulo"] == rot and r["processos"] >= 2], key=lambda x: x["processos"])
            if not pts:
                continue
            xs = [r["processos"] for r in pts]
            y_ovh = [r["overhead_com_media"] for r in pts]
            y_r0 = [r["tempo_com_raiz_media"] for r in pts]
            ax1.plot(xs, y_ovh, **cfg)
            ax2.plot(xs, y_r0, **cfg)
        ax1.set_title("Overhead de Comunicação/Sincronização (T_calc - T_max)")
        ax1.set_xlabel("Número de processos MPI (p)")
        ax1.set_ylabel("Tempo (s)")
        ax1.set_xticks([2, 4, 8, 16])
        ax1.grid(True)
        ax1.legend()

        ax2.set_title("Tempo Acumulado em Chamadas MPI na Raiz (rank 0)")
        ax2.set_xlabel("Número de processos MPI (p)")
        ax2.set_ylabel("Tempo em MPI no rank 0 (s)")
        ax2.set_xticks([2, 4, 8, 16])
        ax2.grid(True)
        ax2.legend()
        fig.tight_layout()
        fig.savefig("fig_mpi_comunicacao.png")
        plt.close(fig)

    # 6. Caso de Zoom (Vale dos Cavalos-Marinhos)
    zoom = [r for r in agregados if r["experimento"] == "zoom"]
    if zoom:
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.3))
        for rot, cfg in estilo.items():
            pts = sorted([r for r in zoom if r["rotulo"] == rot], key=lambda x: x["processos"])
            if not pts:
                continue
            xs = [r["processos"] for r in pts]
            yt = [r["tempo_calculo_media"] for r in pts]
            yf = [r["fbc_media"] for r in pts]
            ax1.plot(xs, yt, **cfg)
            ax2.plot(xs, yf, **cfg)
        ax1.set_title("Vale dos Cavalos-Marinhos — Tempo de Execução")
        ax1.set_xlabel("Número de processos MPI (p)")
        ax1.set_ylabel("Tempo de cálculo + coleta (s)")
        ax1.set_xticks([2, 4, 8, 16])
        ax1.grid(True)
        ax1.legend()

        ax2.set_title("Vale dos Cavalos-Marinhos — FBC = (T_max - T_min) / T_max")
        ax2.set_xlabel("Número de processos MPI (p)")
        ax2.set_ylabel("FBC (0 = perfeito, 1 = desbalanceado)")
        ax2.set_xticks([2, 4, 8, 16])
        ax2.set_ylim(-0.02, 1.05)
        ax2.grid(True)
        ax2.legend()
        fig.tight_layout()
        fig.savefig("fig_mpi_zoom_fbc_tempo.png")
        plt.close(fig)

    # 7. Escalabilidade Fraca
    weak = [r for r in agregados if r["experimento"] == "weak"]
    if weak:
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.3))
        for rot, cfg in estilo.items():
            pts = sorted([r for r in weak if r["rotulo"] == rot], key=lambda x: x["processos"])
            if not pts:
                continue
            xs = [r["processos"] for r in pts]
            yt = [r["tempo_calculo_media"] for r in pts]
            ye = [r["eficiencia"] for r in pts]
            ax1.plot(xs, yt, **cfg)
            ax2.plot(xs, ye, **cfg)
        ax1.set_title("Escalabilidade Fraca MPI — Tempo de Execução (N = 4096·√p)")
        ax1.set_xlabel("Número de processos MPI (p)")
        ax1.set_ylabel("Tempo de cálculo + coleta (s)")
        ax1.set_xticks([1, 2, 4, 8, 16])
        ax1.grid(True)
        ax1.legend()

        ax2.set_title("Escalabilidade Fraca MPI — Eficiência E(n,p) = T(n) / (p·T(n,p))")
        ax2.set_xlabel("Número de processos MPI (p)")
        ax2.set_ylabel("Eficiência E(n,p), constante indica escalabilidade")
        ax2.set_xticks([1, 2, 4, 8, 16])
        ax2.axhline(1.0, color="k", ls=":")
        ax2.grid(True)
        ax2.legend()
        fig.tight_layout()
        fig.savefig("fig_mpi_weak_tempo.png")
        plt.close(fig)

    # 8. Comparacao MPI vs OpenMP (se resultados_agregados.csv da Etapa 1 existir)
    if os.path.exists(OMP_AGG_IN) and strong:
        omp_rows = []
        with open(OMP_AGG_IN, "r", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                omp_rows.append(r)

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5))
        pares_comp = [
            ("bloco",      "static,0",   "#1f77b4", "o", "Bloco / static"),
            ("ciclico,16", "static,16",  "#2ca02c", "^", "Cíclico,16 / static,16"),
            ("mestre,16",  "dynamic,16", "#9467bd", "D", "Mestre,16 / dynamic,16"),
        ]
        for rot_mpi, rot_omp, cor, mk, nome in pares_comp:
            pts_m = sorted([r for r in strong if r["rotulo"] == rot_mpi], key=lambda x: x["processos"])
            if pts_m:
                ax1.plot([r["processos"] for r in pts_m], [r["speedup"] for r in pts_m],
                         color=cor, marker=mk, ls="-", label=f"MPI {nome.split('/')[0].strip()}")
            pts_o = filtra_omp(omp_rows, "strong", rot_omp)
            if pts_o:
                # Usa o speedup publicado da Etapa 1, calculado com o baseline
                # serial contemporaneo a ela. Misturar o T(n) de hoje com os
                # tempos paralelos de la daria um speedup sem significado.
                ax1.plot([int(r["threads"]) for r in pts_o],
                         [float(r["speedup"]) for r in pts_o],
                         color=cor, marker=mk, ls="--", alpha=0.8, label=f"OpenMP {nome.split('/')[1].strip()}")

        ax1.set_title("Input Padrão (4096²) — Speedup MPI vs. OpenMP")
        ax1.set_xlabel("Processos MPI / Threads OpenMP (p)")
        ax1.set_ylabel("Speedup S(n,p)")
        ax1.set_xticks([1, 2, 4, 8, 16])
        ax1.grid(True)
        ax1.legend(fontsize=7.5)

        if zoom:
            for rot_mpi, rot_omp, cor, mk, nome in pares_comp:
                pts_m = sorted([r for r in zoom if r["rotulo"] == rot_mpi], key=lambda x: x["processos"])
                if pts_m:
                    ax2.plot([r["processos"] for r in pts_m], [r["speedup"] for r in pts_m],
                             color=cor, marker=mk, ls="-", label=f"MPI {nome.split('/')[0].strip()}")
                pts_o = filtra_omp(omp_rows, "zoom", rot_omp)
                if pts_o:
                    ax2.plot([int(r["threads"]) for r in pts_o],
                             [float(r["speedup"]) for r in pts_o],
                             color=cor, marker=mk, ls="--", alpha=0.8, label=f"OpenMP {nome.split('/')[1].strip()}")

            ax2.set_title("Vale dos Cavalos-Marinhos (Zoom) — Speedup MPI vs. OpenMP")
            ax2.set_xlabel("Processos MPI / Threads OpenMP (p)")
            ax2.set_ylabel("Speedup S(n,p)")
            ax2.set_xticks([2, 4, 8, 16])
            ax2.grid(True)
            ax2.legend(fontsize=7.5)

        fig.tight_layout()
        fig.savefig("fig_mpi_vs_openmp.png")
        plt.close(fig)


def main():
    baselines = carrega_serial(SERIAL_IN)
    grupos = carrega_mpi_csv(CSV_IN)
    agregados = agrega_resultados(grupos, baselines)
    salva_csv_agregado(agregados, CSV_AGG_OUT)
    imprime_tabelas(agregados, baselines)
    plota_graficos(agregados)
    print(f"\nPos-processamento concluido! Arquivo '{CSV_AGG_OUT}' e graficos '.png' gerados.")


if __name__ == "__main__":
    main()