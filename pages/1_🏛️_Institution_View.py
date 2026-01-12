"""
Institution View - Analyze a specific institution's rankings
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils import load_arwu, load_gras, get_institution_list, search_institutions, label_institution

st.set_page_config(page_title="Institution View", page_icon="🏛️", layout="wide")
st.title("🏛️ Institution View")

# Load data
arwu_df = load_arwu()
gras_df = load_gras()
institutions_df = get_institution_list()

# ============================================================================
# SEARCH SECTION
# ============================================================================
st.markdown("### Find your institution")
q = st.text_input(
    "Search by name",
    placeholder="e.g., Harvard, Sorbonne, ETH Zurich, Peking University..."
)

chosen = None

if q:
    results = search_institutions(institutions_df, q)
else:
    results = institutions_df.head(0)

if len(results) == 0 and q:
    st.info("No match found. Try fewer words or a different spelling.")
elif len(results) > 0:
    st.caption(f"Found {len(results)} match(es)")
    options = ["— Select an institution —"] + [label_institution(r) for _, r in results.iterrows()]
    sel = st.selectbox("Select institution", options=options, index=0, label_visibility="collapsed")
    if sel != "— Select an institution —":
        idx = options.index(sel) - 1
        chosen = results.iloc[idx]

if chosen is None:
    st.markdown("---")
    st.info("👆 Search and select an institution to view its rankings.")
    st.stop()

# ============================================================================
# INSTITUTION SELECTED - HEADER
# ============================================================================
inst_name = chosen["Institution"]
inst_country = chosen["Country/Region"]

st.markdown("---")
st.header(f"{inst_name}")
st.caption(f"📍 {inst_country}")

# Filter data for this institution
arwu_inst = arwu_df[arwu_df["Institution"] == inst_name].sort_values("Year")
gras_inst = gras_df[gras_df["Institution"] == inst_name].sort_values("Year")

# ============================================================================
# ARWU SECTION
# ============================================================================
st.markdown("---")
st.markdown("## 📊 ARWU Rankings")

if arwu_inst.empty:
    st.warning(f"{inst_name} is not ranked in ARWU (2017-2025).")
else:
    # ---------- ARWU Evolution Line Plot ----------
    st.markdown("### World Rank Evolution")
    
    all_years = list(range(2017, 2026))
    arwu_plot = arwu_inst.set_index("Year").reindex(all_years).reset_index()
    arwu_plot.columns = ["Year"] + list(arwu_plot.columns[1:])
    
    fig_arwu_evo = go.Figure()
    
    fig_arwu_evo.add_trace(go.Scatter(
        x=arwu_plot["Year"],
        y=arwu_plot["Rank_recomputed"],
        mode="lines+markers",
        name=inst_name,
        line=dict(color="#1f77b4", width=3),
        marker=dict(size=10, color="#1f77b4"),
        connectgaps=False,
        hovertemplate="<b>Year:</b> %{x}<br><b>World Rank:</b> %{y}<extra></extra>"
    ))
    
    fig_arwu_evo.update_layout(
        title=f"ARWU World Rank Evolution",
        xaxis=dict(title="Year", dtick=1, range=[2016.5, 2025.5]),
        yaxis=dict(title="World Rank", autorange="reversed"),
        height=400,
        hovermode="x unified"
    )
    
    st.plotly_chart(fig_arwu_evo, use_container_width=True)
    
    # ---------- ARWU Country Positioning (Regional Rank Evolution) ----------
    st.markdown("### Country Positioning")
    st.caption(f"Top 10 institutions in {inst_country} (2025) + selected institution. Showing regional rank evolution.")
    
    latest_year = arwu_inst["Year"].max()
    
    # Get top 10 from country in 2025
    arwu_country_2025 = arwu_df[
        (arwu_df["Country/Region"] == inst_country) & 
        (arwu_df["Year"] == 2025)
    ].nsmallest(10, "Region_Rank_recomputed")
    
    top10_institutions = arwu_country_2025["Institution"].tolist()
    
    # Add selected institution if not in top 10
    if inst_name not in top10_institutions:
        top10_institutions.append(inst_name)
    
    # Get all data for these institutions
    arwu_country_all = arwu_df[
        (arwu_df["Country/Region"] == inst_country) & 
        (arwu_df["Institution"].isin(top10_institutions))
    ].copy()
    
    fig_country = go.Figure()
    colors = px.colors.qualitative.Plotly
    
    for i, institution in enumerate(top10_institutions):
        inst_data = arwu_country_all[arwu_country_all["Institution"] == institution].sort_values("Year")
        inst_plot = inst_data.set_index("Year").reindex(all_years)
        
        is_selected = institution == inst_name
        line_width = 4 if is_selected else 2
        line_color = "#e74c3c" if is_selected else colors[i % len(colors)]
        
        # Create custom hover with world rank
        hover_text = []
        for yr in all_years:
            if yr in inst_data["Year"].values:
                row = inst_data[inst_data["Year"] == yr].iloc[0]
                hover_text.append(
                    f"<b>{institution}</b><br>Year: {yr}<br>Regional Rank: {int(row['Region_Rank_recomputed'])}<br>World Rank: {int(row['Rank_recomputed'])}"
                )
            else:
                hover_text.append(None)
        
        fig_country.add_trace(go.Scatter(
            x=all_years,
            y=inst_plot["Region_Rank_recomputed"],
            mode="lines+markers",
            name=institution,
            line=dict(color=line_color, width=line_width),
            marker=dict(size=8 if not is_selected else 12),
            connectgaps=False,
            hovertemplate="%{text}<extra></extra>",
            text=hover_text
        ))
    
    fig_country.update_layout(
        title=f"Regional Rank Evolution - {inst_country}",
        xaxis=dict(title="Year", dtick=1, range=[2016.5, 2025.5]),
        yaxis=dict(title=f"Regional Rank ({inst_country})", autorange="reversed"),
        height=500,
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.15,
            xanchor="center",
            x=0.5,
            font=dict(size=10)
        ),
        hovermode="closest"
    )
    
    st.plotly_chart(fig_country, use_container_width=True)

# ============================================================================
# GRAS SECTION
# ============================================================================
st.markdown("---")
st.markdown("## 📚 GRAS Subject Rankings")

if gras_inst.empty:
    st.warning(f"{inst_name} is not ranked in any GRAS subject (2021-2025).")
else:
    # ---------- GRAS Rankings Table ----------
    st.markdown("### Rankings Overview")
    
    # Pivot table: subjects x years
    gras_pivot = gras_inst.pivot_table(
        index="Subject",
        columns="Year",
        values="Rank_global",
        aggfunc="first"
    ).reset_index()
    
    # Sort by 2025 rank (or latest available)
    gras_years = sorted(gras_inst["Year"].unique(), reverse=True)
    for yr in gras_years:
        if yr in gras_pivot.columns:
            gras_pivot = gras_pivot.sort_values(yr, na_position="last")
            break
    
    # Format for display
    gras_display = gras_pivot.copy()
    year_cols = [c for c in gras_display.columns if isinstance(c, int)]
    for col in year_cols:
        gras_display[col] = gras_display[col].apply(lambda x: int(x) if pd.notna(x) else "—")
    
    st.dataframe(
        gras_display,
        use_container_width=True,
        hide_index=True,
        height=min(400, len(gras_display) * 35 + 40)
    )
    
    # ---------- GRAS Evolution Multi-Line Plot ----------
    st.markdown("### Subject Rank Evolution")
    
    latest_gras_year = gras_inst["Year"].max()
    gras_latest = gras_inst[gras_inst["Year"] == latest_gras_year].nsmallest(10, "Rank_global")
    top_subjects = gras_latest["Subject"].tolist()
    
    # Get all subjects for dropdown
    all_inst_subjects = sorted(gras_inst["Subject"].unique().tolist())
    other_subjects = [s for s in all_inst_subjects if s not in top_subjects]
    
    # Multi-select for additional subjects
    additional_subjects = st.multiselect(
        "Add more subjects to display",
        options=other_subjects,
        default=[],
        placeholder="Select additional subjects..."
    )
    
    display_subjects = top_subjects + additional_subjects
    
    st.caption(f"Showing top 10 subjects from {latest_gras_year} + selected. Click legend to show/hide.")
    
    gras_top = gras_inst[gras_inst["Subject"].isin(display_subjects)].copy()
    
    fig_gras_evo = go.Figure()
    colors = px.colors.qualitative.Plotly
    all_gras_years = list(range(2021, 2026))
    
    for i, subject in enumerate(display_subjects):
        subj_data = gras_top[gras_top["Subject"] == subject].sort_values("Year")
        subj_plot = subj_data.set_index("Year").reindex(all_gras_years)
        
        # Different style for manually added subjects
        is_additional = subject in additional_subjects
        line_dash = "dash" if is_additional else "solid"
        
        fig_gras_evo.add_trace(go.Scatter(
            x=all_gras_years,
            y=subj_plot["Rank_global"],
            mode="lines+markers",
            name=subject,
            line=dict(color=colors[i % len(colors)], width=2, dash=line_dash),
            marker=dict(size=8),
            connectgaps=False,
            hovertemplate=f"<b>{subject}</b><br>Year: %{{x}}<br>Rank: %{{y}}<extra></extra>"
        ))
    
    fig_gras_evo.update_layout(
        title="GRAS Global Rank by Subject",
        xaxis=dict(title="Year", dtick=1, range=[2020.5, 2025.5]),
        yaxis=dict(title="Global Rank", autorange="reversed"),
        height=500,
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.15,
            xanchor="center",
            x=0.5,
            font=dict(size=10)
        ),
        hovermode="closest"
    )
    
    st.plotly_chart(fig_gras_evo, use_container_width=True)
    
    # ---------- GRAS Country Positioning ----------
    st.markdown("### Country Positioning by Subject")
    st.caption(f"Top 10 institutions in {inst_country} for selected subject + selected institution.")
    
    # Get subjects where institution appears
    inst_subjects = sorted(gras_inst["Subject"].unique().tolist())
    
    selected_subject = st.selectbox(
        "Select subject for country comparison",
        options=inst_subjects,
        index=0 if inst_subjects else None
    )
    
    if selected_subject:
        # Get top 10 from country in 2025 for this subject
        gras_country_2025 = gras_df[
            (gras_df["Country/Region"] == inst_country) & 
            (gras_df["Year"] == latest_gras_year) &
            (gras_df["Subject"] == selected_subject)
        ].nsmallest(10, "Rank_region")
        
        top10_gras_institutions = gras_country_2025["Institution"].tolist()
        
        # Add selected institution if not in top 10
        if inst_name not in top10_gras_institutions:
            top10_gras_institutions.append(inst_name)
        
        # Get all data for these institutions in this subject
        gras_country_all = gras_df[
            (gras_df["Country/Region"] == inst_country) & 
            (gras_df["Subject"] == selected_subject) &
            (gras_df["Institution"].isin(top10_gras_institutions))
        ].copy()
        
        if not gras_country_all.empty:
            fig_gras_country = go.Figure()
            all_gras_years = list(range(2021, 2026))
            
            for i, institution in enumerate(top10_gras_institutions):
                inst_subj_data = gras_country_all[gras_country_all["Institution"] == institution].sort_values("Year")
                inst_subj_plot = inst_subj_data.set_index("Year").reindex(all_gras_years)
                
                is_selected = institution == inst_name
                line_width = 4 if is_selected else 2
                line_color = "#e74c3c" if is_selected else colors[i % len(colors)]
                
                # Create custom hover with global rank
                hover_text = []
                for yr in all_gras_years:
                    if yr in inst_subj_data["Year"].values:
                        row = inst_subj_data[inst_subj_data["Year"] == yr].iloc[0]
                        regional_rank = int(row["Rank_region"]) if pd.notna(row.get("Rank_region")) else "N/A"
                        global_rank = int(row["Rank_global"]) if pd.notna(row.get("Rank_global")) else "N/A"
                        hover_text.append(
                            f"<b>{institution}</b><br>Year: {yr}<br>Regional Rank: {regional_rank}<br>Global Rank: {global_rank}"
                        )
                    else:
                        hover_text.append(None)
                
                fig_gras_country.add_trace(go.Scatter(
                    x=all_gras_years,
                    y=inst_subj_plot["Rank_region"],
                    mode="lines+markers",
                    name=institution,
                    line=dict(color=line_color, width=line_width),
                    marker=dict(size=8 if not is_selected else 12),
                    connectgaps=False,
                    hovertemplate="%{text}<extra></extra>",
                    text=hover_text
                ))
            
            fig_gras_country.update_layout(
                title=f"{selected_subject} - Regional Rank Evolution in {inst_country}",
                xaxis=dict(title="Year", dtick=1, range=[2020.5, 2025.5]),
                yaxis=dict(title=f"Regional Rank ({inst_country})", autorange="reversed"),
                height=500,
                legend=dict(
                    orientation="h",
                    yanchor="top",
                    y=-0.15,
                    xanchor="center",
                    x=0.5,
                    font=dict(size=10)
                ),
                hovermode="closest"
            )
            
            st.plotly_chart(fig_gras_country, use_container_width=True)
        else:
            st.info(f"No data for {selected_subject} in {inst_country}.")

# ============================================================================
# BENCHMARK SECTION
# ============================================================================
st.markdown("---")
st.markdown("## 🔄 Benchmark Comparison")

benchmark_type = st.radio(
    "Select ranking to compare",
    options=["ARWU Overall", "GRAS Subject"],
    horizontal=True
)

# Initialize session state for benchmark institutions
if "benchmark_institutions" not in st.session_state:
    st.session_state.benchmark_institutions = []

st.markdown("#### Add institutions to compare")

col_search, col_tags = st.columns([1, 2])

with col_search:
    q_bench = st.text_input(
        "Search institution to add",
        placeholder="e.g., MIT, Oxford, Tsinghua...",
        key="benchmark_search"
    )
    
    if q_bench:
        results_bench = search_institutions(institutions_df, q_bench)
        # Exclude current institution and already selected ones
        already_selected = [inst_name] + st.session_state.benchmark_institutions
        results_bench = results_bench[~results_bench["Institution"].isin(already_selected)]
        
        if len(results_bench) > 0:
            options_bench = [label_institution(r) for _, r in results_bench.head(10).iterrows()]
            for opt in options_bench:
                inst_opt = results_bench[results_bench.apply(lambda r: label_institution(r) == opt, axis=1)].iloc[0]["Institution"]
                if st.button(f"➕ {opt}", key=f"add_{inst_opt}"):
                    st.session_state.benchmark_institutions.append(inst_opt)
                    st.rerun()

with col_tags:
    st.markdown("**Selected for comparison:**")
    if not st.session_state.benchmark_institutions:
        st.caption("No institutions selected yet. Search and add institutions to compare.")
    else:
        # Display tags with remove buttons
        cols = st.columns(min(len(st.session_state.benchmark_institutions), 4))
        for i, bench_inst in enumerate(st.session_state.benchmark_institutions):
            with cols[i % 4]:
                if st.button(f"❌ {bench_inst[:25]}...", key=f"remove_{bench_inst}"):
                    st.session_state.benchmark_institutions.remove(bench_inst)
                    st.rerun()

# Subject selector for GRAS benchmark
if benchmark_type == "GRAS Subject":
    all_subjects = sorted(gras_df["Subject"].unique().tolist())
    default_subj_idx = 0
    if not gras_inst.empty:
        latest_gras_year = gras_inst["Year"].max()
        gras_latest = gras_inst[gras_inst["Year"] == latest_gras_year].nsmallest(1, "Rank_global")
        if not gras_latest.empty and gras_latest.iloc[0]["Subject"] in all_subjects:
            default_subj_idx = all_subjects.index(gras_latest.iloc[0]["Subject"])
    
    bench_subject = st.selectbox(
        "Select subject to compare",
        options=all_subjects,
        index=default_subj_idx,
        key="bench_subject"
    )

# Generate benchmark chart
st.markdown("---")

if benchmark_type == "ARWU Overall":
    if arwu_inst.empty and not st.session_state.benchmark_institutions:
        st.info("👆 Add institutions to compare ARWU rankings.")
    else:
        fig_bench = go.Figure()
        all_years = list(range(2017, 2026))
        colors_bench = ["#1f77b4", "#e74c3c", "#2ca02c", "#9467bd", "#ff7f0e", "#8c564b", "#17becf", "#bcbd22"]
        
        # Add main institution
        if not arwu_inst.empty:
            arwu1_plot = arwu_inst.set_index("Year").reindex(all_years)
            fig_bench.add_trace(go.Scatter(
                x=all_years,
                y=arwu1_plot["Rank_recomputed"],
                mode="lines+markers",
                name=inst_name,
                line=dict(color=colors_bench[0], width=3),
                marker=dict(size=10),
                connectgaps=False,
                hovertemplate=f"<b>{inst_name}</b><br>Year: %{{x}}<br>Rank: %{{y}}<extra></extra>"
            ))
        
        # Add benchmark institutions
        for i, bench_inst in enumerate(st.session_state.benchmark_institutions):
            arwu_bench = arwu_df[arwu_df["Institution"] == bench_inst].sort_values("Year")
            if not arwu_bench.empty:
                arwu_bench_plot = arwu_bench.set_index("Year").reindex(all_years)
                fig_bench.add_trace(go.Scatter(
                    x=all_years,
                    y=arwu_bench_plot["Rank_recomputed"],
                    mode="lines+markers",
                    name=bench_inst,
                    line=dict(color=colors_bench[(i + 1) % len(colors_bench)], width=3),
                    marker=dict(size=10),
                    connectgaps=False,
                    hovertemplate=f"<b>{bench_inst}</b><br>Year: %{{x}}<br>Rank: %{{y}}<extra></extra>"
                ))
        
        fig_bench.update_layout(
            title="ARWU World Rank Comparison",
            xaxis=dict(title="Year", dtick=1, range=[2016.5, 2025.5]),
            yaxis=dict(title="World Rank", autorange="reversed"),
            height=500,
            legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5),
            hovermode="x unified"
        )
        
        st.plotly_chart(fig_bench, use_container_width=True)

else:  # GRAS Subject
    if gras_inst.empty:
        st.warning(f"{inst_name} has no GRAS rankings.")
    elif not st.session_state.benchmark_institutions:
        st.info("👆 Add institutions to compare GRAS rankings.")
    else:
        fig_bench_gras = go.Figure()
        all_gras_years = list(range(2021, 2026))
        colors_bench = ["#1f77b4", "#e74c3c", "#2ca02c", "#9467bd", "#ff7f0e", "#8c564b", "#17becf", "#bcbd22"]
        
        # Add main institution
        gras_inst1_subj = gras_inst[gras_inst["Subject"] == bench_subject].copy()
        if not gras_inst1_subj.empty:
            gras1_plot = gras_inst1_subj.set_index("Year").reindex(all_gras_years)
            fig_bench_gras.add_trace(go.Scatter(
                x=all_gras_years,
                y=gras1_plot["Rank_global"],
                mode="lines+markers",
                name=inst_name,
                line=dict(color=colors_bench[0], width=3),
                marker=dict(size=10),
                connectgaps=False,
                hovertemplate=f"<b>{inst_name}</b><br>Year: %{{x}}<br>Rank: %{{y}}<extra></extra>"
            ))
        
        # Add benchmark institutions
        for i, bench_inst in enumerate(st.session_state.benchmark_institutions):
            gras_bench = gras_df[
                (gras_df["Institution"] == bench_inst) & 
                (gras_df["Subject"] == bench_subject)
            ].sort_values("Year")
            
            if not gras_bench.empty:
                gras_bench_plot = gras_bench.set_index("Year").reindex(all_gras_years)
                fig_bench_gras.add_trace(go.Scatter(
                    x=all_gras_years,
                    y=gras_bench_plot["Rank_global"],
                    mode="lines+markers",
                    name=bench_inst,
                    line=dict(color=colors_bench[(i + 1) % len(colors_bench)], width=3),
                    marker=dict(size=10),
                    connectgaps=False,
                    hovertemplate=f"<b>{bench_inst}</b><br>Year: %{{x}}<br>Rank: %{{y}}<extra></extra>"
                ))
        
        fig_bench_gras.update_layout(
            title=f"{bench_subject} - Global Rank Comparison",
            xaxis=dict(title="Year", dtick=1, range=[2020.5, 2025.5]),
            yaxis=dict(title="Global Rank", autorange="reversed"),
            height=500,
            legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5),
            hovermode="x unified"
        )
        
        st.plotly_chart(fig_bench_gras, use_container_width=True)

# Clear all button
if st.session_state.benchmark_institutions:
    if st.button("🗑️ Clear all benchmark institutions"):
        st.session_state.benchmark_institutions = []
        st.rerun()