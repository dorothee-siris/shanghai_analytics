"""
Institution View - Detailed analysis of a specific institution's rankings
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sys
from pathlib import Path
from datetime import datetime
from io import BytesIO

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils import load_arwu, load_gras, get_institution_list, search_institutions, label_institution

st.set_page_config(page_title="Institution View", page_icon="🏛️", layout="wide")
st.title("🏛️ Institution View")

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================
def get_download_filename(title: str) -> str:
    """Generate filename with timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in title)
    safe_title = safe_title.replace(' ', '_')[:50]
    return f"{safe_title}_{timestamp}.xlsx"


def create_download_button(df: pd.DataFrame, title: str, key: str):
    """Create a download button for dataframe as Excel."""
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Data')
    buffer.seek(0)
    
    st.download_button(
        label="📥 Download Excel",
        data=buffer,
        file_name=get_download_filename(title),
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=key
    )


def get_default_subjects(gras_inst, max_display=10):
    """Get default subjects to display based on ranking history."""
    all_subjects = gras_inst["Subject"].unique().tolist()
    
    if len(all_subjects) <= max_display:
        return sorted(all_subjects), []
    
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


# ============================================================================
# LOAD DATA
# ============================================================================
arwu_df = load_arwu()
gras_df = load_gras()
institutions_df = get_institution_list()

# ============================================================================
# INSTITUTION SEARCH & SELECTION
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
# INSTITUTION HEADER
# ============================================================================
inst_name = chosen["Institution"]
inst_country = chosen["Country/Region"]
inst_id = chosen.get("Institution_ID", "N/A")

st.markdown("---")
st.header(f"{inst_name}")
st.caption(f"📍 {inst_country} | 🆔 {inst_id}")

# Filter data for this institution (using Institution_ID if available, else name)
if "Institution_ID" in arwu_df.columns and pd.notna(inst_id) and inst_id != "N/A":
    arwu_inst = arwu_df[arwu_df["Institution_ID"] == inst_id].sort_values("Year")
    gras_inst = gras_df[gras_df["Institution_ID"] == inst_id].sort_values("Year")
else:
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
    # ---------- ARWU Rank Evolution ----------
    st.markdown("### Rank Evolution")
    
    # Toggle for global vs regional
    arwu_rank_view = st.radio(
        "View",
        options=["World Rank", "Regional Rank"],
        horizontal=True,
        key="arwu_rank_view"
    )
    
    all_years = list(range(2017, 2026))
    
    # Determine rank column and calculate axis range
    if arwu_rank_view == "World Rank":
        rank_col = "Rank_recomputed"
        # Global range: 1 to 1000
        y_min, y_max = 1, 1000
        y_title = "World Rank"
    else:
        rank_col = "Region_Rank_recomputed"
        # Regional range: 1 to max regional rank for this country across all years
        country_data = arwu_df[arwu_df["Country/Region"] == inst_country]
        y_max = int(country_data["Region_Rank_recomputed"].max()) if not country_data.empty else 100
        y_min = 1
        y_title = f"Regional Rank ({inst_country})"
    
    # Prepare plot data
    arwu_plot = arwu_inst.set_index("Year").reindex(all_years).reset_index()
    arwu_plot.columns = ["Year"] + list(arwu_plot.columns[1:])
    
    # Create hover text with score
    hover_texts = []
    for _, row in arwu_plot.iterrows():
        if pd.notna(row.get(rank_col)):
            score = row.get("Score_normalized", "N/A")
            score_str = f"{score:.1f}" if isinstance(score, (int, float)) and pd.notna(score) else "N/A"
            world_rank = int(row.get("Rank_recomputed")) if pd.notna(row.get("Rank_recomputed")) else "N/A"
            regional_rank = int(row.get("Region_Rank_recomputed")) if pd.notna(row.get("Region_Rank_recomputed")) else "N/A"
            hover_texts.append(
                f"<b>{inst_name}</b><br>"
                f"Year: {int(row['Year'])}<br>"
                f"World Rank: {world_rank}<br>"
                f"Regional Rank: {regional_rank}<br>"
                f"Score: {score_str}"
            )
        else:
            hover_texts.append(None)
    
    fig_arwu_rank = go.Figure()
    
    fig_arwu_rank.add_trace(go.Scatter(
        x=arwu_plot["Year"],
        y=arwu_plot[rank_col],
        mode="lines+markers",
        name=inst_name,
        line=dict(color="#1f77b4", width=3),
        marker=dict(size=12, color="#1f77b4"),
        connectgaps=False,
        hovertemplate="%{text}<extra></extra>",
        text=hover_texts
    ))
    
    fig_arwu_rank.update_layout(
        title=f"ARWU {arwu_rank_view} Evolution",
        xaxis=dict(
            title="Year",
            dtick=1,
            range=[2016.5, 2025.5]
        ),
        yaxis=dict(
            title=y_title,
            autorange="reversed",
            range=[y_max, y_min],  # Reversed: max at bottom, min at top
            dtick=max(1, (y_max - y_min) // 10)
        ),
        height=600,
        hovermode="closest",
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.15,
            xanchor="center",
            x=0.5,
            font=dict(size=11)
        ),
        margin=dict(b=100)
    )
    
    st.plotly_chart(fig_arwu_rank, use_container_width=True)
    
    # Download button for rank evolution
    rank_download_df = arwu_inst[["Year", "Institution", "Country/Region", "Rank_recomputed", "Region_Rank_recomputed", "Score_normalized"]].copy()
    rank_download_df.columns = ["Year", "Institution", "Country/Region", "World Rank", "Regional Rank", "Score"]
    create_download_button(rank_download_df, f"ARWU_Rank_Evolution_{inst_name}", "dl_arwu_rank")
    
    # ---------- ARWU Indicators Evolution ----------
    st.markdown("### Indicators Score Evolution")
    
    # Identify indicator columns
    indicator_cols = ["Alumni", "Award", "HiCi", "N&S", "PUB", "PCP"]
    available_indicators = [col for col in indicator_cols if col in arwu_inst.columns]
    
    if available_indicators:
        fig_indicators = go.Figure()
        
        colors_indicators = px.colors.qualitative.Set2
        
        for i, indicator in enumerate(available_indicators):
            indicator_data = arwu_inst.set_index("Year").reindex(all_years)
            
            fig_indicators.add_trace(go.Scatter(
                x=all_years,
                y=indicator_data[indicator],
                mode="lines+markers",
                name=indicator,
                line=dict(color=colors_indicators[i % len(colors_indicators)], width=2),
                marker=dict(size=8),
                connectgaps=False,
                hovertemplate=f"<b>{indicator}</b><br>Year: %{{x}}<br>Score: %{{y:.1f}}<extra></extra>"
            ))
        
        fig_indicators.update_layout(
            title="ARWU Indicator Scores Over Time",
            xaxis=dict(
                title="Year",
                dtick=1,
                range=[2016.5, 2025.5]
            ),
            yaxis=dict(
                title="Indicator Score",
                range=[0, 105]
            ),
            height=500,
            hovermode="x unified",
            legend=dict(
                orientation="h",
                yanchor="top",
                y=-0.15,
                xanchor="center",
                x=0.5,
                font=dict(size=11)
            ),
            margin=dict(b=100)
        )
        
        st.plotly_chart(fig_indicators, use_container_width=True)
        
        # Download button for indicators
        indicators_download_df = arwu_inst[["Year", "Institution"] + available_indicators].copy()
        create_download_button(indicators_download_df, f"ARWU_Indicators_{inst_name}", "dl_arwu_indicators")
    else:
        st.info("No indicator data available for this institution.")

# ============================================================================
# GRAS SECTION
# ============================================================================
st.markdown("---")
st.markdown("## 📚 GRAS Subject Rankings")

if gras_inst.empty:
    st.warning(f"{inst_name} is not ranked in any GRAS subject (2021-2025).")
else:
    # ---------- GRAS Overview Stats ----------
    st.markdown("### Rankings Overview")
    
    # Calculate statistics
    subjects_2025 = gras_inst[gras_inst["Year"] == 2025]["Subject"].nunique()
    subjects_total = gras_inst["Subject"].nunique()
    
    st.markdown(f"""
    📌 **{inst_name}** appears in **{subjects_2025} subject ranking(s)** in 2025, 
    and has been ranked in **{subjects_total} unique subject(s)** across all years (2021-2025).
    """)
    
    # ---------- GRAS Rankings Table ----------
    # Pivot table: subjects x years
    gras_pivot = gras_inst.pivot_table(
        index="Subject",
        columns="Year",
        values="Rank_global",
        aggfunc="first"
    ).reset_index()
    
    # Add Field column
    subject_to_field = gras_inst[["Subject", "Field"]].drop_duplicates().set_index("Subject")["Field"].to_dict()
    gras_pivot.insert(0, "Field", gras_pivot["Subject"].map(subject_to_field))
    
    # Sort by Field, then by 2025 rank (or latest available)
    gras_years = sorted([c for c in gras_pivot.columns if isinstance(c, int)], reverse=True)
    gras_pivot = gras_pivot.sort_values(["Field"] + gras_years[:1], ascending=[True, True], na_position="last")
    
    # Format for display
    gras_display = gras_pivot.copy()
    year_cols = [c for c in gras_display.columns if isinstance(c, int)]
    for col in year_cols:
        gras_display[col] = gras_display[col].apply(lambda x: int(x) if pd.notna(x) else "—")
    
    st.dataframe(
        gras_display,
        use_container_width=True,
        hide_index=True,
        height=min(500, len(gras_display) * 35 + 50)
    )
    
    # Download button for rankings table
    create_download_button(gras_pivot, f"GRAS_Rankings_Overview_{inst_name}", "dl_gras_table")
    
    # ---------- GRAS Indicators Evolution ----------
    st.markdown("### Indicators Score Evolution")
    
    # Subject selector for indicators
    indicator_subjects = sorted(gras_inst["Subject"].unique().tolist())
    selected_indicator_subject = st.selectbox(
        "Select subject to view indicators",
        options=indicator_subjects,
        index=0,
        key="gras_indicator_subject"
    )
    
    # Filter to selected subject
    gras_subject_data = gras_inst[gras_inst["Subject"] == selected_indicator_subject].copy()
    
    # Explanation of indicators
    with st.expander("ℹ️ About GRAS Indicators (click to expand)"):
        st.markdown("""
        **GRAS methodology changed in 2024.** The new indicators are:
        
        | Indicator | Full Name | Description |
        |-----------|-----------|-------------|
        | **WCF** | World-Class Faculty | New in 2024. Aggregation of 4 sub-indicators: (1) Faculty winning Nobel Prizes, Fields Medals, Turing Awards, etc.; (2) Highly Cited Researchers; (3) Faculty with high H-index; (4) Faculty with publications in top journals |
        | **WCO** | World-Class Outputs | Replaces TOP + AWARD. Combines: (1) Papers in top journals/conferences; (2) Award-winning research outputs; (3) Highly cited papers |
        | **HQR** | High Quality Research | Continuation of Q1. Percentage of publications in Q1 journals |
        | **RI** | Research Impact | Continuation of CNCI. Category Normalized Citation Impact |
        | **IC** | International Collaboration | Continuation of IC. Percentage of papers with international co-authors |
        
        **Continuity with pre-2024 indicators:**
        - HQR = Q1 (continuous line)
        - RI = CNCI (continuous line)  
        - IC = IC (continuous line)
        - WCO ≈ TOP + AWARD (shown together for comparison)
        - WCF = new indicator (no historical data)
        """)
    
    # Check available indicator columns
    # Old indicators (pre-2024)
    old_indicators = {
        "Q1_old": "Q1",
        "CNCI_old": "CNCI", 
        "IC_old": "IC (old)",
        "TOP_old": "TOP",
        "AWARD_old": "AWARD"
    }
    # New indicators (2024+)
    new_indicators = {
        "WCF_new": "WCF",
        "WCO_new": "WCO",
        "HQR_new": "HQR",
        "RI_new": "RI",
        "IC_new": "IC"
    }
    
    all_gras_years = list(range(2021, 2026))
    gras_indicators_data = gras_subject_data.copy()
    
    # We'll create 4 charts: HQR/Q1, RI/CNCI, IC, and WCO/TOP/AWARD (+WCF separate)
    
    col_left, col_right = st.columns(2)
    
    # --- Chart 1: HQR / Q1 (continuous) ---
    with col_left:
        st.markdown("**HQR (High Quality Research) / Q1**")
        
        fig_hqr = go.Figure()
        
        # Combine Q1_old (2021-2023) and HQR_new (2024-2025)
        hqr_values = []
        for year in all_gras_years:
            year_data = gras_indicators_data[gras_indicators_data["Year"] == year]
            if not year_data.empty:
                row = year_data.iloc[0]
                if year < 2024 and "Q1_old" in row and pd.notna(row.get("Q1_old")):
                    hqr_values.append(row["Q1_old"])
                elif year >= 2024 and "HQR_new" in row and pd.notna(row.get("HQR_new")):
                    hqr_values.append(row["HQR_new"])
                else:
                    hqr_values.append(None)
            else:
                hqr_values.append(None)
        
        fig_hqr.add_trace(go.Scatter(
            x=all_gras_years,
            y=hqr_values,
            mode="lines+markers",
            name="HQR / Q1",
            line=dict(color="#9467bd", width=2),
            marker=dict(size=8),
            connectgaps=False
        ))
        
        fig_hqr.update_layout(
            xaxis=dict(title="Year", dtick=1),
            yaxis=dict(title="Score", range=[0, 105]),
            height=300,
            margin=dict(t=30, b=50),
            showlegend=False
        )
        st.plotly_chart(fig_hqr, use_container_width=True)
    
    # --- Chart 2: RI / CNCI (continuous) ---
    with col_right:
        st.markdown("**RI (Research Impact) / CNCI**")
        
        fig_ri = go.Figure()
        
        ri_values = []
        for year in all_gras_years:
            year_data = gras_indicators_data[gras_indicators_data["Year"] == year]
            if not year_data.empty:
                row = year_data.iloc[0]
                if year < 2024 and "CNCI_old" in row and pd.notna(row.get("CNCI_old")):
                    ri_values.append(row["CNCI_old"])
                elif year >= 2024 and "RI_new" in row and pd.notna(row.get("RI_new")):
                    ri_values.append(row["RI_new"])
                else:
                    ri_values.append(None)
            else:
                ri_values.append(None)
        
        fig_ri.add_trace(go.Scatter(
            x=all_gras_years,
            y=ri_values,
            mode="lines+markers",
            name="RI / CNCI",
            line=dict(color="#ff7f0e", width=2),
            marker=dict(size=8),
            connectgaps=False
        ))
        
        fig_ri.update_layout(
            xaxis=dict(title="Year", dtick=1),
            yaxis=dict(title="Score", range=[0, 105]),
            height=300,
            margin=dict(t=30, b=50),
            showlegend=False
        )
        st.plotly_chart(fig_ri, use_container_width=True)
    
    col_left2, col_right2 = st.columns(2)
    
    # --- Chart 3: IC (continuous) ---
    with col_left2:
        st.markdown("**IC (International Collaboration)**")
        
        fig_ic = go.Figure()
        
        ic_values = []
        for year in all_gras_years:
            year_data = gras_indicators_data[gras_indicators_data["Year"] == year]
            if not year_data.empty:
                row = year_data.iloc[0]
                if year < 2024 and "IC_old" in row and pd.notna(row.get("IC_old")):
                    ic_values.append(row["IC_old"])
                elif year >= 2024 and "IC_new" in row and pd.notna(row.get("IC_new")):
                    ic_values.append(row["IC_new"])
                else:
                    ic_values.append(None)
            else:
                ic_values.append(None)
        
        fig_ic.add_trace(go.Scatter(
            x=all_gras_years,
            y=ic_values,
            mode="lines+markers",
            name="IC",
            line=dict(color="#2ca02c", width=2),
            marker=dict(size=8),
            connectgaps=False
        ))
        
        fig_ic.update_layout(
            xaxis=dict(title="Year", dtick=1),
            yaxis=dict(title="Score", range=[0, 105]),
            height=300,
            margin=dict(t=30, b=50),
            showlegend=False
        )
        st.plotly_chart(fig_ic, use_container_width=True)
    
    # --- Chart 4: WCF (new, 2024+ only) ---
    with col_right2:
        st.markdown("**WCF (World-Class Faculty)** — *New in 2024*")
        
        fig_wcf = go.Figure()
        
        wcf_values = []
        for year in all_gras_years:
            year_data = gras_indicators_data[gras_indicators_data["Year"] == year]
            if not year_data.empty and year >= 2024:
                row = year_data.iloc[0]
                if "WCF_new" in row and pd.notna(row.get("WCF_new")):
                    wcf_values.append(row["WCF_new"])
                else:
                    wcf_values.append(None)
            else:
                wcf_values.append(None)
        
        fig_wcf.add_trace(go.Scatter(
            x=all_gras_years,
            y=wcf_values,
            mode="lines+markers",
            name="WCF",
            line=dict(color="#e377c2", width=2),
            marker=dict(size=8),
            connectgaps=False
        ))
        
        fig_wcf.update_layout(
            xaxis=dict(title="Year", dtick=1),
            yaxis=dict(title="Score", range=[0, 105]),
            height=300,
            margin=dict(t=30, b=50),
            showlegend=False
        )
        st.plotly_chart(fig_wcf, use_container_width=True)
    
    # --- Chart 5: WCO / TOP / AWARD (full width) ---
    st.markdown("**WCO (World-Class Outputs)** — *Replaces TOP + AWARD*")
    st.caption("TOP and AWARD shown in dotted lines for historical comparison. WCO in solid line.")
    
    fig_wco = go.Figure()
    
    # TOP (dotted, blue)
    top_values = []
    for year in all_gras_years:
        year_data = gras_indicators_data[gras_indicators_data["Year"] == year]
        if not year_data.empty and year < 2024:
            row = year_data.iloc[0]
            if "TOP_old" in row and pd.notna(row.get("TOP_old")):
                top_values.append(row["TOP_old"])
            else:
                top_values.append(None)
        else:
            top_values.append(None)
    
    fig_wco.add_trace(go.Scatter(
        x=all_gras_years,
        y=top_values,
        mode="lines+markers",
        name="TOP (pre-2024)",
        line=dict(color="#1f77b4", width=2, dash="dot"),
        marker=dict(size=8),
        connectgaps=False
    ))
    
    # AWARD (dotted, green)
    award_values = []
    for year in all_gras_years:
        year_data = gras_indicators_data[gras_indicators_data["Year"] == year]
        if not year_data.empty and year < 2024:
            row = year_data.iloc[0]
            if "AWARD_old" in row and pd.notna(row.get("AWARD_old")):
                award_values.append(row["AWARD_old"])
            else:
                award_values.append(None)
        else:
            award_values.append(None)
    
    fig_wco.add_trace(go.Scatter(
        x=all_gras_years,
        y=award_values,
        mode="lines+markers",
        name="AWARD (pre-2024)",
        line=dict(color="#2ca02c", width=2, dash="dot"),
        marker=dict(size=8),
        connectgaps=False
    ))
    
    # WCO (solid, teal/blue-green)
    wco_values = []
    for year in all_gras_years:
        year_data = gras_indicators_data[gras_indicators_data["Year"] == year]
        if not year_data.empty and year >= 2024:
            row = year_data.iloc[0]
            if "WCO_new" in row and pd.notna(row.get("WCO_new")):
                wco_values.append(row["WCO_new"])
            else:
                wco_values.append(None)
        else:
            wco_values.append(None)
    
    fig_wco.add_trace(go.Scatter(
        x=all_gras_years,
        y=wco_values,
        mode="lines+markers",
        name="WCO (2024+)",
        line=dict(color="#17becf", width=3),  # Teal/cyan - between blue and green
        marker=dict(size=10),
        connectgaps=False
    ))
    
    fig_wco.update_layout(
        xaxis=dict(title="Year", dtick=1),
        yaxis=dict(title="Score", range=[0, 105]),
        height=350,
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.18,
            xanchor="center",
            x=0.5,
            font=dict(size=11)
        ),
        margin=dict(b=80)
    )
    st.plotly_chart(fig_wco, use_container_width=True)
    
    # Download button for GRAS indicators
    gras_ind_download = gras_indicators_data[["Year", "Subject", "Field"]].copy()
    for col in ["Q1_old", "CNCI_old", "IC_old", "TOP_old", "AWARD_old", "WCF_new", "WCO_new", "HQR_new", "RI_new", "IC_new"]:
        if col in gras_indicators_data.columns:
            gras_ind_download[col] = gras_indicators_data[col]
    create_download_button(gras_ind_download, f"GRAS_Indicators_{selected_indicator_subject}_{inst_name}", "dl_gras_indicators")
    
    # ---------- GRAS Subject Rank Evolution ----------
    st.markdown("### Subject Rank Evolution")
    
    latest_gras_year = gras_inst["Year"].max()
    default_subjects, other_subjects = get_default_subjects(gras_inst, max_display=10)
    
    # Determine which subjects are ranked in 2025
    subjects_in_2025 = gras_inst[gras_inst["Year"] == 2025]["Subject"].tolist()
    
    # All subjects for selection
    all_inst_subjects = sorted(gras_inst["Subject"].unique().tolist())
    
    # Multiselect for subjects
    display_subjects = st.multiselect(
        "Subjects to display (add or remove)",
        options=all_inst_subjects,
        default=default_subjects,
        key="gras_subjects_display"
    )
    
    st.caption("━━ Plain line: ranked in 2025 | ┅┅ Dotted line: not ranked in 2025")
    
    if display_subjects:
        gras_evolution = gras_inst[gras_inst["Subject"].isin(display_subjects)].copy()
        
        fig_gras_evo = go.Figure()
        colors = px.colors.qualitative.Plotly
        all_gras_years = list(range(2021, 2026))
        
        for i, subject in enumerate(display_subjects):
            subj_data = gras_evolution[gras_evolution["Subject"] == subject].sort_values("Year")
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
                hovertemplate=f"<b>{subject}</b><br>Year: %{{x}}<br>Global Rank: %{{y}}<extra></extra>"
            ))
        
        fig_gras_evo.update_layout(
            title="GRAS Global Rank by Subject",
            xaxis=dict(
                title="Year",
                dtick=1,
                range=[2020.5, 2025.5]
            ),
            yaxis=dict(
                title="Global Rank",
                autorange="reversed"
            ),
            height=550,
            hovermode="closest",
            legend=dict(
                orientation="h",
                yanchor="top",
                y=-0.18,
                xanchor="center",
                x=0.5,
                font=dict(size=11)
            ),
            margin=dict(b=120)
        )
        
        st.plotly_chart(fig_gras_evo, use_container_width=True)
        
        # Download button for subject evolution
        gras_evo_download = gras_evolution[["Year", "Subject", "Field", "Rank_global", "Rank_region", "Score_recomputed"]].copy()
        gras_evo_download.columns = ["Year", "Subject", "Field", "Global Rank", "Regional Rank", "Score"]
        create_download_button(gras_evo_download, f"GRAS_Subject_Evolution_{inst_name}", "dl_gras_evolution")
    else:
        st.info("Select at least one subject to display the evolution chart.")