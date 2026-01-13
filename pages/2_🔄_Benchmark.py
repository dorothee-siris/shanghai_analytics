"""
Benchmark View - Compare institutions across rankings
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys
from pathlib import Path
from datetime import datetime
from io import BytesIO

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils import load_arwu, load_gras, get_institution_list, search_institutions, label_institution

st.set_page_config(page_title="Benchmark", page_icon="🔄", layout="wide")
st.title("🔄 Benchmark")

# ============================================================================
# CONSTANTS
# ============================================================================
EUROPEAN_COUNTRIES = [
    "Netherlands", "Germany", "United Kingdom", "Italy", "Sweden", "France",
    "Denmark", "Spain", "Norway", "Portugal", "Belgium", "Finland", "Greece",
    "Ireland", "Austria", "Poland", "Czech Republic", "Slovenia", "Croatia",
    "Luxembourg", "Iceland", "Cyprus", "Romania", "Serbia", "Hungary", "Estonia",
    "Slovakia", "Lithuania", "Malta", "Bulgaria", "Georgia", "Belarus", "Latvia",
    "Liechtenstein", "Switzerland"
]

# Color scheme
COLOR_SELECTED = "#e74c3c"  # Red - selected institution
COLOR_SAME_COUNTRY = "#f1948a"  # Light red/salmon - same country
COLOR_EUROPE = "#27ae60"  # Green - Europe (not same country)
COLOR_OUTSIDE = "#3498db"  # Blue - outside Europe

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


def get_institution_color(inst_country: str, selected_country: str) -> str:
    """Determine color based on geographic relationship."""
    if inst_country == selected_country:
        return COLOR_SAME_COUNTRY
    elif inst_country in EUROPEAN_COUNTRIES:
        return COLOR_EUROPE
    else:
        return COLOR_OUTSIDE


def get_region_label(inst_country: str, selected_country: str) -> str:
    """Get region label for an institution."""
    if inst_country == selected_country:
        return "Same Country"
    elif inst_country in EUROPEAN_COUNTRIES:
        return "Europe"
    else:
        return "Other"


def get_context_institutions(df, inst_name, country, year, rank_col, top_n=2, above_n=2, below_n=2):
    """Get top N + institutions ranked above/below selected institution."""
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
        return list(set(top_institutions + [inst_name]))
    
    inst_idx = inst_idx[0]
    
    # Get institutions above and below
    above_institutions = []
    below_institutions = []
    
    for i in range(1, above_n + 1):
        if inst_idx - i >= 0:
            above_inst = country_data.iloc[inst_idx - i]["Institution"]
            if above_inst not in top_institutions and above_inst != inst_name:
                above_institutions.append(above_inst)
    
    for i in range(1, below_n + 1):
        if inst_idx + i < len(country_data):
            below_inst = country_data.iloc[inst_idx + i]["Institution"]
            if below_inst not in top_institutions and below_inst != inst_name:
                below_institutions.append(below_inst)
    
    # Combine without duplicates
    result = []
    for inst in top_institutions + above_institutions + [inst_name] + below_institutions:
        if inst not in result:
            result.append(inst)
    
    return result


def get_weighted_value(row, indicator_col, weight_col):
    """Apply weight to old GRAS indicator scores."""
    if pd.isna(row.get(indicator_col)) or pd.isna(row.get(weight_col)):
        return None
    return row[indicator_col] * (row[weight_col] / 100)


# ============================================================================
# LOAD DATA
# ============================================================================
arwu_df = load_arwu()
gras_df = load_gras()
institutions_df = get_institution_list()

# ============================================================================
# SECTION 1: INSTITUTION SELECTION
# ============================================================================
st.markdown("### Find your institution")
q = st.text_input(
    "Search by name",
    placeholder="e.g., Harvard, Sorbonne, ETH Zurich, Peking University...",
    key="main_search"
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
    st.info("👆 Search and select an institution to start benchmarking.")
    st.stop()

# Get institution details
inst_name = chosen["Institution"]
inst_country = chosen["Country/Region"]
inst_id = chosen.get("Institution_ID", None)

# Fetch ID from data if needed
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
st.subheader(f"{inst_name}")
st.caption(f"📍 {inst_country} | 🆔 {inst_id_display}")

# ============================================================================
# SECTION 2: RANKING SELECTION
# ============================================================================
st.markdown("### Select Ranking")

col_ranking, col_subject = st.columns([1, 2])

with col_ranking:
    ranking_type = st.radio(
        "Ranking type",
        options=["ARWU", "GRAS"],
        horizontal=True,
        key="ranking_type"
    )

# Get institution's data
if "Institution_ID" in arwu_df.columns and pd.notna(inst_id):
    arwu_inst = arwu_df[arwu_df["Institution_ID"] == inst_id]
    gras_inst = gras_df[gras_df["Institution_ID"] == inst_id]
else:
    arwu_inst = arwu_df[arwu_df["Institution"] == inst_name]
    gras_inst = gras_df[gras_df["Institution"] == inst_name]

selected_subject = None

with col_subject:
    if ranking_type == "GRAS":
        available_subjects = sorted(gras_inst["Subject"].unique().tolist())
        if not available_subjects:
            st.warning(f"{inst_name} is not ranked in any GRAS subject.")
            st.stop()
        selected_subject = st.selectbox(
            "Select subject",
            options=available_subjects,
            key="subject_select"
        )
    else:
        if arwu_inst.empty:
            st.warning(f"{inst_name} is not ranked in ARWU.")
            st.stop()
        st.caption("Overall ARWU ranking selected")

# ============================================================================
# SECTION 3: BENCHMARK MODE
# ============================================================================
st.markdown("---")
st.markdown("### Benchmark Mode")

benchmark_mode = st.radio(
    "Select mode",
    options=["Any Institution", "Country Level"],
    horizontal=True,
    key="benchmark_mode"
)

# Initialize session state for benchmark institutions
if "benchmark_institutions" not in st.session_state:
    st.session_state.benchmark_institutions = []

# Clear benchmark institutions if mode changes
if "prev_benchmark_mode" not in st.session_state:
    st.session_state.prev_benchmark_mode = benchmark_mode
elif st.session_state.prev_benchmark_mode != benchmark_mode:
    st.session_state.benchmark_institutions = []
    st.session_state.prev_benchmark_mode = benchmark_mode

# ============================================================================
# SECTION 4: ADD INSTITUTIONS (depends on mode)
# ============================================================================
st.markdown("---")
st.markdown("### Add Institutions to Compare")

if benchmark_mode == "Country Level":
    # Country level options
    col_filter, col_search = st.columns([1, 2])
    
    with col_filter:
        num_institutions = st.slider(
            "Number of context institutions",
            min_value=2,
            max_value=10,
            value=6,
            help="Top N from country + N above/below selected institution"
        )
    
    # Auto-select context institutions
    if ranking_type == "ARWU":
        context_insts = get_context_institutions(
            arwu_df, inst_name, inst_country, 2025, "Region_Rank_recomputed",
            top_n=num_institutions//3, above_n=num_institutions//3, below_n=num_institutions//3
        )
    else:
        gras_subject_df = gras_df[gras_df["Subject"] == selected_subject]
        context_insts = get_context_institutions(
            gras_subject_df, inst_name, inst_country, 2025, "Rank_region",
            top_n=num_institutions//3, above_n=num_institutions//3, below_n=num_institutions//3
        )
    
    # Remove selected institution from context (will be added separately)
    context_insts = [i for i in context_insts if i != inst_name]
    
    with col_search:
        st.caption(f"Add more institutions from {inst_country}")
        q_add = st.text_input(
            "Search to add",
            placeholder=f"Search institutions in {inst_country}...",
            key="add_search_country"
        )
        
        if q_add:
            # Filter to same country
            country_institutions = institutions_df[institutions_df["Country/Region"] == inst_country]
            results_add = search_institutions(country_institutions, q_add)
            already_selected = [inst_name] + context_insts + st.session_state.benchmark_institutions
            results_add = results_add[~results_add["Institution"].isin(already_selected)]
            
            if len(results_add) > 0:
                for _, row in results_add.head(5).iterrows():
                    if st.button(f"➕ {row['Institution']}", key=f"add_{row['Institution']}"):
                        st.session_state.benchmark_institutions.append(row["Institution"])
                        st.rerun()
    
    # Combine context + manually added
    comparison_institutions = context_insts + st.session_state.benchmark_institutions

else:  # Any Institution mode
    st.caption("Search and add any institution globally")
    q_add = st.text_input(
        "Search to add",
        placeholder="Search any institution...",
        key="add_search_global"
    )
    
    if q_add:
        results_add = search_institutions(institutions_df, q_add)
        already_selected = [inst_name] + st.session_state.benchmark_institutions
        results_add = results_add[~results_add["Institution"].isin(already_selected)]
        
        if len(results_add) > 0:
            for _, row in results_add.head(5).iterrows():
                inst_label = f"{row['Institution']} ({row['Country/Region']})"
                if st.button(f"➕ {inst_label}", key=f"add_{row['Institution']}"):
                    st.session_state.benchmark_institutions.append(row["Institution"])
                    st.rerun()
    
    comparison_institutions = st.session_state.benchmark_institutions

# Display selected institutions as tags
if comparison_institutions or st.session_state.benchmark_institutions:
    st.markdown("**Selected for comparison:**")
    
    all_comparison = list(set(comparison_institutions + st.session_state.benchmark_institutions))
    
    # Create tag display
    cols = st.columns(min(len(all_comparison) + 1, 5))
    
    # Selected institution (not removable)
    with cols[0]:
        st.markdown(f"🔴 **{inst_name[:20]}...**" if len(inst_name) > 20 else f"🔴 **{inst_name}**")
    
    # Other institutions (removable if manually added)
    col_idx = 1
    for inst in all_comparison:
        if inst == inst_name:
            continue
        with cols[col_idx % len(cols)]:
            # Get color indicator
            inst_data = institutions_df[institutions_df["Institution"] == inst]
            if not inst_data.empty:
                inst_ctry = inst_data.iloc[0]["Country/Region"]
                if inst_ctry == inst_country:
                    emoji = "🟠"  # Same country
                elif inst_ctry in EUROPEAN_COUNTRIES:
                    emoji = "🟢"  # Europe
                else:
                    emoji = "🔵"  # Outside
            else:
                emoji = "⚪"
            
            # Only show remove button for manually added
            if inst in st.session_state.benchmark_institutions:
                if st.button(f"❌ {emoji} {inst[:15]}...", key=f"rm_{inst}"):
                    st.session_state.benchmark_institutions.remove(inst)
                    st.rerun()
            else:
                st.markdown(f"{emoji} {inst[:20]}..." if len(inst) > 20 else f"{emoji} {inst}")
        col_idx += 1
    
    # Color legend
    st.caption("🔴 Selected | 🟠 Same country | 🟢 Europe | 🔵 Other")

# Final list of institutions to compare
all_institutions = [inst_name] + list(set(comparison_institutions + st.session_state.benchmark_institutions))
all_institutions = list(dict.fromkeys(all_institutions))  # Remove duplicates, keep order

if len(all_institutions) < 2:
    st.info("👆 Add at least one institution to compare.")
    st.stop()

# ============================================================================
# SECTION 5: VIEW TOGGLE
# ============================================================================
st.markdown("---")
st.markdown("### View Options")

view_type = st.radio(
    "Select view",
    options=["Global Rank", "Regional Rank", "Score"],
    horizontal=True,
    key="view_type"
)

# ============================================================================
# SECTION 6: PREPARE DATA FOR CHARTS
# ============================================================================
# Determine columns and year range based on ranking type
if ranking_type == "ARWU":
    if view_type == "Global Rank":
        value_col = "Rank_recomputed"
        y_title = "World Rank"
        reverse_y = True
    elif view_type == "Regional Rank":
        value_col = "Region_Rank_recomputed"
        y_title = "Regional Rank"
        reverse_y = True
    else:
        value_col = "Score_normalized"
        y_title = "Score"
        reverse_y = False
    
    years_range = list(range(2017, 2026))
    base_df = arwu_df
else:  # GRAS
    if view_type == "Global Rank":
        value_col = "Rank_global"
        y_title = "Global Rank"
        reverse_y = True
    elif view_type == "Regional Rank":
        value_col = "Rank_region"
        y_title = "Regional Rank"
        reverse_y = True
    else:
        value_col = "Score_recomputed"
        y_title = "Score"
        reverse_y = False
    
    years_range = list(range(2021, 2026))
    base_df = gras_df[gras_df["Subject"] == selected_subject]

# Build institution colors and data
inst_colors = {}
inst_countries = {}

for inst in all_institutions:
    inst_data = institutions_df[institutions_df["Institution"] == inst]
    if not inst_data.empty:
        ctry = inst_data.iloc[0]["Country/Region"]
    else:
        ctry = "Unknown"
    inst_countries[inst] = ctry
    
    if inst == inst_name:
        inst_colors[inst] = COLOR_SELECTED
    else:
        inst_colors[inst] = get_institution_color(ctry, inst_country)

# ============================================================================
# SECTION 7: MAIN EVOLUTION CHART
# ============================================================================
st.markdown("---")
st.markdown("## Rank/Score Evolution")

fig_main = go.Figure()

for inst in all_institutions:
    if "Institution_ID" in base_df.columns:
        inst_match = institutions_df[institutions_df["Institution"] == inst]
        if not inst_match.empty and pd.notna(inst_match.iloc[0].get("Institution_ID")):
            inst_data = base_df[base_df["Institution_ID"] == inst_match.iloc[0]["Institution_ID"]]
        else:
            inst_data = base_df[base_df["Institution"] == inst]
    else:
        inst_data = base_df[base_df["Institution"] == inst]
    
    inst_plot = inst_data.set_index("Year").reindex(years_range)
    
    # Line width: thicker for selected
    line_width = 3 if inst == inst_name else 2
    
    fig_main.add_trace(go.Scatter(
        x=years_range,
        y=inst_plot[value_col],
        mode="lines+markers",
        name=f"{inst} ({inst_countries.get(inst, '')})",
        line=dict(color=inst_colors[inst], width=line_width),
        marker=dict(size=8 if inst == inst_name else 6),
        connectgaps=False
    ))

fig_main.update_layout(
    xaxis=dict(
        title="Year",
        dtick=1,
        showgrid=True,
        gridcolor='lightgray'
    ),
    yaxis=dict(
        title=y_title,
        autorange="reversed" if reverse_y else None,
        showgrid=True,
        gridcolor='lightgray'
    ),
    height=500,
    hovermode="x unified",
    legend=dict(
        orientation="h",
        yanchor="top",
        y=-0.15,
        xanchor="center",
        x=0.5,
        font=dict(size=10)
    ),
    margin=dict(b=120),
    plot_bgcolor='white'
)

st.plotly_chart(fig_main, use_container_width=True)

# Download data for main chart
main_download_data = []
for inst in all_institutions:
    if "Institution_ID" in base_df.columns:
        inst_match = institutions_df[institutions_df["Institution"] == inst]
        if not inst_match.empty and pd.notna(inst_match.iloc[0].get("Institution_ID")):
            inst_data = base_df[base_df["Institution_ID"] == inst_match.iloc[0]["Institution_ID"]]
        else:
            inst_data = base_df[base_df["Institution"] == inst]
    else:
        inst_data = base_df[base_df["Institution"] == inst]
    
    for _, row in inst_data.iterrows():
        main_download_data.append({
            "Institution": inst,
            "Country": inst_countries.get(inst, ""),
            "Year": row["Year"],
            "Value": row.get(value_col)
        })

main_download_df = pd.DataFrame(main_download_data)
ranking_label = "ARWU" if ranking_type == "ARWU" else selected_subject
create_download_button(main_download_df, f"Benchmark_{ranking_label}_Evolution", "dl_main_evolution")

# ============================================================================
# SECTION 8: RADAR CHART (2025 SNAPSHOT)
# ============================================================================
st.markdown("---")
st.markdown("## Indicators Snapshot (2025)")

if ranking_type == "ARWU":
    radar_indicators = ["Alumni", "Award", "HiCi", "N&S", "PUB", "PCP"]
    
    fig_radar = go.Figure()
    
    for inst in all_institutions:
        inst_data = arwu_df[(arwu_df["Institution"] == inst) & (arwu_df["Year"] == 2025)]
        
        if not inst_data.empty:
            row = inst_data.iloc[0]
            values = [row.get(ind, 0) or 0 for ind in radar_indicators]
            values.append(values[0])  # Close the radar
            
            fig_radar.add_trace(go.Scatterpolar(
                r=values,
                theta=radar_indicators + [radar_indicators[0]],
                fill='toself',
                name=inst,
                line=dict(color=inst_colors[inst], width=2 if inst != inst_name else 3),
                opacity=0.7 if inst == inst_name else 0.4
            ))
    
    fig_radar.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100])
        ),
        height=500,
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.1,
            xanchor="center",
            x=0.5,
            font=dict(size=10)
        ),
        margin=dict(b=100)
    )
    
    st.plotly_chart(fig_radar, use_container_width=True)

else:  # GRAS
    radar_indicators = ["WCF", "WCO", "HQR", "RI", "IC"]
    indicator_cols = ["WCF_new", "WCO_new", "HQR_new", "RI_new", "IC_new"]
    
    fig_radar = go.Figure()
    
    gras_2025 = gras_df[(gras_df["Subject"] == selected_subject) & (gras_df["Year"] == 2025)]
    
    for inst in all_institutions:
        inst_data = gras_2025[gras_2025["Institution"] == inst]
        
        if not inst_data.empty:
            row = inst_data.iloc[0]
            values = [row.get(col, 0) or 0 for col in indicator_cols]
            values.append(values[0])  # Close the radar
            
            fig_radar.add_trace(go.Scatterpolar(
                r=values,
                theta=radar_indicators + [radar_indicators[0]],
                fill='toself',
                name=inst,
                line=dict(color=inst_colors[inst], width=2 if inst != inst_name else 3),
                opacity=0.7 if inst == inst_name else 0.4
            ))
    
    fig_radar.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100])
        ),
        height=500,
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.1,
            xanchor="center",
            x=0.5,
            font=dict(size=10)
        ),
        margin=dict(b=100)
    )
    
    st.plotly_chart(fig_radar, use_container_width=True)

# ============================================================================
# SECTION 9: INDICATORS EVOLUTION CHARTS
# ============================================================================
st.markdown("---")
st.markdown("## Indicators Evolution")

if ranking_type == "ARWU":
    # ARWU: 6 indicators in 2x3 grid
    indicators = ["Alumni", "Award", "HiCi", "N&S", "PUB", "PCP"]
    
    col1, col2 = st.columns(2)
    
    for i, indicator in enumerate(indicators):
        with col1 if i % 2 == 0 else col2:
            st.markdown(f"**{indicator}**")
            
            fig_ind = go.Figure()
            
            for inst in all_institutions:
                inst_data = arwu_df[arwu_df["Institution"] == inst].set_index("Year").reindex(years_range)
                
                fig_ind.add_trace(go.Scatter(
                    x=years_range,
                    y=inst_data[indicator],
                    mode="lines+markers",
                    name=inst,
                    line=dict(color=inst_colors[inst], width=2 if inst != inst_name else 3),
                    marker=dict(size=6),
                    connectgaps=False
                ))
            
            fig_ind.update_layout(
                xaxis=dict(title="Year", dtick=1, showgrid=True, gridcolor='lightgray'),
                yaxis=dict(title="Score", range=[0, 105], showgrid=True, gridcolor='lightgray'),
                height=300,
                hovermode="x unified",
                showlegend=False,
                margin=dict(t=30, b=50),
                plot_bgcolor='white'
            )
            
            st.plotly_chart(fig_ind, use_container_width=True)

else:  # GRAS
    # GRAS: 5 indicator charts with methodology transition
    gras_years = list(range(2021, 2026))
    
    col1, col2 = st.columns(2)
    
    # Chart 1: HQR / Q1
    with col1:
        st.markdown("**HQR (High Quality Research) / Q1**")
        fig_hqr = go.Figure()
        
        for inst in all_institutions:
            gras_inst_data = gras_df[(gras_df["Subject"] == selected_subject) & (gras_df["Institution"] == inst)]
            
            hqr_values = []
            for year in gras_years:
                year_data = gras_inst_data[gras_inst_data["Year"] == year]
                if not year_data.empty:
                    row = year_data.iloc[0]
                    if year < 2024 and pd.notna(row.get("Q1_old")):
                        val = get_weighted_value(row, "Q1_old", "Q1_weight")
                        hqr_values.append(val)
                    elif year >= 2024 and pd.notna(row.get("HQR_new")):
                        hqr_values.append(row["HQR_new"])
                    else:
                        hqr_values.append(None)
                else:
                    hqr_values.append(None)
            
            fig_hqr.add_trace(go.Scatter(
                x=gras_years, y=hqr_values, mode="lines+markers", name=inst,
                line=dict(color=inst_colors[inst], width=2 if inst != inst_name else 3),
                marker=dict(size=6), connectgaps=False
            ))
        
        fig_hqr.update_layout(
            xaxis=dict(title="Year", dtick=1, showgrid=True, gridcolor='lightgray'),
            yaxis=dict(title="Weighted Score", range=[0, 105], showgrid=True, gridcolor='lightgray'),
            height=300, hovermode="x unified", showlegend=False,
            margin=dict(t=30, b=50), plot_bgcolor='white'
        )
        st.plotly_chart(fig_hqr, use_container_width=True)
    
    # Chart 2: RI / CNCI
    with col2:
        st.markdown("**RI (Research Impact) / CNCI**")
        fig_ri = go.Figure()
        
        for inst in all_institutions:
            gras_inst_data = gras_df[(gras_df["Subject"] == selected_subject) & (gras_df["Institution"] == inst)]
            
            ri_values = []
            for year in gras_years:
                year_data = gras_inst_data[gras_inst_data["Year"] == year]
                if not year_data.empty:
                    row = year_data.iloc[0]
                    if year < 2024 and pd.notna(row.get("CNCI_old")):
                        val = get_weighted_value(row, "CNCI_old", "CNCI_weight")
                        ri_values.append(val)
                    elif year >= 2024 and pd.notna(row.get("RI_new")):
                        ri_values.append(row["RI_new"])
                    else:
                        ri_values.append(None)
                else:
                    ri_values.append(None)
            
            fig_ri.add_trace(go.Scatter(
                x=gras_years, y=ri_values, mode="lines+markers", name=inst,
                line=dict(color=inst_colors[inst], width=2 if inst != inst_name else 3),
                marker=dict(size=6), connectgaps=False
            ))
        
        fig_ri.update_layout(
            xaxis=dict(title="Year", dtick=1, showgrid=True, gridcolor='lightgray'),
            yaxis=dict(title="Weighted Score", range=[0, 105], showgrid=True, gridcolor='lightgray'),
            height=300, hovermode="x unified", showlegend=False,
            margin=dict(t=30, b=50), plot_bgcolor='white'
        )
        st.plotly_chart(fig_ri, use_container_width=True)
    
    # Chart 3: IC
    with col1:
        st.markdown("**IC (International Collaboration)**")
        fig_ic = go.Figure()
        
        for inst in all_institutions:
            gras_inst_data = gras_df[(gras_df["Subject"] == selected_subject) & (gras_df["Institution"] == inst)]
            
            ic_values = []
            for year in gras_years:
                year_data = gras_inst_data[gras_inst_data["Year"] == year]
                if not year_data.empty:
                    row = year_data.iloc[0]
                    if year < 2024 and pd.notna(row.get("IC_old")):
                        val = get_weighted_value(row, "IC_old", "IC_weight")
                        ic_values.append(val)
                    elif year >= 2024 and pd.notna(row.get("IC_new")):
                        ic_values.append(row["IC_new"])
                    else:
                        ic_values.append(None)
                else:
                    ic_values.append(None)
            
            fig_ic.add_trace(go.Scatter(
                x=gras_years, y=ic_values, mode="lines+markers", name=inst,
                line=dict(color=inst_colors[inst], width=2 if inst != inst_name else 3),
                marker=dict(size=6), connectgaps=False
            ))
        
        fig_ic.update_layout(
            xaxis=dict(title="Year", dtick=1, showgrid=True, gridcolor='lightgray'),
            yaxis=dict(title="Weighted Score", range=[0, 105], showgrid=True, gridcolor='lightgray'),
            height=300, hovermode="x unified", showlegend=False,
            margin=dict(t=30, b=50), plot_bgcolor='white'
        )
        st.plotly_chart(fig_ic, use_container_width=True)
    
    # Chart 4: WCF
    with col2:
        st.markdown("**WCF (World-Class Faculty)** — *New in 2024*")
        fig_wcf = go.Figure()
        
        for inst in all_institutions:
            gras_inst_data = gras_df[(gras_df["Subject"] == selected_subject) & (gras_df["Institution"] == inst)]
            
            wcf_values = []
            for year in gras_years:
                year_data = gras_inst_data[gras_inst_data["Year"] == year]
                if not year_data.empty and year >= 2024:
                    row = year_data.iloc[0]
                    wcf_values.append(row.get("WCF_new"))
                else:
                    wcf_values.append(None)
            
            fig_wcf.add_trace(go.Scatter(
                x=gras_years, y=wcf_values, mode="lines+markers", name=inst,
                line=dict(color=inst_colors[inst], width=2 if inst != inst_name else 3),
                marker=dict(size=6), connectgaps=False
            ))
        
        fig_wcf.update_layout(
            xaxis=dict(title="Year", dtick=1, showgrid=True, gridcolor='lightgray'),
            yaxis=dict(title="Score", range=[0, 105], showgrid=True, gridcolor='lightgray'),
            height=300, hovermode="x unified", showlegend=False,
            margin=dict(t=30, b=50), plot_bgcolor='white'
        )
        st.plotly_chart(fig_wcf, use_container_width=True)
    
    # Chart 5: WCO / TOP / AWARD (full width)
    st.markdown("**WCO (World-Class Outputs)** — *Replaces TOP + AWARD*")
    st.caption("Dotted lines: TOP/AWARD (pre-2024, weighted). Solid lines: WCO (2024+).")
    
    fig_wco = go.Figure()
    
    for inst in all_institutions:
        gras_inst_data = gras_df[(gras_df["Subject"] == selected_subject) & (gras_df["Institution"] == inst)]
        
        # TOP (dotted, pre-2024)
        top_values = []
        for year in gras_years:
            year_data = gras_inst_data[gras_inst_data["Year"] == year]
            if not year_data.empty and year < 2024:
                row = year_data.iloc[0]
                if pd.notna(row.get("TOP_old")):
                    top_values.append(get_weighted_value(row, "TOP_old", "TOP_weight"))
                else:
                    top_values.append(None)
            else:
                top_values.append(None)
        
        fig_wco.add_trace(go.Scatter(
            x=gras_years, y=top_values, mode="lines+markers",
            name=f"{inst} (TOP)" if inst == inst_name else None,
            line=dict(color=inst_colors[inst], width=1, dash="dot"),
            marker=dict(size=4), connectgaps=False, showlegend=(inst == inst_name),
            legendgroup=inst
        ))
        
        # AWARD (dotted, pre-2024)
        award_values = []
        for year in gras_years:
            year_data = gras_inst_data[gras_inst_data["Year"] == year]
            if not year_data.empty and year < 2024:
                row = year_data.iloc[0]
                if pd.notna(row.get("AWARD_old")):
                    award_values.append(get_weighted_value(row, "AWARD_old", "AWARD_weight"))
                else:
                    award_values.append(None)
            else:
                award_values.append(None)
        
        fig_wco.add_trace(go.Scatter(
            x=gras_years, y=award_values, mode="lines+markers",
            name=f"{inst} (AWARD)" if inst == inst_name else None,
            line=dict(color=inst_colors[inst], width=1, dash="dash"),
            marker=dict(size=4), connectgaps=False, showlegend=(inst == inst_name),
            legendgroup=inst
        ))
        
        # WCO (solid, 2024+)
        wco_values = []
        for year in gras_years:
            year_data = gras_inst_data[gras_inst_data["Year"] == year]
            if not year_data.empty and year >= 2024:
                row = year_data.iloc[0]
                wco_values.append(row.get("WCO_new"))
            else:
                wco_values.append(None)
        
        fig_wco.add_trace(go.Scatter(
            x=gras_years, y=wco_values, mode="lines+markers",
            name=f"{inst} (WCO)",
            line=dict(color=inst_colors[inst], width=2 if inst != inst_name else 3),
            marker=dict(size=6), connectgaps=False,
            legendgroup=inst
        ))
    
    fig_wco.update_layout(
        xaxis=dict(title="Year", dtick=1, showgrid=True, gridcolor='lightgray'),
        yaxis=dict(title="Weighted Score", range=[0, 105], showgrid=True, gridcolor='lightgray'),
        height=400, hovermode="x unified",
        legend=dict(
            orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5, font=dict(size=9)
        ),
        margin=dict(b=100), plot_bgcolor='white'
    )
    st.plotly_chart(fig_wco, use_container_width=True)

# ============================================================================
# SECTION 10: DATA TABLE
# ============================================================================
st.markdown("---")
st.markdown("## Comparison Data Table")

table_data = []
for inst in all_institutions:
    if ranking_type == "ARWU":
        inst_data = arwu_df[arwu_df["Institution"] == inst]
    else:
        inst_data = gras_df[(gras_df["Subject"] == selected_subject) & (gras_df["Institution"] == inst)]
    
    row_data = {
        "Institution": inst,
        "Country": inst_countries.get(inst, ""),
        "Region": get_region_label(inst_countries.get(inst, ""), inst_country)
    }
    
    for year in years_range:
        year_data = inst_data[inst_data["Year"] == year]
        if not year_data.empty:
            row_data[str(year)] = year_data.iloc[0].get(value_col)
        else:
            row_data[str(year)] = None
    
    table_data.append(row_data)

table_df = pd.DataFrame(table_data)

# Highlight selected institution
def highlight_selected(row):
    if row["Institution"] == inst_name:
        return ['background-color: #fadbd8'] * len(row)
    return [''] * len(row)

styled_table = table_df.style.apply(highlight_selected, axis=1)
st.dataframe(styled_table, use_container_width=True, hide_index=True)

create_download_button(table_df, f"Benchmark_{ranking_label}_Data", "dl_comparison_table")

# Clear all button
st.markdown("---")
if st.button("🗑️ Clear all added institutions"):
    st.session_state.benchmark_institutions = []
    st.rerun()