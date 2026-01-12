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
inst_id = chosen.get("Institution_ID", None)

# If ID not in chosen, try to get it from the data
if pd.isna(inst_id) or inst_id is None:
    if "Institution_ID" in arwu_df.columns:
        arwu_match = arwu_df[arwu_df["Institution"] == inst_name]
        if not arwu_match.empty and pd.notna(arwu_match.iloc[0].get("Institution_ID")):
            inst_id = arwu_match.iloc[0]["Institution_ID"]
    if (pd.isna(inst_id) or inst_id is None) and "Institution_ID" in gras_df.columns:
        gras_match = gras_df[gras_df["Institution"] == inst_name]
        if not gras_match.empty and pd.notna(gras_match.iloc[0].get("Institution_ID")):
            inst_id = gras_match.iloc[0]["Institution_ID"]

inst_id_display = inst_id if pd.notna(inst_id) and inst_id is not None else "N/A"

st.markdown("---")
st.header(f"{inst_name}")
st.caption(f"📍 {inst_country} | 🆔 {inst_id_display}")

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
    st.markdown("### Rank / Score Evolution")
    
    # Toggle for global vs regional vs score
    arwu_rank_view = st.radio(
        "View",
        options=["World Rank", "Regional Rank", "Global Score"],
        horizontal=True,
        key="arwu_rank_view"
    )
    
    all_years = list(range(2017, 2026))
    
    # Prepare plot data
    arwu_plot = arwu_inst.set_index("Year").reindex(all_years).reset_index()
    arwu_plot.columns = ["Year"] + list(arwu_plot.columns[1:])
    
    # Determine column and axis settings based on view
    if arwu_rank_view == "World Rank":
        value_col = "Rank_recomputed"
        y_min, y_max = 1, 1000
        y_title = "World Rank"
        reverse_axis = True
        value_format = lambda x: f"{int(x)}" if pd.notna(x) else ""
    elif arwu_rank_view == "Regional Rank":
        value_col = "Region_Rank_recomputed"
        # Regional range: 1 to max institutions ranked in this country in any single year
        country_data = arwu_df[arwu_df["Country/Region"] == inst_country]
        max_per_year = country_data.groupby("Year")["Region_Rank_recomputed"].max()
        y_max = int(max_per_year.max()) if not max_per_year.empty else 100
        y_min = 1
        y_title = f"Regional Rank ({inst_country})"
        reverse_axis = True
        value_format = lambda x: f"{int(x)}" if pd.notna(x) else ""
    else:  # Global Score
        value_col = "Score_normalized"
        y_min, y_max = 0, 100
        y_title = "Global Score"
        reverse_axis = False
        value_format = lambda x: f"{x:.1f}" if pd.notna(x) else ""
    
    # Create hover text
    hover_texts = []
    text_labels = []
    for _, row in arwu_plot.iterrows():
        if pd.notna(row.get(value_col)):
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
            text_labels.append(value_format(row[value_col]))
        else:
            hover_texts.append(None)
            text_labels.append("")
    
    fig_arwu_rank = go.Figure()
    
    fig_arwu_rank.add_trace(go.Scatter(
        x=arwu_plot["Year"],
        y=arwu_plot[value_col],
        mode="lines+markers+text",
        name=inst_name,
        line=dict(color="#1f77b4", width=3),
        marker=dict(size=12, color="#1f77b4"),
        connectgaps=False,
        hovertemplate="%{text}<extra></extra>",
        text=hover_texts,
        textposition="top center",
        textfont=dict(size=10, color="#1f77b4"),
        customdata=text_labels
    ))
    
    # Add text annotations for data point values
    for i, row in arwu_plot.iterrows():
        if pd.notna(row.get(value_col)):
            fig_arwu_rank.add_annotation(
                x=row["Year"],
                y=row[value_col],
                text=value_format(row[value_col]),
                showarrow=False,
                yshift=15 if not reverse_axis else -15,
                font=dict(size=10, color="#1f77b4")
            )
    
    # Set y-axis range based on view
    if reverse_axis:
        y_range = [y_max, y_min]  # Reversed for ranks
    else:
        y_range = [y_min, y_max]  # Normal for score
    
    fig_arwu_rank.update_layout(
        title=f"ARWU {arwu_rank_view} Evolution",
        xaxis=dict(
            title="Year",
            dtick=1,
            range=[2016.5, 2025.5],
            showgrid=True,
            gridwidth=1,
            gridcolor='lightgray'
        ),
        yaxis=dict(
            title=y_title,
            range=y_range,
            showgrid=True,
            gridwidth=1,
            gridcolor='lightgray',
            zeroline=True,
            zerolinewidth=1,
            zerolinecolor='lightgray'
        ),
        height=600,
        hovermode="closest",
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.12,
            xanchor="center",
            x=0.5,
            font=dict(size=11)
        ),
        margin=dict(b=100),
        plot_bgcolor='white'
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
        
        ---
        
        ⚠️ **Score Recalibration for Pre-2024 Data:**
        
        Before 2024, each indicator had a different **weight** that varied by subject. The raw scores have been 
        recalibrated to weighted scores using the formula:
        
        > **Weighted Score = Raw Score × (Weight / 100)**
        
        For example, if International Collaboration in Chemistry 2023 has a raw score of 80 and a weight of 20, 
        the displayed weighted score is: 80 × 0.20 = **16**
        
        This recalibration ensures comparability with the new 2024+ indicators where weights are already integrated.
        """)
    
    # Check available indicator columns
    all_gras_years = list(range(2021, 2026))
    gras_indicators_data = gras_subject_data.copy()
    
    # Helper function to get weighted old indicator value
    def get_weighted_value(row, indicator_col, weight_col):
        """Apply weight to old indicator scores."""
        if pd.isna(row.get(indicator_col)) or pd.isna(row.get(weight_col)):
            return None
        raw_score = row[indicator_col]
        weight = row[weight_col]
        return raw_score * (weight / 100)
    
    # We'll create 4 charts: HQR/Q1, RI/CNCI, IC, and WCO/TOP/AWARD (+WCF separate)
    
    col_left, col_right = st.columns(2)
    
    # --- Chart 1: HQR / Q1 (continuous) ---
    with col_left:
        st.markdown("**HQR (High Quality Research) / Q1**")
        
        fig_hqr = go.Figure()
        
        # Combine Q1_old (2021-2023, weighted) and HQR_new (2024-2025)
        hqr_values = []
        hqr_labels = []
        for year in all_gras_years:
            year_data = gras_indicators_data[gras_indicators_data["Year"] == year]
            if not year_data.empty:
                row = year_data.iloc[0]
                if year < 2024 and "Q1_old" in row.index and pd.notna(row.get("Q1_old")):
                    val = get_weighted_value(row, "Q1_old", "Q1_weight")
                    hqr_values.append(val)
                    hqr_labels.append(f"{val:.1f}" if val is not None else "")
                elif year >= 2024 and "HQR_new" in row.index and pd.notna(row.get("HQR_new")):
                    val = row["HQR_new"]
                    hqr_values.append(val)
                    hqr_labels.append(f"{val:.1f}" if pd.notna(val) else "")
                else:
                    hqr_values.append(None)
                    hqr_labels.append("")
            else:
                hqr_values.append(None)
                hqr_labels.append("")
        
        fig_hqr.add_trace(go.Scatter(
            x=all_gras_years,
            y=hqr_values,
            mode="lines+markers",
            name="HQR / Q1",
            line=dict(color="#9467bd", width=2),
            marker=dict(size=8),
            connectgaps=False
        ))
        
        # Add data labels
        for i, (year, val, label) in enumerate(zip(all_gras_years, hqr_values, hqr_labels)):
            if val is not None:
                fig_hqr.add_annotation(
                    x=year, y=val, text=label, showarrow=False,
                    yshift=12, font=dict(size=9, color="#9467bd")
                )
        
        fig_hqr.update_layout(
            xaxis=dict(title="Year", dtick=1, showgrid=True, gridcolor='lightgray'),
            yaxis=dict(title="Weighted Score", range=[0, 105], showgrid=True, gridcolor='lightgray'),
            height=300, margin=dict(t=30, b=50), showlegend=False, plot_bgcolor='white'
        )
        st.plotly_chart(fig_hqr, use_container_width=True)
    
    # --- Chart 2: RI / CNCI (continuous) ---
    with col_right:
        st.markdown("**RI (Research Impact) / CNCI**")
        
        fig_ri = go.Figure()
        
        ri_values = []
        ri_labels = []
        for year in all_gras_years:
            year_data = gras_indicators_data[gras_indicators_data["Year"] == year]
            if not year_data.empty:
                row = year_data.iloc[0]
                if year < 2024 and "CNCI_old" in row.index and pd.notna(row.get("CNCI_old")):
                    val = get_weighted_value(row, "CNCI_old", "CNCI_weight")
                    ri_values.append(val)
                    ri_labels.append(f"{val:.1f}" if val is not None else "")
                elif year >= 2024 and "RI_new" in row.index and pd.notna(row.get("RI_new")):
                    val = row["RI_new"]
                    ri_values.append(val)
                    ri_labels.append(f"{val:.1f}" if pd.notna(val) else "")
                else:
                    ri_values.append(None)
                    ri_labels.append("")
            else:
                ri_values.append(None)
                ri_labels.append("")
        
        fig_ri.add_trace(go.Scatter(
            x=all_gras_years,
            y=ri_values,
            mode="lines+markers",
            name="RI / CNCI",
            line=dict(color="#ff7f0e", width=2),
            marker=dict(size=8),
            connectgaps=False
        ))
        
        # Add data labels
        for i, (year, val, label) in enumerate(zip(all_gras_years, ri_values, ri_labels)):
            if val is not None:
                fig_ri.add_annotation(
                    x=year, y=val, text=label, showarrow=False,
                    yshift=12, font=dict(size=9, color="#ff7f0e")
                )
        
        fig_ri.update_layout(
            xaxis=dict(title="Year", dtick=1, showgrid=True, gridcolor='lightgray'),
            yaxis=dict(title="Weighted Score", range=[0, 105], showgrid=True, gridcolor='lightgray'),
            height=300, margin=dict(t=30, b=50), showlegend=False, plot_bgcolor='white'
        )
        st.plotly_chart(fig_ri, use_container_width=True)
    
    col_left2, col_right2 = st.columns(2)
    
    # --- Chart 3: IC (continuous) ---
    with col_left2:
        st.markdown("**IC (International Collaboration)**")
        
        fig_ic = go.Figure()
        
        ic_values = []
        ic_labels = []
        for year in all_gras_years:
            year_data = gras_indicators_data[gras_indicators_data["Year"] == year]
            if not year_data.empty:
                row = year_data.iloc[0]
                if year < 2024 and "IC_old" in row.index and pd.notna(row.get("IC_old")):
                    val = get_weighted_value(row, "IC_old", "IC_weight")
                    ic_values.append(val)
                    ic_labels.append(f"{val:.1f}" if val is not None else "")
                elif year >= 2024 and "IC_new" in row.index and pd.notna(row.get("IC_new")):
                    val = row["IC_new"]
                    ic_values.append(val)
                    ic_labels.append(f"{val:.1f}" if pd.notna(val) else "")
                else:
                    ic_values.append(None)
                    ic_labels.append("")
            else:
                ic_values.append(None)
                ic_labels.append("")
        
        fig_ic.add_trace(go.Scatter(
            x=all_gras_years,
            y=ic_values,
            mode="lines+markers",
            name="IC",
            line=dict(color="#2ca02c", width=2),
            marker=dict(size=8),
            connectgaps=False
        ))
        
        # Add data labels
        for i, (year, val, label) in enumerate(zip(all_gras_years, ic_values, ic_labels)):
            if val is not None:
                fig_ic.add_annotation(
                    x=year, y=val, text=label, showarrow=False,
                    yshift=12, font=dict(size=9, color="#2ca02c")
                )
        
        fig_ic.update_layout(
            xaxis=dict(title="Year", dtick=1, showgrid=True, gridcolor='lightgray'),
            yaxis=dict(title="Weighted Score", range=[0, 105], showgrid=True, gridcolor='lightgray'),
            height=300, margin=dict(t=30, b=50), showlegend=False, plot_bgcolor='white'
        )
        st.plotly_chart(fig_ic, use_container_width=True)
    
    # --- Chart 4: WCF (new, 2024+ only) ---
    with col_right2:
        st.markdown("**WCF (World-Class Faculty)** — *New in 2024*")
        
        fig_wcf = go.Figure()
        
        wcf_values = []
        wcf_labels = []
        for year in all_gras_years:
            year_data = gras_indicators_data[gras_indicators_data["Year"] == year]
            if not year_data.empty and year >= 2024:
                row = year_data.iloc[0]
                if "WCF_new" in row.index and pd.notna(row.get("WCF_new")):
                    val = row["WCF_new"]
                    wcf_values.append(val)
                    wcf_labels.append(f"{val:.1f}" if pd.notna(val) else "")
                else:
                    wcf_values.append(None)
                    wcf_labels.append("")
            else:
                wcf_values.append(None)
                wcf_labels.append("")
        
        fig_wcf.add_trace(go.Scatter(
            x=all_gras_years,
            y=wcf_values,
            mode="lines+markers",
            name="WCF",
            line=dict(color="#e377c2", width=2),
            marker=dict(size=8),
            connectgaps=False
        ))
        
        # Add data labels
        for i, (year, val, label) in enumerate(zip(all_gras_years, wcf_values, wcf_labels)):
            if val is not None:
                fig_wcf.add_annotation(
                    x=year, y=val, text=label, showarrow=False,
                    yshift=12, font=dict(size=9, color="#e377c2")
                )
        
        fig_wcf.update_layout(
            xaxis=dict(title="Year", dtick=1, showgrid=True, gridcolor='lightgray'),
            yaxis=dict(title="Score", range=[0, 105], showgrid=True, gridcolor='lightgray'),
            height=300, margin=dict(t=30, b=50), showlegend=False, plot_bgcolor='white'
        )
        st.plotly_chart(fig_wcf, use_container_width=True)
    
    # --- Chart 5: WCO / TOP / AWARD (full width) ---
    st.markdown("**WCO (World-Class Outputs)** — *Replaces TOP + AWARD*")
    st.caption("TOP and AWARD shown in dotted lines (weighted scores). WCO in solid line.")
    
    fig_wco = go.Figure()
    
    # TOP (dotted, blue, weighted)
    top_values = []
    top_labels = []
    for year in all_gras_years:
        year_data = gras_indicators_data[gras_indicators_data["Year"] == year]
        if not year_data.empty and year < 2024:
            row = year_data.iloc[0]
            if "TOP_old" in row.index and pd.notna(row.get("TOP_old")):
                val = get_weighted_value(row, "TOP_old", "TOP_weight")
                top_values.append(val)
                top_labels.append(f"{val:.1f}" if val is not None else "")
            else:
                top_values.append(None)
                top_labels.append("")
        else:
            top_values.append(None)
            top_labels.append("")
    
    fig_wco.add_trace(go.Scatter(
        x=all_gras_years,
        y=top_values,
        mode="lines+markers",
        name="TOP (pre-2024)",
        line=dict(color="#1f77b4", width=2, dash="dot"),
        marker=dict(size=8),
        connectgaps=False
    ))
    
    # Add data labels for TOP
    for i, (year, val, label) in enumerate(zip(all_gras_years, top_values, top_labels)):
        if val is not None:
            fig_wco.add_annotation(
                x=year, y=val, text=label, showarrow=False,
                yshift=12, font=dict(size=9, color="#1f77b4")
            )
    
    # AWARD (dotted, green, weighted)
    award_values = []
    award_labels = []
    for year in all_gras_years:
        year_data = gras_indicators_data[gras_indicators_data["Year"] == year]
        if not year_data.empty and year < 2024:
            row = year_data.iloc[0]
            if "AWARD_old" in row.index and pd.notna(row.get("AWARD_old")):
                val = get_weighted_value(row, "AWARD_old", "AWARD_weight")
                award_values.append(val)
                award_labels.append(f"{val:.1f}" if val is not None else "")
            else:
                award_values.append(None)
                award_labels.append("")
        else:
            award_values.append(None)
            award_labels.append("")
    
    fig_wco.add_trace(go.Scatter(
        x=all_gras_years,
        y=award_values,
        mode="lines+markers",
        name="AWARD (pre-2024)",
        line=dict(color="#2ca02c", width=2, dash="dot"),
        marker=dict(size=8),
        connectgaps=False
    ))
    
    # Add data labels for AWARD
    for i, (year, val, label) in enumerate(zip(all_gras_years, award_values, award_labels)):
        if val is not None:
            fig_wco.add_annotation(
                x=year, y=val, text=label, showarrow=False,
                yshift=-15, font=dict(size=9, color="#2ca02c")
            )
    
    # WCO (solid, teal/blue-green)
    wco_values = []
    wco_labels = []
    for year in all_gras_years:
        year_data = gras_indicators_data[gras_indicators_data["Year"] == year]
        if not year_data.empty and year >= 2024:
            row = year_data.iloc[0]
            if "WCO_new" in row.index and pd.notna(row.get("WCO_new")):
                val = row["WCO_new"]
                wco_values.append(val)
                wco_labels.append(f"{val:.1f}" if pd.notna(val) else "")
            else:
                wco_values.append(None)
                wco_labels.append("")
        else:
            wco_values.append(None)
            wco_labels.append("")
    
    fig_wco.add_trace(go.Scatter(
        x=all_gras_years,
        y=wco_values,
        mode="lines+markers",
        name="WCO (2024+)",
        line=dict(color="#17becf", width=3),  # Teal/cyan - between blue and green
        marker=dict(size=10),
        connectgaps=False
    ))
    
    # Add data labels for WCO
    for i, (year, val, label) in enumerate(zip(all_gras_years, wco_values, wco_labels)):
        if val is not None:
            fig_wco.add_annotation(
                x=year, y=val, text=label, showarrow=False,
                yshift=15, font=dict(size=9, color="#17becf")
            )
    
    fig_wco.update_layout(
        xaxis=dict(title="Year", dtick=1, showgrid=True, gridcolor='lightgray'),
        yaxis=dict(title="Weighted Score", range=[0, 105], showgrid=True, gridcolor='lightgray'),
        height=350,
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.18,
            xanchor="center",
            x=0.5,
            font=dict(size=11)
        ),
        margin=dict(b=80),
        plot_bgcolor='white'
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
            color = colors[i % len(colors)]
            
            fig_gras_evo.add_trace(go.Scatter(
                x=all_gras_years,
                y=subj_plot["Rank_global"],
                mode="lines+markers",
                name=subject,
                line=dict(color=color, width=2, dash=line_dash),
                marker=dict(size=8),
                connectgaps=False,
                hovertemplate=f"<b>{subject}</b><br>Year: %{{x}}<br>Global Rank: %{{y}}<extra></extra>"
            ))
            
            # Add data labels for each point
            for year in all_gras_years:
                if year in subj_plot.index and pd.notna(subj_plot.loc[year, "Rank_global"]):
                    val = int(subj_plot.loc[year, "Rank_global"])
                    fig_gras_evo.add_annotation(
                        x=year, y=val, text=str(val), showarrow=False,
                        yshift=-12, font=dict(size=8, color=color)
                    )
        
        fig_gras_evo.update_layout(
            title="GRAS Global Rank by Subject",
            xaxis=dict(
                title="Year",
                dtick=1,
                range=[2020.5, 2025.5],
                showgrid=True,
                gridcolor='lightgray'
            ),
            yaxis=dict(
                title="Global Rank",
                autorange="reversed",
                showgrid=True,
                gridcolor='lightgray'
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
            margin=dict(b=120),
            plot_bgcolor='white'
        )
        
        st.plotly_chart(fig_gras_evo, use_container_width=True)
        
        # Download button for subject evolution
        gras_evo_download = gras_evolution[["Year", "Subject", "Field", "Rank_global", "Rank_region", "Score_recomputed"]].copy()
        gras_evo_download.columns = ["Year", "Subject", "Field", "Global Rank", "Regional Rank", "Score"]
        create_download_button(gras_evo_download, f"GRAS_Subject_Evolution_{inst_name}", "dl_gras_evolution")
    else:
        st.info("Select at least one subject to display the evolution chart.")