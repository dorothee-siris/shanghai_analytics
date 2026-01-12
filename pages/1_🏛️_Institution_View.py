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
# HELPER FUNCTIONS
# ============================================================================
def get_default_subjects(gras_inst, max_display=10):
    """Get default subjects to display based on ranking history."""
    all_subjects = gras_inst["Subject"].unique().tolist()
    
    # If 10 or fewer subjects total, display all
    if len(all_subjects) <= max_display:
        return sorted(all_subjects), []
    
    # Otherwise, prioritize by most recent year
    selected = []
    years_desc = sorted(gras_inst["Year"].unique(), reverse=True)
    
    for year in years_desc:
        year_subjects = gras_inst[gras_inst["Year"] == year]["Subject"].tolist()
        for subj in year_subjects:
            if subj not in selected:
                selected.append(subj)
            if len(selected) >= max_display:
                break
        if len(selected) >= max_display:
            break
    
    remaining = [s for s in all_subjects if s not in selected]
    return selected, remaining


def get_context_institutions(df, inst_name, country, year, rank_col, n_above=2, n_below=2, top_n=3):
    """Get top N + institutions ranked just above/below selected institution."""
    country_data = df[
        (df["Country/Region"] == country) & 
        (df["Year"] == year)
    ].sort_values(rank_col).reset_index(drop=True)
    
    if country_data.empty:
        return []
    
    # Get top N
    top_institutions = country_data.head(top_n)["Institution"].tolist()
    
    # Find selected institution's position
    inst_idx = country_data[country_data["Institution"] == inst_name].index
    if len(inst_idx) == 0:
        return top_institutions + [inst_name]
    
    inst_idx = inst_idx[0]
    
    # Get institutions above and below
    above_institutions = []
    below_institutions = []
    
    for i in range(1, n_above + 1):
        if inst_idx - i >= 0:
            above_inst = country_data.iloc[inst_idx - i]["Institution"]
            if above_inst not in top_institutions and above_inst != inst_name:
                above_institutions.append(above_inst)
    
    for i in range(1, n_below + 1):
        if inst_idx + i < len(country_data):
            below_inst = country_data.iloc[inst_idx + i]["Institution"]
            if below_inst not in top_institutions and below_inst != inst_name:
                below_institutions.append(below_inst)
    
    # Combine: top + above + selected + below (remove duplicates)
    result = []
    for inst in top_institutions + above_institutions + [inst_name] + below_institutions:
        if inst not in result:
            result.append(inst)
    
    return result


def add_line_labels(fig, df, x_col, y_col, name_col, year_max):
    """Add institution names at the end of lines."""
    for trace in fig.data:
        inst_name = trace.name
        inst_data = df[df[name_col] == inst_name]
        if not inst_data.empty:
            # Get the last valid point
            last_valid = inst_data[inst_data[y_col].notna()].sort_values(x_col)
            if not last_valid.empty:
                last_row = last_valid.iloc[-1]
                fig.add_annotation(
                    x=last_row[x_col],
                    y=last_row[y_col],
                    text=inst_name[:20] + "..." if len(inst_name) > 20 else inst_name,
                    showarrow=False,
                    xanchor="left",
                    xshift=10,
                    font=dict(size=9),
                    opacity=0.8
                )


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
    st.caption(f"Top 3 in {inst_country} (2025) + 2 above/below selected institution. Hover for details.")
    
    # Get context institutions
    context_institutions = get_context_institutions(
        arwu_df, inst_name, inst_country, 2025, "Region_Rank_recomputed",
        n_above=2, n_below=2, top_n=3
    )
    
    # Get other institutions from same country for manual addition
    all_country_institutions = arwu_df[
        arwu_df["Country/Region"] == inst_country
    ]["Institution"].unique().tolist()
    other_country_institutions = [i for i in all_country_institutions if i not in context_institutions]
    
    additional_arwu = st.multiselect(
        f"Add more institutions from {inst_country}",
        options=sorted(other_country_institutions),
        default=[],
        key="arwu_country_add"
    )
    
    display_institutions = context_institutions + additional_arwu
    
    # Get all data for these institutions
    arwu_country_all = arwu_df[
        (arwu_df["Country/Region"] == inst_country) & 
        (arwu_df["Institution"].isin(display_institutions))
    ].copy()
    
    # Toggle between regional and global rank
    arwu_view = st.radio(
        "View",
        options=["Regional Rank", "World Rank"],
        horizontal=True,
        key="arwu_country_view"
    )
    
    # Grey tones for other institutions
    grey_palette = ["#2d2d2d", "#4a4a4a", "#666666", "#808080", "#999999", "#b3b3b3", "#cccccc"]
    
    fig_arwu_country = go.Figure()
    
    grey_idx = 0
    for institution in display_institutions:
        inst_data = arwu_country_all[arwu_country_all["Institution"] == institution].sort_values("Year")
        inst_plot = inst_data.set_index("Year").reindex(all_years)
        
        is_selected = institution == inst_name
        line_color = "#e74c3c" if is_selected else grey_palette[grey_idx % len(grey_palette)]
        if not is_selected:
            grey_idx += 1
        
        rank_col = "Region_Rank_recomputed" if arwu_view == "Regional Rank" else "Rank_recomputed"
        other_rank_col = "Rank_recomputed" if arwu_view == "Regional Rank" else "Region_Rank_recomputed"
        rank_label = "Regional Rank" if arwu_view == "Regional Rank" else "World Rank"
        other_label = "World Rank" if arwu_view == "Regional Rank" else "Regional Rank"
        
        hover_text = []
        for yr in all_years:
            if yr in inst_data["Year"].values:
                row = inst_data[inst_data["Year"] == yr].iloc[0]
                hover_text.append(
                    f"<b>{institution}</b><br>Year: {yr}<br>{rank_label}: {int(row[rank_col])}<br>{other_label}: {int(row[other_rank_col])}"
                )
            else:
                hover_text.append(None)
        
        fig_arwu_country.add_trace(go.Scatter(
            x=all_years,
            y=inst_plot[rank_col],
            mode="lines+markers",
            name=institution,
            line=dict(color=line_color, width=2),
            marker=dict(size=8),
            connectgaps=False,
            hovertemplate="%{text}<extra></extra>",
            text=hover_text
        ))
    
    y_title = f"Regional Rank ({inst_country})" if arwu_view == "Regional Rank" else "World Rank"
    
    fig_arwu_country.update_layout(
        title=f"{arwu_view} Evolution - {inst_country}",
        xaxis=dict(title="Year", dtick=1, range=[2016.5, 2025.5]),
        yaxis=dict(title=y_title, autorange="reversed"),
        height=500,
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.12,
            xanchor="center",
            x=0.5,
            font=dict(size=9)
        ),
        hovermode="closest"
    )
    
    st.plotly_chart(fig_arwu_country, use_container_width=True)

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
    
    gras_pivot = gras_inst.pivot_table(
        index="Subject",
        columns="Year",
        values="Rank_global",
        aggfunc="first"
    ).reset_index()
    
    gras_years = sorted(gras_inst["Year"].unique(), reverse=True)
    for yr in gras_years:
        if yr in gras_pivot.columns:
            gras_pivot = gras_pivot.sort_values(yr, na_position="last")
            break
    
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
    default_subjects, other_subjects = get_default_subjects(gras_inst, max_display=10)
    
    # Determine which subjects are ranked in 2025
    subjects_in_2025 = gras_inst[gras_inst["Year"] == 2025]["Subject"].tolist()
    
    # Multiselect with default subjects
    all_inst_subjects = sorted(gras_inst["Subject"].unique().tolist())
    
    display_subjects = st.multiselect(
        "Subjects to display (add or remove)",
        options=all_inst_subjects,
        default=default_subjects,
        key="gras_subjects_display"
    )
    
    st.caption("━━ Plain line: ranked in 2025 | ┅┅ Dotted line: not ranked in 2025")
    
    gras_top = gras_inst[gras_inst["Subject"].isin(display_subjects)].copy()
    
    fig_gras_evo = go.Figure()
    colors = px.colors.qualitative.Plotly
    all_gras_years = list(range(2021, 2026))
    
    for i, subject in enumerate(display_subjects):
        subj_data = gras_top[gras_top["Subject"] == subject].sort_values("Year")
        subj_plot = subj_data.set_index("Year").reindex(all_gras_years)
        
        is_in_2025 = subject in subjects_in_2025
        line_dash = "solid" if is_in_2025 else "dot"
        
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
    st.caption(f"Top 3 in {inst_country} (2025) + 2 above/below selected institution. Hover for details.")
    st.caption("━━ Plain line: ranked in 2025 | ┅┅ Dotted line: not ranked in 2025")
    
    inst_subjects = sorted(gras_inst["Subject"].unique().tolist())
    
    selected_subject = st.selectbox(
        "Select subject for country comparison",
        options=inst_subjects,
        index=0 if inst_subjects else None
    )
    
    if selected_subject:
        # Get context institutions for this subject
        gras_context = get_context_institutions(
            gras_df[gras_df["Subject"] == selected_subject],
            inst_name, inst_country, 2025, "Rank_region",
            n_above=2, n_below=2, top_n=3
        )
        
        # Get other institutions from same country for this subject
        all_gras_country = gras_df[
            (gras_df["Country/Region"] == inst_country) &
            (gras_df["Subject"] == selected_subject)
        ]["Institution"].unique().tolist()
        other_gras_country = [i for i in all_gras_country if i not in gras_context]
        
        additional_gras_country = st.multiselect(
            f"Add more institutions from {inst_country}",
            options=sorted(other_gras_country),
            default=[],
            key="gras_country_add"
        )
        
        gras_display_institutions = gras_context + additional_gras_country
        
        gras_country_all = gras_df[
            (gras_df["Country/Region"] == inst_country) & 
            (gras_df["Subject"] == selected_subject) &
            (gras_df["Institution"].isin(gras_display_institutions))
        ].copy()
        
        if not gras_country_all.empty:
            # Get institutions ranked in 2025 for this subject
            gras_2025_institutions = gras_df[
                (gras_df["Subject"] == selected_subject) &
                (gras_df["Year"] == 2025)
            ]["Institution"].tolist()
            
            # Toggle between regional and global rank
            gras_view = st.radio(
                "View",
                options=["Regional Rank", "Global Rank"],
                horizontal=True,
                key="gras_country_view"
            )
            
            # Grey tones for other institutions
            grey_palette = ["#2d2d2d", "#4a4a4a", "#666666", "#808080", "#999999", "#b3b3b3", "#cccccc"]
            
            fig_gras_country = go.Figure()
            
            grey_idx = 0
            for institution in gras_display_institutions:
                inst_subj_data = gras_country_all[gras_country_all["Institution"] == institution].sort_values("Year")
                inst_subj_plot = inst_subj_data.set_index("Year").reindex(all_gras_years)
                
                is_selected = institution == inst_name
                is_in_2025 = institution in gras_2025_institutions
                line_color = "#e74c3c" if is_selected else grey_palette[grey_idx % len(grey_palette)]
                line_dash = "solid" if is_in_2025 else "dot"
                if not is_selected:
                    grey_idx += 1
                
                rank_col = "Rank_region" if gras_view == "Regional Rank" else "Rank_global"
                other_rank_col = "Rank_global" if gras_view == "Regional Rank" else "Rank_region"
                rank_label = "Regional Rank" if gras_view == "Regional Rank" else "Global Rank"
                other_label = "Global Rank" if gras_view == "Regional Rank" else "Regional Rank"
                
                hover_text = []
                for yr in all_gras_years:
                    if yr in inst_subj_data["Year"].values:
                        row = inst_subj_data[inst_subj_data["Year"] == yr].iloc[0]
                        regional_rank = int(row["Rank_region"]) if pd.notna(row.get("Rank_region")) else "N/A"
                        global_rank = int(row["Rank_global"]) if pd.notna(row.get("Rank_global")) else "N/A"
                        hover_text.append(
                            f"<b>{institution}</b><br>Year: {yr}<br>{rank_label}: {regional_rank if gras_view == 'Regional Rank' else global_rank}<br>{other_label}: {global_rank if gras_view == 'Regional Rank' else regional_rank}"
                        )
                    else:
                        hover_text.append(None)
                
                fig_gras_country.add_trace(go.Scatter(
                    x=all_gras_years,
                    y=inst_subj_plot[rank_col],
                    mode="lines+markers",
                    name=institution,
                    line=dict(color=line_color, width=2, dash=line_dash),
                    marker=dict(size=8),
                    connectgaps=False,
                    hovertemplate="%{text}<extra></extra>",
                    text=hover_text
                ))
            
            y_title = f"Regional Rank ({inst_country})" if gras_view == "Regional Rank" else "Global Rank"
            
            fig_gras_country.update_layout(
                title=f"{selected_subject} - {gras_view} Evolution",
                xaxis=dict(title="Year", dtick=1, range=[2020.5, 2025.5]),
                yaxis=dict(title=y_title, autorange="reversed"),
                height=500,
                legend=dict(
                    orientation="h",
                    yanchor="top",
                    y=-0.12,
                    xanchor="center",
                    x=0.5,
                    font=dict(size=9)
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
        cols = st.columns(min(len(st.session_state.benchmark_institutions), 4))
        for i, bench_inst in enumerate(st.session_state.benchmark_institutions):
            with cols[i % 4]:
                if st.button(f"❌ {bench_inst[:25]}...", key=f"remove_{bench_inst}"):
                    st.session_state.benchmark_institutions.remove(bench_inst)
                    st.rerun()

# Subject selector for GRAS benchmark - only subjects where selected institution appears
if benchmark_type == "GRAS Subject":
    if gras_inst.empty:
        st.warning(f"{inst_name} has no GRAS rankings to compare.")
        bench_subject = None
    else:
        inst_subjects_benchmark = sorted(gras_inst["Subject"].unique().tolist())
        default_subj_idx = 0
        
        bench_subject = st.selectbox(
            "Select subject to compare (only subjects where institution is ranked)",
            options=inst_subjects_benchmark,
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
    elif bench_subject:
        fig_bench_gras = go.Figure()
        all_gras_years = list(range(2021, 2026))
        colors_bench = ["#1f77b4", "#e74c3c", "#2ca02c", "#9467bd", "#ff7f0e", "#8c564b", "#17becf", "#bcbd22"]
        
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

if st.session_state.benchmark_institutions:
    if st.button("🗑️ Clear all benchmark institutions"):
        st.session_state.benchmark_institutions = []
        st.rerun()