"""
Country View - Compare countries' performance in rankings
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils import load_arwu, load_gras, get_country_list

st.set_page_config(page_title="Country View", page_icon="🌍", layout="wide")
st.title("🌍 Country Analytics")

# Load data
arwu_df = load_arwu()
gras_df = load_gras()
countries = get_country_list()

# ============================================================================
# COUNTRY SELECTION
# ============================================================================
st.markdown("### Select countries to analyze")

selected_countries = st.multiselect(
    "Choose one or more countries",
    options=countries,
    default=["United States", "China", "United Kingdom"] if all(c in countries for c in ["United States", "China", "United Kingdom"]) else countries[:3],
    max_selections=10
)

if not selected_countries:
    st.info("👆 Select at least one country to view analytics.")
    st.stop()

# Filter data for selected countries
arwu_countries = arwu_df[arwu_df["Country/Region"].isin(selected_countries)]
gras_countries = gras_df[gras_df["Country/Region"].isin(selected_countries)]

# Color palette for countries
country_colors = {}
color_palette = px.colors.qualitative.Plotly
for i, country in enumerate(selected_countries):
    country_colors[country] = color_palette[i % len(color_palette)]

# ============================================================================
# SECTION 1: OVERVIEW METRICS
# ============================================================================
st.markdown("---")
st.markdown("## 📈 Overview (2025)")

# Calculate key metrics for each country
metrics_data = []
for country in selected_countries:
    arwu_c = arwu_countries[arwu_countries["Country/Region"] == country]
    gras_c = gras_countries[gras_countries["Country/Region"] == country]
    
    arwu_2025 = arwu_c[arwu_c["Year"] == 2025]
    gras_2025 = gras_c[gras_c["Year"] == 2025]
    
    metrics_data.append({
        "Country": country,
        "ARWU Institutions": len(arwu_2025),
        "ARWU Top 100": len(arwu_2025[arwu_2025["Rank_recomputed"] <= 100]),
        "ARWU Top 500": len(arwu_2025[arwu_2025["Rank_recomputed"] <= 500]),
        "Best ARWU Rank": int(arwu_2025["Rank_recomputed"].min()) if not arwu_2025.empty else "—",
        "Avg ARWU Rank": round(arwu_2025["Rank_recomputed"].mean(), 1) if not arwu_2025.empty else "—",
        "GRAS Unique Institutions": gras_2025["Institution"].nunique(),
        "GRAS Total Rankings": len(gras_2025)
    })

metrics_df = pd.DataFrame(metrics_data)
st.dataframe(metrics_df, use_container_width=True, hide_index=True)

# ============================================================================
# SECTION 2: INSTITUTIONS RANKED OVER TIME
# ============================================================================
st.markdown("---")
st.markdown("## 🏛️ Number of Institutions Ranked Over Time")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### ARWU")
    arwu_counts = arwu_countries.groupby(["Year", "Country/Region"]).size().reset_index(name="Count")
    
    fig_arwu_count = go.Figure()
    for country in selected_countries:
        country_data = arwu_counts[arwu_counts["Country/Region"] == country]
        fig_arwu_count.add_trace(go.Bar(
            x=country_data["Year"],
            y=country_data["Count"],
            name=country,
            marker_color=country_colors[country]
        ))
    
    fig_arwu_count.update_layout(
        barmode="group",
        xaxis=dict(title="Year", dtick=1),
        yaxis=dict(title="Number of Institutions"),
        height=400,
        legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5)
    )
    st.plotly_chart(fig_arwu_count, use_container_width=True)

with col2:
    st.markdown("### GRAS (Unique Institutions)")
    gras_inst_counts = gras_countries.groupby(["Year", "Country/Region"])["Institution"].nunique().reset_index(name="Count")
    
    fig_gras_count = go.Figure()
    for country in selected_countries:
        country_data = gras_inst_counts[gras_inst_counts["Country/Region"] == country]
        fig_gras_count.add_trace(go.Bar(
            x=country_data["Year"],
            y=country_data["Count"],
            name=country,
            marker_color=country_colors[country]
        ))
    
    fig_gras_count.update_layout(
        barmode="group",
        xaxis=dict(title="Year", dtick=1),
        yaxis=dict(title="Number of Institutions"),
        height=400,
        legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5)
    )
    st.plotly_chart(fig_gras_count, use_container_width=True)

# ============================================================================
# SECTION 3: RESEARCH FIELD STRENGTHS (RADAR)
# ============================================================================
st.markdown("---")
st.markdown("## 🎯 Research Field Strengths (2025)")
st.caption("Average rank per field. Outer position = better (lower average rank).")

gras_2025 = gras_countries[gras_countries["Year"] == 2025]
field_avg = gras_2025.groupby(["Country/Region", "Field"])["Rank_global"].mean().reset_index(name="Avg_Rank")
all_fields = sorted(field_avg["Field"].unique())

fig_radar = go.Figure()

for country in selected_countries:
    country_field = field_avg[field_avg["Country/Region"] == country]
    
    values = []
    for field in all_fields:
        field_val = country_field[country_field["Field"] == field]["Avg_Rank"]
        values.append(field_val.values[0] if not field_val.empty else None)
    
    values_closed = values + [values[0]] if values and values[0] is not None else values
    fields_closed = all_fields + [all_fields[0]]
    
    fig_radar.add_trace(go.Scatterpolar(
        r=values_closed,
        theta=fields_closed,
        fill='toself',
        name=country,
        line=dict(color=country_colors[country]),
        opacity=0.6
    ))

fig_radar.update_layout(
    polar=dict(radialaxis=dict(visible=True, autorange="reversed", title="Avg Rank")),
    height=550,
    legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5)
)
st.plotly_chart(fig_radar, use_container_width=True)

# ============================================================================
# SECTION 4: DETAILED RANKING ANALYSIS (LINKED CHARTS)
# ============================================================================
st.markdown("---")
st.markdown("## 📊 Detailed Ranking Analysis")

# Dropdown for ranking selection
all_subjects = sorted(gras_df["Subject"].unique().tolist())
ranking_options = ["ARWU Overall"] + all_subjects

selected_ranking = st.selectbox(
    "Select ranking to analyze",
    options=ranking_options,
    index=0
)

is_arwu = selected_ranking == "ARWU Overall"

if is_arwu:
    analysis_df = arwu_countries.copy()
    rank_col = "Rank_recomputed"
    years_range = list(range(2017, 2026))
    year_2025 = arwu_countries[arwu_countries["Year"] == 2025]
else:
    analysis_df = gras_countries[gras_countries["Subject"] == selected_ranking].copy()
    rank_col = "Rank_global"
    years_range = list(range(2021, 2026))
    year_2025 = analysis_df[analysis_df["Year"] == 2025]

col_avg, col_dist = st.columns(2)

# --- Average Rank Evolution ---
with col_avg:
    st.markdown("### Average Rank Evolution")
    
    avg_ranks = analysis_df.groupby(["Year", "Country/Region"])[rank_col].mean().reset_index(name="Avg_Rank")
    
    fig_avg_rank = go.Figure()
    for country in selected_countries:
        country_data = avg_ranks[avg_ranks["Country/Region"] == country].sort_values("Year")
        country_plot = country_data.set_index("Year").reindex(years_range)
        
        fig_avg_rank.add_trace(go.Scatter(
            x=years_range,
            y=country_plot["Avg_Rank"],
            mode="lines+markers",
            name=country,
            line=dict(color=country_colors[country], width=2),
            marker=dict(size=8),
            connectgaps=False
        ))
    
    fig_avg_rank.update_layout(
        xaxis=dict(title="Year", dtick=1),
        yaxis=dict(title="Average Rank", autorange="reversed"),
        height=400,
        legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5),
        hovermode="x unified"
    )
    st.plotly_chart(fig_avg_rank, use_container_width=True)

# --- Rank Distribution ---
with col_dist:
    st.markdown("### Rank Distribution (2025)")
    
    if not year_2025.empty:
        year_2025_copy = year_2025.copy()
        
        if is_arwu:
            bins = [0, 10, 50, 100, 200, 500, 1000, float('inf')]
            labels = ["Top 10", "11-50", "51-100", "101-200", "201-500", "501-1000", "1000+"]
        else:
            max_rank = year_2025_copy[rank_col].max()
            if max_rank <= 100:
                bins = [0, 10, 25, 50, 75, 100, float('inf')]
                labels = ["Top 10", "11-25", "26-50", "51-75", "76-100", "100+"]
            else:
                bins = [0, 25, 50, 100, 200, 300, float('inf')]
                labels = ["Top 25", "26-50", "51-100", "101-200", "201-300", "300+"]
        
        year_2025_copy["Rank_Bin"] = pd.cut(year_2025_copy[rank_col], bins=bins, labels=labels)
        bin_counts = year_2025_copy.groupby(["Country/Region", "Rank_Bin"]).size().reset_index(name="Count")
        
        fig_bins = go.Figure()
        for country in selected_countries:
            country_data = bin_counts[bin_counts["Country/Region"] == country]
            all_bins = pd.DataFrame({"Rank_Bin": labels})
            country_data = all_bins.merge(country_data, on="Rank_Bin", how="left").fillna(0)
            
            fig_bins.add_trace(go.Bar(
                x=country_data["Rank_Bin"],
                y=country_data["Count"],
                name=country,
                marker_color=country_colors[country]
            ))
        
        fig_bins.update_layout(
            barmode="group",
            xaxis=dict(title="Rank Range", categoryorder="array", categoryarray=labels),
            yaxis=dict(title="Number of Institutions"),
            height=400,
            legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5)
        )
        st.plotly_chart(fig_bins, use_container_width=True)
    else:
        st.info("No data available for 2025.")

# ============================================================================
# SECTION 5: TOP INSTITUTIONS TRAJECTORIES
# ============================================================================
st.markdown("---")
st.markdown("## 📈 Top Institutions Trajectories")
st.caption(f"Evolution of top institutions from each country in {selected_ranking}. Same color = same country.")

top_n_trajectory = st.slider("Top N institutions per country to display", min_value=1, max_value=10, value=3, key="trajectory_slider")

# Get top N institutions per country from 2025
top_institutions_by_country = {}
for country in selected_countries:
    if is_arwu:
        country_2025 = arwu_countries[(arwu_countries["Country/Region"] == country) & (arwu_countries["Year"] == 2025)]
    else:
        country_2025 = analysis_df[(analysis_df["Country/Region"] == country) & (analysis_df["Year"] == 2025)]
    
    top_insts = country_2025.nsmallest(top_n_trajectory, rank_col)["Institution"].tolist()
    top_institutions_by_country[country] = top_insts

# Flatten list of all top institutions
all_top_institutions = []
for insts in top_institutions_by_country.values():
    all_top_institutions.extend(insts)

# Get historical data for these institutions
if is_arwu:
    trajectory_data = arwu_df[arwu_df["Institution"].isin(all_top_institutions)].copy()
else:
    trajectory_data = gras_df[(gras_df["Institution"].isin(all_top_institutions)) & (gras_df["Subject"] == selected_ranking)].copy()

fig_trajectory = go.Figure()

# Create shades for each country
def get_country_shades(base_color, n_shades):
    """Generate shades of a color."""
    import plotly.colors as pc
    try:
        rgb = pc.hex_to_rgb(base_color)
    except:
        rgb = (100, 100, 100)
    
    shades = []
    for i in range(n_shades):
        factor = 1 - (i * 0.15)
        r = min(255, int(rgb[0] * factor + 255 * (1 - factor) * 0.3))
        g = min(255, int(rgb[1] * factor + 255 * (1 - factor) * 0.3))
        b = min(255, int(rgb[2] * factor + 255 * (1 - factor) * 0.3))
        shades.append(f"rgb({r},{g},{b})")
    return shades

for country in selected_countries:
    institutions = top_institutions_by_country.get(country, [])
    shades = get_country_shades(country_colors[country], len(institutions))
    
    for i, inst in enumerate(institutions):
        inst_data = trajectory_data[trajectory_data["Institution"] == inst].sort_values("Year")
        inst_plot = inst_data.set_index("Year").reindex(years_range)
        
        fig_trajectory.add_trace(go.Scatter(
            x=years_range,
            y=inst_plot[rank_col],
            mode="lines+markers",
            name=f"{inst} ({country})",
            line=dict(color=shades[i], width=2),
            marker=dict(size=6),
            connectgaps=False,
            legendgroup=country,
            hovertemplate=f"<b>{inst}</b><br>Year: %{{x}}<br>Rank: %{{y}}<extra>{country}</extra>"
        ))

fig_trajectory.update_layout(
    xaxis=dict(title="Year", dtick=1),
    yaxis=dict(title="Rank", autorange="reversed"),
    height=550,
    legend=dict(orientation="h", yanchor="top", y=-0.1, xanchor="center", x=0.5, font=dict(size=9)),
    hovermode="closest"
)
st.plotly_chart(fig_trajectory, use_container_width=True)

# ============================================================================
# SECTION 6: GRAS SUBJECT COVERAGE HEATMAP
# ============================================================================
st.markdown("---")
st.markdown("## 📚 GRAS Subject Coverage (2025)")
st.caption("Number of institutions ranked per subject by country")

gras_2025_all = gras_countries[gras_countries["Year"] == 2025]
subject_counts = gras_2025_all.groupby(["Country/Region", "Subject"]).size().reset_index(name="Count")

subject_pivot = subject_counts.pivot(index="Subject", columns="Country/Region", values="Count").fillna(0)
subject_pivot["Total"] = subject_pivot.sum(axis=1)
subject_pivot = subject_pivot.sort_values("Total", ascending=False).drop(columns=["Total"])
subject_pivot_display = subject_pivot.head(30)

fig_heatmap = go.Figure(data=go.Heatmap(
    z=subject_pivot_display.values,
    x=subject_pivot_display.columns.tolist(),
    y=subject_pivot_display.index.tolist(),
    colorscale="Blues",
    hovertemplate="Country: %{x}<br>Subject: %{y}<br>Institutions: %{z}<extra></extra>"
))

fig_heatmap.update_layout(
    title="Institutions Ranked per Subject (Top 30 subjects by total count)",
    height=700,
    xaxis=dict(title="Country"),
    yaxis=dict(title="Subject", tickfont=dict(size=9))
)
st.plotly_chart(fig_heatmap, use_container_width=True)

# ============================================================================
# SECTION 7: TOP INSTITUTIONS TABLE
# ============================================================================
st.markdown("---")
st.markdown(f"## 🏅 Top Institutions by Country ({selected_ranking} - 2025)")

top_n_table = st.slider("Show top N institutions per country", min_value=3, max_value=20, value=5, key="table_slider")

# Calculate GRAS subject count per institution in 2025
gras_2025_counts = gras_countries[gras_countries["Year"] == 2025].groupby("Institution")["Subject"].nunique().reset_index(name="GRAS_Subjects_2025")

for country in selected_countries:
    st.markdown(f"### {country}")
    
    if is_arwu:
        country_2025 = arwu_countries[(arwu_countries["Country/Region"] == country) & (arwu_countries["Year"] == 2025)]
        country_top = country_2025.nsmallest(top_n_table, "Rank_recomputed")[["Institution", "Rank_recomputed"]].copy()
        country_top = country_top.rename(columns={"Rank_recomputed": "World Rank"})
    else:
        country_2025 = analysis_df[(analysis_df["Country/Region"] == country) & (analysis_df["Year"] == 2025)]
        country_top = country_2025.nsmallest(top_n_table, "Rank_global")[["Institution", "Rank_global"]].copy()
        country_top = country_top.rename(columns={"Rank_global": "Global Rank"})
    
    # Merge with GRAS subject count
    country_top = country_top.merge(gras_2025_counts, on="Institution", how="left")
    country_top["GRAS_Subjects_2025"] = country_top["GRAS_Subjects_2025"].fillna(0).astype(int)
    country_top = country_top.rename(columns={"GRAS_Subjects_2025": "GRAS Subjects (2025)"})
    
    if not country_top.empty:
        st.dataframe(country_top, use_container_width=True, hide_index=True)
    else:
        st.caption("No institutions ranked.")