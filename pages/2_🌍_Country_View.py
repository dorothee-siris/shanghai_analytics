"""
Country View - Compare countries' performance in rankings
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
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
# OVERVIEW METRICS
# ============================================================================
st.markdown("---")
st.markdown("## 📈 Overview")

# Calculate key metrics for each country
metrics_data = []
for country in selected_countries:
    arwu_c = arwu_countries[arwu_countries["Country/Region"] == country]
    gras_c = gras_countries[gras_countries["Country/Region"] == country]
    
    # 2025 data
    arwu_2025 = arwu_c[arwu_c["Year"] == 2025]
    gras_2025 = gras_c[gras_c["Year"] == 2025]
    
    metrics_data.append({
        "Country": country,
        "ARWU Institutions (2025)": len(arwu_2025),
        "GRAS Rankings (2025)": len(gras_2025),
        "ARWU Top 100": len(arwu_2025[arwu_2025["Rank_recomputed"] <= 100]),
        "ARWU Top 500": len(arwu_2025[arwu_2025["Rank_recomputed"] <= 500]),
        "Best ARWU Rank": int(arwu_2025["Rank_recomputed"].min()) if not arwu_2025.empty else "—",
        "Avg ARWU Rank": round(arwu_2025["Rank_recomputed"].mean(), 1) if not arwu_2025.empty else "—"
    })

metrics_df = pd.DataFrame(metrics_data)
st.dataframe(metrics_df, use_container_width=True, hide_index=True)

# ============================================================================
# INSTITUTIONS RANKED OVER TIME
# ============================================================================
st.markdown("---")
st.markdown("## 🏛️ Number of Institutions Ranked Over Time")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### ARWU")
    
    # Count institutions per country per year
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
    st.markdown("### GRAS (All Subjects)")
    
    # Count unique institutions per country per year in GRAS
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
# AVERAGE RANK COMPARISON
# ============================================================================
st.markdown("---")
st.markdown("## 📊 Average Rank Comparison")

rank_type = st.radio(
    "Select ranking",
    options=["ARWU Overall"] + sorted(gras_df["Subject"].unique().tolist()),
    horizontal=False
)

if rank_type == "ARWU Overall":
    # Calculate average ARWU rank per country per year
    avg_ranks = arwu_countries.groupby(["Year", "Country/Region"])["Rank_recomputed"].mean().reset_index(name="Avg_Rank")
    years_range = list(range(2017, 2026))
    title = "Average ARWU World Rank by Country"
else:
    # Calculate average GRAS rank for selected subject
    gras_subject = gras_countries[gras_countries["Subject"] == rank_type]
    avg_ranks = gras_subject.groupby(["Year", "Country/Region"])["Rank_global"].mean().reset_index(name="Avg_Rank")
    years_range = list(range(2021, 2026))
    title = f"Average {rank_type} Global Rank by Country"

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
    title=title,
    xaxis=dict(title="Year", dtick=1),
    yaxis=dict(title="Average Rank", autorange="reversed"),
    height=450,
    legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
    hovermode="x unified"
)

st.plotly_chart(fig_avg_rank, use_container_width=True)

# ============================================================================
# TOP INSTITUTIONS DISTRIBUTION (ARWU)
# ============================================================================
st.markdown("---")
st.markdown("## 🏆 ARWU Top Institutions Distribution (2025)")

# Create bins for rank ranges
arwu_2025 = arwu_countries[arwu_countries["Year"] == 2025].copy()

bins = [0, 10, 50, 100, 200, 500, 1000, float('inf')]
labels = ["Top 10", "11-50", "51-100", "101-200", "201-500", "501-1000", "1000+"]
arwu_2025["Rank_Bin"] = pd.cut(arwu_2025["Rank_recomputed"], bins=bins, labels=labels)

# Count per bin per country
bin_counts = arwu_2025.groupby(["Country/Region", "Rank_Bin"]).size().reset_index(name="Count")

fig_bins = go.Figure()

for country in selected_countries:
    country_data = bin_counts[bin_counts["Country/Region"] == country]
    # Ensure all bins are present
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

# ============================================================================
# GRAS SUBJECT COVERAGE
# ============================================================================
st.markdown("---")
st.markdown("## 📚 GRAS Subject Coverage (2025)")
st.caption("Number of institutions ranked per subject by country")

# Get subjects where selected countries have rankings
gras_2025 = gras_countries[gras_countries["Year"] == 2025]
subject_counts = gras_2025.groupby(["Country/Region", "Subject"]).size().reset_index(name="Count")

# Pivot for heatmap
subject_pivot = subject_counts.pivot(index="Subject", columns="Country/Region", values="Count").fillna(0)

# Sort by total count
subject_pivot["Total"] = subject_pivot.sum(axis=1)
subject_pivot = subject_pivot.sort_values("Total", ascending=False).drop(columns=["Total"])

# Show top 30 subjects
subject_pivot_display = subject_pivot.head(30)

fig_heatmap = go.Figure(data=go.Heatmap(
    z=subject_pivot_display.values,
    x=subject_pivot_display.columns.tolist(),
    y=subject_pivot_display.index.tolist(),
    colorscale="Blues",
    hovertemplate="Country: %{x}<br>Subject: %{y}<br>Institutions: %{z}<extra></extra>"
))

fig_heatmap.update_layout(
    title="Institutions Ranked per Subject (Top 30 subjects)",
    height=700,
    xaxis=dict(title="Country"),
    yaxis=dict(title="Subject", tickfont=dict(size=9))
)

st.plotly_chart(fig_heatmap, use_container_width=True)

# ============================================================================
# RADAR CHART - FIELD STRENGTHS
# ============================================================================
st.markdown("---")
st.markdown("## 🎯 Research Field Strengths (2025)")
st.caption("Average rank per field (lower is better). Inner = stronger.")

# Get fields
gras_2025_fields = gras_2025.copy()
field_avg = gras_2025_fields.groupby(["Country/Region", "Field"])["Rank_global"].mean().reset_index(name="Avg_Rank")

# Get all fields
all_fields = sorted(field_avg["Field"].unique())

fig_radar = go.Figure()

for country in selected_countries:
    country_field = field_avg[field_avg["Country/Region"] == country]
    
    # Create full field list with values
    values = []
    for field in all_fields:
        field_val = country_field[country_field["Field"] == field]["Avg_Rank"]
        if not field_val.empty:
            # Invert so lower rank = higher value (closer to center is worse)
            values.append(field_val.values[0])
        else:
            values.append(None)
    
    # Close the radar
    values_closed = values + [values[0]] if values[0] is not None else values
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
    polar=dict(
        radialaxis=dict(
            visible=True,
            autorange="reversed",  # Lower rank (better) = closer to edge
            title="Avg Rank"
        )
    ),
    height=600,
    legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5),
    title="Average Rank by Research Field (lower/inner = worse, outer = better)"
)

st.plotly_chart(fig_radar, use_container_width=True)

# ============================================================================
# SCATTER: QUANTITY VS QUALITY
# ============================================================================
st.markdown("---")
st.markdown("## 📍 Quantity vs Quality (ARWU 2025)")
st.caption("Bubble size = number of institutions in Top 100")

scatter_data = []
for country in selected_countries:
    arwu_c_2025 = arwu_2025[arwu_2025["Country/Region"] == country]
    if not arwu_c_2025.empty:
        scatter_data.append({
            "Country": country,
            "Total Institutions": len(arwu_c_2025),
            "Average Rank": arwu_c_2025["Rank_recomputed"].mean(),
            "Top 100 Count": len(arwu_c_2025[arwu_c_2025["Rank_recomputed"] <= 100]),
            "Best Rank": arwu_c_2025["Rank_recomputed"].min()
        })

if scatter_data:
    scatter_df = pd.DataFrame(scatter_data)
    
    fig_scatter = px.scatter(
        scatter_df,
        x="Total Institutions",
        y="Average Rank",
        size="Top 100 Count",
        color="Country",
        color_discrete_map=country_colors,
        hover_data=["Best Rank", "Top 100 Count"],
        text="Country"
    )
    
    fig_scatter.update_traces(textposition="top center")
    fig_scatter.update_layout(
        height=500,
        yaxis=dict(autorange="reversed", title="Average Rank (lower is better)"),
        xaxis=dict(title="Total Institutions Ranked"),
        showlegend=False
    )
    
    st.plotly_chart(fig_scatter, use_container_width=True)

# ============================================================================
# YEAR-OVER-YEAR CHANGE
# ============================================================================
st.markdown("---")
st.markdown("## 📈 Year-over-Year Change in ARWU Presence")

# Calculate YoY change in number of institutions
yoy_data = []
for country in selected_countries:
    arwu_c = arwu_countries[arwu_countries["Country/Region"] == country]
    yearly_counts = arwu_c.groupby("Year").size()
    
    for year in range(2018, 2026):
        if year in yearly_counts.index and year - 1 in yearly_counts.index:
            change = yearly_counts[year] - yearly_counts[year - 1]
            pct_change = (change / yearly_counts[year - 1]) * 100 if yearly_counts[year - 1] > 0 else 0
            yoy_data.append({
                "Country": country,
                "Year": year,
                "Change": change,
                "Pct_Change": pct_change
            })

if yoy_data:
    yoy_df = pd.DataFrame(yoy_data)
    
    fig_yoy = go.Figure()
    
    for country in selected_countries:
        country_yoy = yoy_df[yoy_df["Country"] == country]
        fig_yoy.add_trace(go.Bar(
            x=country_yoy["Year"],
            y=country_yoy["Change"],
            name=country,
            marker_color=country_colors[country]
        ))
    
    fig_yoy.update_layout(
        barmode="group",
        xaxis=dict(title="Year", dtick=1),
        yaxis=dict(title="Change in Number of Institutions"),
        height=400,
        legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5)
    )
    
    st.plotly_chart(fig_yoy, use_container_width=True)

# ============================================================================
# TOP INSTITUTIONS TABLE
# ============================================================================
st.markdown("---")
st.markdown("## 🏅 Top Institutions by Country (ARWU 2025)")

top_n = st.slider("Show top N institutions per country", min_value=3, max_value=20, value=5)

for country in selected_countries:
    st.markdown(f"### {country}")
    country_top = arwu_2025[arwu_2025["Country/Region"] == country].nsmallest(top_n, "Rank_recomputed")[
        ["Institution", "Rank_recomputed", "Score_normalized"]
    ].rename(columns={
        "Rank_recomputed": "World Rank",
        "Score_normalized": "Score"
    })
    
    if not country_top.empty:
        st.dataframe(country_top, use_container_width=True, hide_index=True)
    else:
        st.caption("No institutions ranked.")