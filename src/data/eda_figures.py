"""Figuras científicas descritivas, sem transformação dos dados de origem."""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from eda import UNITS


def render(df,time,monthly,seasonal,categories,corr,pairs,output):
    plt.rcParams.update({"font.size":10,"axes.spines.top":False,"axes.spines.right":False,
                         "figure.facecolor":"white","axes.titleweight":"bold","savefig.dpi":140})
    def save(fig,name):
        fig.savefig(output/name,bbox_inches="tight")
        plt.close(fig)
    cols=[col for col in df.select_dtypes(include="number") if col not in ["weather_code","is_day","wind_direction_10m","rain","precipitation"]]
    for part,start in enumerate(range(0,len(cols),6),1):
        fig,axes=plt.subplots(3,2,figsize=(12,11),layout="constrained")
        for ax,col in zip(axes.flat,cols[start:start+6]):
            ax.hist(df[col].dropna(),bins=40,color="#267b91",edgecolor="white",linewidth=.3)
            ax.set(title=col,xlabel=UNITS[col],ylabel="Registros horários")
        for ax in list(axes.flat)[len(cols[start:start+6]):]:ax.set_visible(False)
        fig.suptitle(f"Distribuições meteorológicas — painel {part}\nTodo o período; unidades conforme README original")
        save(fig,f"histograms_{part}.png")
    for col in ["rain","precipitation"]:
        fig,axes=plt.subplots(1,2,figsize=(11,4.4),layout="constrained")
        for ax,values,title in [(axes[0],df[col],"Todos os registros"),(axes[1],df.loc[df[col]>0,col],"Apenas valores positivos")]:
            ax.hist(values,bins=50,color="#267b91"); ax.set_yscale("log")
            ax.set(title=title,xlabel=f"{col} (mm por intervalo horário)",ylabel="Registros (escala log)")
        fig.suptitle(f"{col}: massa em zero e cauda positiva — sem limiar de target")
        save(fig,f"{col}_distribution.png")
    x=pd.to_datetime(monthly.index)
    fig,axes=plt.subplots(5,1,figsize=(12,14),sharex=True,layout="constrained")
    for ax,col,label in zip(axes,["rows","temperature_mean","precipitation_mm","positive_fraction","coverage"],
                           ["Registros/mês","Temperatura média (°C)","Precipitação (mm/mês)","Horas com >0 mm (%)","Com imagem (%)"]):
        multiplier=100 if col in ["positive_fraction","coverage"] else 1
        ax.plot(x,monthly[col]*multiplier,color="#267b91",marker=".",linewidth=1)
        ax.set(ylabel=label); ax.grid(alpha=.2)
    axes[-1].set_xlabel("Mês de referência — America/Sao_Paulo")
    fig.suptitle("Evolução mensal — janeiro/2020 a setembro/2026\nAcumulados agrupados pelo timestamp da linha; 2026 é parcial")
    save(fig,"monthly_evolution.png")
    fig,axes=plt.subplots(3,1,figsize=(10,9),sharex=True,layout="constrained")
    for ax,col,label in zip(axes,["temperature_mean","precipitation_month_mean_mm","positive_fraction"],
                            ["Temperatura média (°C)","Média dos totais mensais (mm)","Fração de horas >0 mm"]):
        ax.plot(seasonal.index,seasonal[col],marker="o",color="#267b91");ax.set(ylabel=label);ax.grid(alpha=.2)
    axes[-1].set(xticks=range(1,13),xlabel="Mês do calendário local")
    fig.suptitle("Sazonalidade descritiva\nJan–set: 7 ocorrências; out–dez: 6. Não é uma normal climatológica")
    save(fig,"seasonality.png")
    fig,axes=plt.subplots(2,2,figsize=(12,9),layout="constrained")
    years=sorted(time.dt.year.unique())
    for ax,col in zip(axes.flat,["temperature_2m","relative_humidity_2m","wind_speed_10m","precipitation"]):
        ax.boxplot([df.loc[time.dt.year==year,col] for year in years],tick_labels=years,
                   flierprops={"markersize":2,"alpha":.2},whis=1.5)
        ax.set(title=col,xlabel="Ano (2026: jan–set)",ylabel=UNITS[col])
    fig.suptitle("Distribuição anual e extremos — boxplots de 1,5 IQR\nChuva tem quartis zero: pontos fora da caixa não implicam erro")
    save(fig,"yearly_boxplots.png")
    fig,ax=plt.subplots(figsize=(13,11),layout="constrained")
    im=ax.imshow(corr,vmin=-1,vmax=1,cmap="RdBu_r")
    ax.set_xticks(range(len(corr)),corr.columns,rotation=70,ha="right",fontsize=8)
    ax.set_yticks(range(len(corr)),corr.index,fontsize=8)
    for i in range(len(corr)):
        for j in range(len(corr)):
            val=corr.iloc[i,j]; ax.text(j,i,f"{val:.2f}",ha="center",va="center",fontsize=6,color="white" if abs(val)>.65 else "black")
    fig.colorbar(im,ax=ax,label="Correlação de Pearson (adimensional)",shrink=.7)
    ax.set_title("Associações contemporâneas exploratórias\nSem weather_code, direção circular ou is_day; não seleciona features",pad=15)
    save(fig,"correlation_exploratory.png")
    fig,axes=plt.subplots(1,3,figsize=(14,4.5),layout="constrained")
    axes[0].bar(categories.index.astype(str),categories.rows,color="#267b91")
    axes[0].set(title="weather_code: frequências",xlabel="Código categórico",ylabel="Registros");axes[0].tick_params(axis="x",rotation=45)
    axes[1].bar(categories.index.astype(str),categories.positive_fraction*100,color="#b4662c")
    axes[1].set(title="Precipitação >0 por código",xlabel="Código categórico",ylabel="Percentual dentro do código");axes[1].tick_params(axis="x",rotation=45)
    counts=df.is_day.value_counts().reindex([0,1],fill_value=0)
    axes[2].bar(["Noite (0)","Dia (1)"],counts,color="#267b91");axes[2].set(title="is_day",ylabel="Registros")
    save(fig,"special_variables.png")
    fig,ax=plt.subplots(figsize=(6.5,6.5),subplot_kw={"projection":"polar"},layout="constrained")
    angle=np.deg2rad(df.loc[df.wind_speed_10m>0,"wind_direction_10m"]%360)
    counts,bins=np.histogram(angle,bins=np.linspace(0,2*np.pi,17))
    ax.bar((bins[:-1]+bins[1:])/2,counts,width=2*np.pi/16*.9,color="#267b91")
    ax.set_theta_zero_location("N");ax.set_theta_direction(-1)
    ax.set_title("Direção do vento (graus)\nContagem radial; vento zero excluído apenas deste gráfico",pad=22)
    save(fig,"wind_direction.png")
    fig,axes=plt.subplots(1,2,figsize=(12,4.5),layout="constrained")
    for satellite,group in pairs.groupby("satellite"):
        axes[0].scatter(pd.to_datetime(group.csv_utc,utc=True),group.delta_seconds/60,s=14,alpha=.7,label=satellite)
    axes[0].axhline(0,color="black",linestyle="--",linewidth=.8)
    axes[0].set(xlabel="Referência do CSV (UTC)",ylabel="Captura − referência (min)",title="Pareamentos da amostra, incluindo reusos");axes[0].legend()
    axes[1].hist(pairs.delta_seconds/60,bins=35,color="#267b91")
    axes[1].set(xlabel="Captura − referência (min)",ylabel="Pares examinados",title="Amostra estratificada + casos dirigidos")
    fig.suptitle("Disponibilidade temporal: valor positivo significa captura posterior\nAmostra não estima a frequência populacional")
    save(fig,"goes_temporal_offsets.png")
