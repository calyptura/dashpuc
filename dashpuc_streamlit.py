import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
import io

# Configuração da página
st.set_page_config(
    page_title="Dashboard de Detecções de Aves",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Aplicar tema escuro via CSS
st.markdown("""
    <style>
    .stApp {
        background-color: #1e1e2f;
        color: white;
    }
    .stSelectbox, .stMultiSelect {
        background-color: #2c2c44;
    }
    .stProgress .st-bo {
        background-color: #2c2c44;
    }
    </style>
    """, unsafe_allow_html=True)


# Funções auxiliares para criar layouts de gráficos
def create_graph_layout(title="", show_legend=True):
    return dict(
        margin={"r": 10, "t": 10, "l": 10, "b": 10},
        paper_bgcolor="#1e1e2f",
        plot_bgcolor="#1e1e2f",
        font_color="white",
        xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
        yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
        showlegend=show_legend,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ) if show_legend else {}
    )


# Upload de arquivos
st.title("Dashboard de Detecções de Aves")

# Criar três colunas para os uploaders
col1, col2, col3 = st.columns(3)

with col1:
    detection_file = st.file_uploader("Carregar arquivo de detecções", type=['csv'])

with col2:
    weather_file = st.file_uploader("Carregar arquivo de dados climáticos", type=['csv'])

with col3:
    moon_file = st.file_uploader("Carregar arquivo de dados lunares", type=['csv'])

# Verificar se todos os arquivos foram carregados
if not all([detection_file, weather_file, moon_file]):
    st.warning("Por favor, carregue todos os arquivos CSV necessários para visualizar o dashboard.")
    st.stop()

# Processar os dados
try:
    # Processar dados de detecção
    data = pd.read_csv(detection_file)
    data['Timestamp'] = pd.to_datetime(data['Timestamp'], utc=True)
    data['Timestamp_10min'] = data['Timestamp'].dt.floor('10min')
    data['Timestamp_1min'] = data['Timestamp'].dt.floor('1min')
    data['Hour'] = data['Timestamp'].dt.hour
    data['Scientific Name'] = data['Scientific Name'].astype(str)

    # Processar dados climáticos
    weather_data = pd.read_csv(weather_file, skiprows=2)
    weather_data['time'] = pd.to_datetime(weather_data['time'], utc=True)

    # Processar dados lunares
    moon_data = pd.read_csv(moon_file)
    moon_data['date'] = pd.to_datetime(moon_data['date'], utc=True)

except Exception as e:
    st.error(f"Erro ao processar os arquivos: {str(e)}")
    st.stop()

st.write(f"Última atualização: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

# Sidebar com filtros
with st.sidebar:
    st.header("Filtros")

    # Inicializar valores no session_state se não existirem
    if 'start_date' not in st.session_state:
        st.session_state.start_date = data['Timestamp'].min().date()
    if 'end_date' not in st.session_state:
        st.session_state.end_date = data['Timestamp'].max().date()


    # Funções para atualizar as datas
    def set_all_period():
        st.session_state.start_date = data['Timestamp'].min().date()
        st.session_state.end_date = data['Timestamp'].max().date()


    def set_last_day():
        st.session_state.end_date = data['Timestamp'].max().date()
        st.session_state.start_date = (st.session_state.end_date - timedelta(days=1))


    def set_last_week():
        st.session_state.end_date = data['Timestamp'].max().date()
        st.session_state.start_date = (st.session_state.end_date - timedelta(days=7))


    def set_last_month():
        st.session_state.end_date = data['Timestamp'].max().date()
        st.session_state.start_date = (st.session_state.end_date - timedelta(days=30))


    # Botões de período
    col1, col2 = st.columns(2)
    with col1:
        st.button("Todo o Período", on_click=set_all_period)
    with col2:
        st.button("Último Dia", on_click=set_last_day)

    col3, col4 = st.columns(2)
    with col3:
        st.button("Última Semana", on_click=set_last_week)
    with col4:
        st.button("Último Mês", on_click=set_last_month)

    # Date picker
    date_range = st.date_input(
        "Selecione o período",
        value=(st.session_state.start_date, st.session_state.end_date),
        min_value=data['Timestamp'].min().date(),
        max_value=data['Timestamp'].max().date(),
        key='date_picker'
    )

    # Atualizar session_state quando o date_picker mudar
    if len(date_range) == 2:
        st.session_state.start_date = date_range[0]
        st.session_state.end_date = date_range[1]

    # Switches
    filter_common_species = st.checkbox("Apenas espécies com mais de 100 registros")
    filter_1min = st.checkbox("Considerar apenas primeiro registro a cada minuto")
    filter_10min = st.checkbox("Considerar apenas primeiro registro a cada 10 minutos")

    # Dropdown de espécies
    species_list = data['Scientific Name'].unique()
    if filter_common_species:
        species_counts = data['Scientific Name'].value_counts()
        species_list = species_counts[species_counts >= 100].index

    selected_species = st.multiselect(
        "Selecione as espécies",
        options=sorted(species_list)
    )

    # Slider de confiança
    confidence_threshold = st.slider(
        "Filtro de Confiança",
        min_value=0.0,
        max_value=1.0,
        value=0.0,
        step=0.1
    )

# Filtrar dados
filtered_data = data.copy()

if filter_1min:
    filtered_data = filtered_data.sort_values('Confidence', ascending=False).groupby(
        ['Scientific Name', 'Timestamp_1min']
    ).first().reset_index()
elif filter_10min:
    filtered_data = filtered_data.sort_values('Confidence', ascending=False).groupby(
        ['Scientific Name', 'Timestamp_10min']
    ).first().reset_index()

if filter_common_species:
    species_counts = filtered_data['Scientific Name'].value_counts()
    common_species = species_counts[species_counts >= 100].index
    filtered_data = filtered_data[filtered_data['Scientific Name'].isin(common_species)]

# Aplicar filtro de data usando session_state
filtered_data = filtered_data[
    (filtered_data['Timestamp'].dt.date >= st.session_state.start_date) &
    (filtered_data['Timestamp'].dt.date <= st.session_state.end_date)
    ]

if selected_species:
    filtered_data = filtered_data[filtered_data['Scientific Name'].isin(selected_species)]

if confidence_threshold > 0:
    filtered_data = filtered_data[filtered_data['Confidence'] >= confidence_threshold]

# Métricas principais
col1, col2 = st.columns(2)
with col1:
    st.metric("Espécies Únicas", filtered_data['Scientific Name'].nunique())
with col2:
    st.metric("Total de Registros", len(filtered_data))

# Indicadores de qualidade
mean_confidence = filtered_data['Confidence'].mean()
quality_score = int(mean_confidence * 100)
col1, col2 = st.columns(2)
with col1:
    st.subheader("Indicadores de Qualidade")
    st.progress(quality_score / 100)
    st.write(f"Média de Confiança: {mean_confidence:.2%}")
    st.write(f"Registros de Alta Confiança: {(filtered_data['Confidence'] > 0.8).mean():.2%}")

with col2:
    st.subheader("Últimos Lifers")
    first_occurrences = filtered_data.sort_values('Timestamp').groupby(
        'Scientific Name'
    ).first().reset_index()
    last_lifers = first_occurrences.sort_values('Timestamp', ascending=False).head(5)
    for _, row in last_lifers.iterrows():
        st.write(f"**{row['Scientific Name']}**")
        st.write(f"_{row['Timestamp'].strftime('%d/%m/%Y %H:%M')}_")

# Top 20 Espécies
st.subheader("Top 20 Espécies")
species_counts = filtered_data['Scientific Name'].value_counts().head(20).reset_index()
species_counts.columns = ['Scientific Name', 'Count']

fig_top_20 = px.bar(
    species_counts,
    x='Count',
    y='Scientific Name',
    orientation='h',
    color='Count',
    color_continuous_scale='Viridis'
)
fig_top_20.update_layout(create_graph_layout())
st.plotly_chart(fig_top_20, use_container_width=True)

# Gráficos temporais
col1, col2 = st.columns(2)

with col1:
    st.subheader("Registros ao Longo do Tempo")
    temporal_data = filtered_data.groupby(
        filtered_data['Timestamp'].dt.date
    ).agg({
        'Scientific Name': 'count',
        'Confidence': 'mean'
    }).reset_index()

    fig_temporal = go.Figure()
    fig_temporal.add_trace(
        go.Scatter(
            x=temporal_data['Timestamp'],
            y=temporal_data['Scientific Name'],
            mode='lines',
            line=dict(color='#00ff00', width=2, shape='spline'),
            fill='tozeroy',
            fillcolor='rgba(0,255,0,0.1)'
        )
    )
    fig_temporal.update_layout(create_graph_layout())
    st.plotly_chart(fig_temporal, use_container_width=True)

with col2:
    st.subheader("Espécies ao Longo do Tempo")
    species_temporal_data = filtered_data.groupby(
        filtered_data['Timestamp'].dt.date
    )['Scientific Name'].nunique().reset_index()

    fig_species_temporal = go.Figure()
    fig_species_temporal.add_trace(
        go.Scatter(
            x=species_temporal_data['Timestamp'],
            y=species_temporal_data['Scientific Name'],
            mode='lines',
            line=dict(color='#ff00ff', width=2, shape='spline'),
            fill='tozeroy',
            fillcolor='rgba(255,0,255,0.1)'
        )
    )
    fig_species_temporal.update_layout(create_graph_layout())
    st.plotly_chart(fig_species_temporal, use_container_width=True)

# Gráfico circular e condições climáticas
col1, col2 = st.columns(2)

with col1:
    st.subheader("Gráfico Circular por Hora")
    circular_data = filtered_data.groupby(['Hour']).size().reindex(
        range(24), fill_value=0
    ).reset_index(name='Detections')

    fig_circular = go.Figure(data=[
        go.Barpolar(
            r=circular_data['Detections'],
            theta=[h * 15 for h in range(24)],
            name="Detecções",
            text=[f"{h:02d}:00" for h in range(24)],
            hoverinfo="text+r"
        )
    ])
    fig_circular.update_layout(
        polar=dict(
            angularaxis=dict(
                direction="clockwise",
                rotation=90,
                tickmode="array",
                tickvals=[h * 15 for h in range(24)],
                ticktext=[f"{h:02d}:00" for h in range(24)]
            ),
            radialaxis=dict(showticklabels=False, ticks="")
        ),
        **create_graph_layout(show_legend=False)
    )
    st.plotly_chart(fig_circular, use_container_width=True)

with col2:
    st.subheader("Condições Climáticas")
    weather_type = st.radio(
        "Selecione o tipo de dados",
        ["Temperatura", "Precipitação", "Vento"],
        horizontal=True
    )

    # Filtrar dados climáticos usando session_state
    mask = (weather_data['time'].dt.date >= st.session_state.start_date) & \
           (weather_data['time'].dt.date <= st.session_state.end_date)
    filtered_weather = weather_data.loc[mask].copy()
    filtered_weather['daylight_hours'] = filtered_weather['daylight_duration (s)'] / 3600

    fig_weather = go.Figure()

    if weather_type == "Temperatura":
        temp_max = filtered_weather['temperature_2m_max (°C)'].tolist()
        temp_min = filtered_weather['temperature_2m_min (°C)'].tolist()
        time_values = filtered_weather['time'].tolist()

        fig_weather.add_trace(go.Scatter(
            x=time_values + time_values[::-1],
            y=temp_max + temp_min[::-1],
            fill='toself',
            fillcolor='rgba(100,100,255,0.2)',
            line=dict(color='rgba(255,255,255,0)'),
            name='Faixa de Temperatura',
            showlegend=False
        ))

        fig_weather.add_trace(go.Scatter(
            x=filtered_weather['time'],
            y=filtered_weather['temperature_2m_max (°C)'],
            name='Temp. Máx.',
            line=dict(color='#ff4444', width=2),
        ))
        fig_weather.add_trace(go.Scatter(
            x=filtered_weather['time'],
            y=filtered_weather['temperature_2m_mean (°C)'],
            name='Temp. Média',
            line=dict(color='#ffaa44', width=2, dash='dot'),
        ))
        fig_weather.add_trace(go.Scatter(
            x=filtered_weather['time'],
            y=filtered_weather['temperature_2m_min (°C)'],
            name='Temp. Mín.',
            line=dict(color='#4444ff', width=2),
        ))

    elif weather_type == "Precipitação":
        fig_weather.add_trace(go.Bar(
            x=filtered_weather['time'],
            y=filtered_weather['precipitation_sum (mm)'],
            name='Precipitação',
            marker_color='rgba(0,191,255,0.7)',
        ))

    else:  # Vento
        fig_weather.add_trace(go.Scatter(
            x=filtered_weather['time'],
            y=filtered_weather['wind_speed_10m_max (km/h)'],
            name='Vel. Vento Máx.',
            line=dict(color='#44ff44', width=2),
        ))

        fig_weather.add_trace(go.Scatter(
            x=filtered_weather['time'],
            y=filtered_weather['daylight_hours'],
            name='Duração do Dia',
            line=dict(color='#ffff44', width=2),
            yaxis='y2'
        ))

    fig_weather.update_layout(
        margin={"r": 50, "t": 10, "l": 50, "b": 10},
        paper_bgcolor="#1e1e2f",
        plot_bgcolor="#1e1e2f",
        font_color="white",
        xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
        yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
        yaxis2=dict(
            title="Duração do Dia (h)",
            overlaying='y',
            side='right',
            showgrid=False
        ) if weather_type == "Vento" else None,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        hovermode='x unified'
    )
    st.plotly_chart(fig_weather, use_container_width=True)

# Gráfico de iluminação lunar
st.subheader("Iluminação Lunar")
# Filtrar dados lunares usando session_state
mask = (moon_data['date'].dt.date >= st.session_state.start_date) & \
       (moon_data['date'].dt.date <= st.session_state.end_date)
filtered_moon = moon_data.loc[mask].copy()

fig_moon = go.Figure()

# Adicionar área preenchida para iluminação
fig_moon.add_trace(go.Scatter(
    x=filtered_moon['date'],
    y=filtered_moon['illum_pct'],
    fill='tozeroy',
    name='Iluminação (%)',
    line=dict(color='#FFD700', width=2),
    fillcolor='rgba(255, 215, 0, 0.2)',
))

# Adicionar marcadores para fases principais
phases = ['new', 'full']
colors = {'new': '#1a1a1a', 'full': '#FFD700'}

for phase in phases:
    phase_data = filtered_moon[filtered_moon['phase'] == phase]
    fig_moon.add_trace(go.Scatter(
        x=phase_data['date'],
        y=phase_data['illum_pct'],
        mode='markers',
        name=f'Lua {phase}',
        marker=dict(
            size=12,
            color=colors[phase],
            line=dict(color='white', width=1)
        )
    ))

fig_moon.update_layout(
    margin={"r": 10, "t": 10, "l": 10, "b": 10},
    paper_bgcolor="#1e1e2f",
    plot_bgcolor="#1e1e2f",
    font_color="white",
    xaxis=dict(
        showgrid=True,
        gridcolor='rgba(255,255,255,0.1)',
        title="Data"
    ),
    yaxis=dict(
        showgrid=True,
        gridcolor='rgba(255,255,255,0.1)',
        title="Iluminação (%)",
        range=[0, 100]
    ),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1
    ),
    hovermode='x unified'
)
st.plotly_chart(fig_moon, use_container_width=True)