"""
Pós-processamento do Benchmark Mandelbrot (Etapa 1 - OpenMP)
DEC107 - Processamento Paralelo

Lê resultados.csv, agrega repetições (média + desvio padrão),
calcula Speedup/Eficiência (exceto no bloco weak) e gera 5 gráficos
com barras de erro.

Requisitos: pandas, matplotlib, numpy
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# ------------------------------------------------------------------
# 1. Leitura
# ------------------------------------------------------------------
CSV = "resultados.csv"
df = pd.read_csv(CSV, comment="#", skip_blank_lines=True)
df["chunk"] = df["chunk"].replace({"NA": np.nan})

print(f"Linhas lidas: {len(df)}")
print(f"Blocos: {df['bloco'].unique()}")
print(f"Políticas: {df['politica'].unique()}")

# ------------------------------------------------------------------
# 2. Baselines seriais (lê do arquivo, com fallback)
# ------------------------------------------------------------------
def carrega_baselines(caminho="serial_baselines.txt"):
    base = {"strong": 7.61, "zoom": 3.30}  # fallback
    try:
        with open(caminho) as f:
            for linha in f:
                linha = linha.strip()
                if "=" in linha and not linha.startswith("#"):
                    k, v = linha.split("=", 1)
                    try:
                        base[k.strip()] = float(v)
                    except ValueError:
                        pass
    except FileNotFoundError:
        print(f"Aviso: {caminho} não encontrado; usando fallback.")
    return base

BASE = carrega_baselines()
BASE["weak"] = BASE["strong"]

# ------------------------------------------------------------------
# 3. Agregação
# ------------------------------------------------------------------
grupo = ["bloco", "politica", "chunk", "threads", "largura", "altura", "max_iter"]
agg = df.groupby(grupo, dropna=False).agg(
    tempo_media=("tempo_calculo", "mean"),
    tempo_std=("tempo_calculo", "std"),
    fator_media=("fator_balanceamento", "mean"),
    fator_std=("fator_balanceamento", "std"),
    n_reps=("rep", "count"),
).reset_index()

agg["speedup"] = agg.apply(
    lambda r: BASE.get(r["bloco"], np.nan) / r["tempo_media"], axis=1)
agg["eficiencia"] = agg["speedup"] / agg["threads"]

mask_weak = agg["bloco"] == "weak"
agg.loc[mask_weak, ["speedup", "eficiencia"]] = np.nan

agg.to_csv("resultados_agregados.csv", index=False, float_format="%.6f")
print("\nAgregado salvo em: resultados_agregados.csv")
print(agg[["bloco", "politica", "chunk", "threads",
           "tempo_media", "fator_media", "speedup", "eficiencia"]].to_string(index=False))

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def melhor_chunk(sub):
    """Para cada política, retorna a linha de menor tempo por nº de threads."""
    return sub.loc[sub.groupby("threads")["tempo_media"].idxmin()]

plt.rcParams.update({"font.size": 10, "figure.dpi": 120})

strong = agg[agg["bloco"] == "strong"]
zoom = agg[agg["bloco"] == "zoom"]
weak = agg[agg["bloco"] == "weak"]
tmax = strong["threads"].max()

# ------------------------------------------------------------------
# 4.1 Strong: tempo × threads (melhor chunk por política) + erro
# ------------------------------------------------------------------
plt.figure(figsize=(8, 5))
for pol in strong["politica"].unique():
    sub = melhor_chunk(strong[strong["politica"] == pol])
    plt.errorbar(sub["threads"], sub["tempo_media"],
                 yerr=sub["tempo_std"], marker="o", capsize=3, label=pol)
plt.xlabel("Número de threads")
plt.ylabel("Tempo de cálculo (s)")
plt.title("Strong scaling — tempo × threads (melhor chunk por política)")
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig("fig_strong_tempo.png")
plt.close()

# ------------------------------------------------------------------
# 4.2 Strong: speedup × threads (melhor chunk) + erro propagado
# ------------------------------------------------------------------
plt.figure(figsize=(8, 5))
for pol in strong["politica"].unique():
    sub = melhor_chunk(strong[strong["politica"] == pol])
    err = sub["speedup"] * (sub["tempo_std"] / sub["tempo_media"])
    plt.errorbar(sub["threads"], sub["speedup"],
                 yerr=err, marker="o", capsize=3, label=pol)
plt.plot([1, tmax], [1, tmax], "--", color="gray", label="ideal (linear)")
plt.xlabel("Número de threads")
plt.ylabel("Speedup")
plt.title("Strong scaling — speedup × threads (melhor chunk por política)")
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig("fig_strong_speedup.png")
plt.close()

# ------------------------------------------------------------------
# 4.3 Strong: eficiência × threads (melhor chunk) + erro
# ------------------------------------------------------------------
plt.figure(figsize=(8, 5))
for pol in strong["politica"].unique():
    sub = melhor_chunk(strong[strong["politica"] == pol])
    err = sub["eficiencia"] * (sub["tempo_std"] / sub["tempo_media"])
    plt.errorbar(sub["threads"], sub["eficiencia"],
                 yerr=err, marker="o", capsize=3, label=pol)
plt.axhline(1.0, color="gray", ls="--", label="ideal (1.0)")
plt.xlabel("Número de threads")
plt.ylabel("Eficiência (speedup/threads)")
plt.ylim(0, 1.15)
plt.title("Strong scaling — eficiência × threads (melhor chunk por política)")
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig("fig_strong_eficiencia.png")
plt.close()

# ------------------------------------------------------------------
# 4.4 Strong: fator de balanceamento × threads (menor fator por política)
# ------------------------------------------------------------------
plt.figure(figsize=(8, 5))
for pol in strong["politica"].unique():
    sub = strong[strong["politica"] == pol]
    idx = sub.groupby("threads")["fator_media"].idxmin()
    melhores = sub.loc[idx]
    plt.errorbar(melhores["threads"], melhores["fator_media"],
                 yerr=melhores["fator_std"], marker="o", capsize=3, label=pol)
plt.axhline(1.0, color="gray", ls="--", lw=1, label="balanceamento perfeito (1,0)")
plt.xlabel("Número de threads")
plt.ylabel("Fator de balanceamento (max/média)")
plt.title("Strong scaling — fator de balanceamento × threads (melhor chunk por política)")
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig("fig_strong_fator.png")
plt.close()

# ------------------------------------------------------------------
# 4.5 Zoom: fator de balanceamento por política/chunk (16 threads) + erro
# ------------------------------------------------------------------
zoom16 = zoom[zoom["threads"] == 16]
rotulos = zoom16.apply(
    lambda r: f"{r['politica']},{r['chunk'] if pd.notna(r['chunk']) else 'def'}",
    axis=1)
plt.figure(figsize=(9, 5))
plt.bar(rotulos, zoom16["fator_media"], yerr=zoom16["fator_std"], capsize=3)
plt.axhline(1.0, color="red", ls="--", lw=1, label="balanceamento perfeito")
plt.xticks(rotation=45, ha="right")
plt.ylabel("Fator de balanceamento (max/média)")
plt.title("Caso de desbalanceamento acentuado (zoom, 16 threads)")
plt.legend()
plt.tight_layout()
plt.savefig("fig_zoom_fator.png")
plt.close()

# ------------------------------------------------------------------
# 4.6 Weak: tempo × threads (trabalho/thread ~constante) + erro
# ------------------------------------------------------------------
plt.figure(figsize=(8, 5))
plt.errorbar(weak["threads"], weak["tempo_media"],
             yerr=weak["tempo_std"], marker="o", capsize=3, color="darkblue")
for _, r in weak.iterrows():
    plt.annotate(f"{int(r['largura'])}²", (r["threads"], r["tempo_media"]),
                 textcoords="offset points", xytext=(0, 10), ha="center")
plt.xlabel("Número de threads (resolução cresce junto)")
plt.ylabel("Tempo de cálculo (s)")
plt.title("Weak scaling — trabalho por thread ~constante")
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig("fig_weak_tempo.png")
plt.close()

print("\nGráficos gerados: fig_strong_tempo.png, fig_strong_speedup.png, "
      "fig_strong_eficiencia.png, fig_strong_fator.png, "
      "fig_zoom_fator.png, fig_weak_tempo.png")