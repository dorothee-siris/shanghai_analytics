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
    col1, col2 = st.columns([1.2, 1])
    
    # ---------- ARWU Evolution Line Plot ----------
    with col1:
        st.markdown("### Rank Evolution")
        
        # Create full year range to show gaps
        all_years = list(range(2017, 2026))
        arwu_plot = arwu_inst.set_index("Year").reindex(all_years).reset_index()
        arwu_plot.columns = ["Year"] + list(arwu_plot.columns[1:])
        
        fig_arwu_evo = go.Figure()
        
        # Add line trace (will have gaps where data is NaN)
        fig_arwu_evo.add_trace(go.Scatter(
            x=arwu_plot["Year"],
            y=arwu_plot["Rank_recomputed"],
            mode="lines+markers",
            name=inst_name,
            line=dict(color="#1f77b4", width=3),
            marker=dict(size=10, color="#1f77b4"),
            connectgaps=False  # Important: shows breaks in the line
        ))
        
        # Add score as secondary info on hover
        fig_arwu_evo.update_traces(
            hovertemplate="<b>Year:</b> %{x}<br><b>Rank:</b> %{y}<extra></extra>"
        )
        
        fig_arwu_evo.update_layout(
            title=f"ARWU World Rank Evolution",
            xaxis=dict(title="Year", dtick=1, range=[2016.5, 2025.5]),
            yaxis=dict(title="World Rank", autorange="reversed"),
            height=450,
            hovermode="x unified"
        )
        
        st.plotly_chart(fig_arwu_evo, use_container_width=True)
    
    # ---------- ARWU Country Positioning ----------
    with col2:
        st.markdown("### Country Positioning")
        
        latest_year = arwu_inst["Year"].max()
        arwu_country = arwu_df[
            (arwu_df["Country/Region"] == inst_country) & 
            (arwu_df["Year"] == latest_year)
        ].sort_values("Rank_recomputed")
        
        # Get top 5
        top5 = arwu_country.head(5).copy()
        inst_in_top5 = inst_name in top5["Institution"].values
        
        # Add selected institution if not in top 5
        if not inst_in_top5:
            inst_row = arwu_country[arwu_country["Institution"] == inst_name].copy()
            if not inst_row.empty:
                display_df = pd.concat([top5, inst_row])
            else:
                display_df = top5
        else:
            display_df = top5
        
        display_df = display_df.copy()
        display_df["Highlight"] = display_df["Institution"].apply(
            lambda x: "Selected Institution" if x == inst_name else "Other"
        )
        
        # Create horizontal bar chart
        fig_country = go.Figure()
        
        # Sort for display (highest score at top)
        display_df = display_df.sort_values("Score_normalized", ascending=True)
        
        colors = ["#e74c3c" if x == inst_name else "#3498db" for x in display_df["Institution"]]
        
        fig_country.add_trace(go.Bar(
            y=display_df["Institution"],
            x=display_df["Score_normalized"],
            orientation="h",
            marker_color=colors,
            text=display_df["Rank_recomputed"].astype(int).astype(str) + " (world)",
            textposition="inside",
            hovertemplate="<b>%{y}</b><br>Score: %{x:.1f}<br>World Rank: %{text}<extra></extra>"
        ))
        
        fig_country.update_layout(
            title=f"Top institutions in {inst_country} ({latest_year})",
            xaxis=dict(title="ARWU Score"),
            yaxis=dict(title=""),
            height=450,
            showlegend=False
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
    # Get top 10 subjects from latest year (best ranked)
    latest_gras_year = gras_inst["Year"].max()
    gras_latest = gras_inst[gras_inst["Year"] == latest_gras_year].nsmallest(10, "Rank_global")
    top_subjects = gras_latest["Subject"].tolist()
    
    col1, col2 = st.columns([1.2, 1])
    
    # ---------- GRAS Evolution Multi-Line Plot ----------
    with col1:
        st.markdown("### Subject Rank Evolution")
        st.caption(f"Showing top 10 subjects from {latest_gras_year}. Click legend items to show/hide.")
        
        # Filter to top subjects
        gras_top = gras_inst[gras_inst["Subject"].isin(top_subjects)].copy()
        
        # Create figure with one trace per subject
        fig_gras_evo = go.Figure()
        
        # Color palette
        colors = px.colors.qualitative.Plotly
        
        for i, subject in enumerate(top_subjects):
            subj_data = gras_top[gras_top["Subject"] == subject].sort_values("Year")
            
            # Reindex to show gaps
            all_gras_years = list(range(2021, 2026))
            subj_plot = subj_data.set_index("Year").reindex(all_gras_years)
            
            fig_gras_evo.add_trace(go.Scatter(
                x=all_gras_years,
                y=subj_plot["Rank_global"],
                mode="lines+markers",
                name=subject,
                line=dict(color=colors[i % len(colors)], width=2),
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
    with col2:
        st.markdown("### Country Positioning by Subject")
        
        # Subject selector
        subjects_available = sorted(gras_inst["Subject"].unique().tolist())
        default_idx = 0
        if top_subjects and top_subjects[0] in subjects_available:
            default_idx = subjects_available.index(top_subjects[0])
        
        selected_subject = st.selectbox(
            "Select subject for country comparison",
            options=subjects_available,
            index=default_idx
        )
        
        if selected_subject:
            gras_country = gras_df[
                (gras_df["Country/Region"] == inst_country) & 
                (gras_df["Year"] == latest_gras_year) &
                (gras_df["Subject"] == selected_subject)
            ].sort_values("Rank_global")
            
            # Get top 5
            top5_gras = gras_country.head(5).copy()
            inst_in_top5_gras = inst_name in top5_gras["Institution"].values
            
            # Add selected institution if not in top 5
            if not inst_in_top5_gras:
                inst_row_gras = gras_country[gras_country["Institution"] == inst_name].copy()
                if not inst_row_gras.empty:
                    display_gras = pd.concat([top5_gras, inst_row_gras])
                else:
                    display_gras = top5_gras
            else:
                display_gras = top5_gras
            
            if not display_gras.empty:
                display_gras = display_gras.copy()
                display_gras = display_gras.sort_values("Score_recomputed", ascending=True)
                
                colors_gras = ["#e74c3c" if x == inst_name else "#27ae60" for x in display_gras["Institution"]]
                
                fig_gras_country = go.Figure()
                
                fig_gras_country.add_trace(go.Bar(
                    y=display_gras["Institution"],
                    x=display_gras["Score_recomputed"],
                    orientation="h",
                    marker_color=colors_gras,
                    text=display_gras["Rank_global"].astype(int).astype(str) + " (world)",
                    textposition="inside",
                    hovertemplate="<b>%{y}</b><br>Score: %{x:.1f}<br>World Rank: %{text}<extra></extra>"
                ))
                
                fig_gras_country.update_layout(
                    title=f"{selected_subject} in {inst_country} ({latest_gras_year})",
                    xaxis=dict(title="GRAS Score"),
                    yaxis=dict(title=""),
                    height=450,
                    showlegend=False
                )
                
                st.plotly_chart(fig_gras_country, use_container_width=True)
            else:
                st.info(f"No institutions from {inst_country} ranked in {selected_subject}.")

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

col_bench1, col_bench2 = st.columns([1, 2])

with col_bench1:
    st.markdown("#### Select comparison institution")
    q2 = st.text_input(
        "Search second institution",
        placeholder="e.g., MIT, Oxford, Tsinghua...",
        key="benchmark_search"
    )
    
    chosen2 = None
    if q2:
        results2 = search_institutions(institutions_df, q2)
        results2 = results2[results2["Institution"] != inst_name]  # Exclude current
    else:
        results2 = institutions_df.head(0)
    
    if len(results2) > 0:
        options2 = ["— Select —"] + [label_institution(r) for _, r in results2.iterrows()]
        sel2 = st.selectbox("Select", options=options2, index=0, label_visibility="collapsed", key="benchmark_select")
        if sel2 != "— Select —":
            idx2 = options2.index(sel2) - 1
            chosen2 = results2.iloc[idx2]
    
    # Subject selector for GRAS benchmark
    if benchmark_type == "GRAS Subject":
        all_subjects = sorted(gras_df["Subject"].unique().tolist())
        default_subj_idx = 0
        if top_subjects and top_subjects[0] in all_subjects:
            default_subj_idx = all_subjects.index(top_subjects[0])
        
        bench_subject = st.selectbox(
            "Select subject to compare",
            options=all_subjects,
            index=default_subj_idx,
            key="bench_subject"
        )

with col_bench2:
    if benchmark_type == "ARWU Overall":
        if chosen2 is not None:
            inst2_name = chosen2["Institution"]
            arwu_inst2 = arwu_df[arwu_df["Institution"] == inst2_name].sort_values("Year")
            
            if arwu_inst.empty and arwu_inst2.empty:
                st.warning("Neither institution is ranked in ARWU.")
            else:
                # Create comparison plot
                fig_bench = go.Figure()
                
                all_years = list(range(2017, 2026))
                
                # Institution 1
                if not arwu_inst.empty:
                    arwu1_plot = arwu_inst.set_index("Year").reindex(all_years)
                    fig_bench.add_trace(go.Scatter(
                        x=all_years,
                        y=arwu1_plot["Rank_recomputed"],
                        mode="lines+markers",
                        name=inst_name,
                        line=dict(color="#1f77b4", width=3),
                        marker=dict(size=10),
                        connectgaps=False
                    ))
                
                # Institution 2
                if not arwu_inst2.empty:
                    arwu2_plot = arwu_inst2.set_index("Year").reindex(all_years)
                    fig_bench.add_trace(go.Scatter(
                        x=all_years,
                        y=arwu2_plot["Rank_recomputed"],
                        mode="lines+markers",
                        name=inst2_name,
                        line=dict(color="#e74c3c", width=3),
                        marker=dict(size=10),
                        connectgaps=False
                    ))
                
                fig_bench.update_layout(
                    title=f"ARWU Rank Comparison",
                    xaxis=dict(title="Year", dtick=1, range=[2016.5, 2025.5]),
                    yaxis=dict(title="World Rank", autorange="reversed"),
                    height=450,
                    legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
                    hovermode="x unified"
                )
                
                st.plotly_chart(fig_bench, use_container_width=True)
        else:
            st.info("👈 Search and select a second institution to compare ARWU rankings.")
    
    else:  # GRAS Subject
        if gras_inst.empty:
            st.warning(f"{inst_name} has no GRAS rankings.")
        elif chosen2 is not None:
            inst2_name = chosen2["Institution"]
            
            gras_inst1_subj = gras_inst[gras_inst["Subject"] == bench_subject].copy()
            gras_inst2_subj = gras_df[
                (gras_df["Institution"] == inst2_name) & 
                (gras_df["Subject"] == bench_subject)
            ].sort_values("Year").copy()
            
            if gras_inst1_subj.empty and gras_inst2_subj.empty:
                st.warning(f"Neither institution is ranked in {bench_subject}.")
            else:
                fig_bench_gras = go.Figure()
                
                all_gras_years = list(range(2021, 2026))
                
                # Institution 1
                if not gras_inst1_subj.empty:
                    gras1_plot = gras_inst1_subj.set_index("Year").reindex(all_gras_years)
                    fig_bench_gras.add_trace(go.Scatter(
                        x=all_gras_years,
                        y=gras1_plot["Rank_global"],
                        mode="lines+markers",
                        name=inst_name,
                        line=dict(color="#1f77b4", width=3),
                        marker=dict(size=10),
                        connectgaps=False
                    ))
                
                # Institution 2
                if not gras_inst2_subj.empty:
                    gras2_plot = gras_inst2_subj.set_index("Year").reindex(all_gras_years)
                    fig_bench_gras.add_trace(go.Scatter(
                        x=all_gras_years,
                        y=gras2_plot["Rank_global"],
                        mode="lines+markers",
                        name=inst2_name,
                        line=dict(color="#e74c3c", width=3),
                        marker=dict(size=10),
                        connectgaps=False
                    ))
                
                fig_bench_gras.update_layout(
                    title=f"{bench_subject} - Rank Comparison",
                    xaxis=dict(title="Year", dtick=1, range=[2020.5, 2025.5]),
                    yaxis=dict(title="Global Rank", autorange="reversed"),
                    height=450,
                    legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
                    hovermode="x unified"
                )
                
                st.plotly_chart(fig_bench_gras, use_container_width=True)
        else:
            st.info("👈 Search and select a second institution to compare GRAS rankings.")