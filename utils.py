"""
Utility functions for data loading and processing
"""
import pandas as pd
import streamlit as st
from unidecode import unidecode
from pathlib import Path

# Data directory relative to this file
DATA_DIR = Path(__file__).parent / "data"


def norm(s: str) -> str:
    """
    Normalize string for search: lowercase, ascii, no extra spaces.
    Handles NaN values gracefully.
    """
    if pd.isna(s):
        return ""
    return unidecode(str(s)).lower().strip()


@st.cache_data
def load_arwu() -> pd.DataFrame:
    """
    Load ARWU data from parquet.
    Adds a normalized search key column.
    """
    df = pd.read_parquet(DATA_DIR / "arwu_2017_2025.parquet")
    df["__searchkey"] = df["Institution"].apply(norm)
    return df


@st.cache_data
def load_gras() -> pd.DataFrame:
    """
    Load GRAS data from parquet.
    Adds a normalized search key column.
    """
    df = pd.read_parquet(DATA_DIR / "gras_2021_2025.parquet")
    df["__searchkey"] = df["Institution"].apply(norm)
    return df


@st.cache_data
def get_institution_list() -> pd.DataFrame:
    """
    Get unique institutions from both datasets with country info.
    Combines ARWU and GRAS institutions, removes duplicates,
    and adds normalized search key.
    
    Returns:
        DataFrame with columns: Institution, Country/Region, __searchkey
    """
    arwu = load_arwu()[["Institution", "Country/Region"]].drop_duplicates()
    gras = load_gras()[["Institution", "Country/Region"]].drop_duplicates()
    
    # Combine and deduplicate
    combined = pd.concat([arwu, gras]).drop_duplicates(subset=["Institution"])
    combined["__searchkey"] = combined["Institution"].apply(norm)
    combined = combined.sort_values("Institution").reset_index(drop=True)
    
    return combined


@st.cache_data
def get_country_list() -> list:
    """
    Get unique countries from both datasets.
    
    Returns:
        Sorted list of country names
    """
    arwu = load_arwu()["Country/Region"].unique().tolist()
    gras = load_gras()["Country/Region"].unique().tolist()
    
    countries = sorted(set(arwu + gras))
    return countries


def search_institutions(df: pd.DataFrame, query: str, max_results: int = 200) -> pd.DataFrame:
    """
    Search institutions by normalized query.
    Prioritizes matches that start with the query, then contains.
    
    Args:
        df: DataFrame with Institution and __searchkey columns
        query: Search string
        max_results: Maximum number of results to return
        
    Returns:
        DataFrame of matching institutions, sorted alphabetically
    """
    if not query:
        return df.head(0)
    
    nq = norm(query)
    
    # Prioritize starts-with matches
    m_starts = df[df["__searchkey"].str.startswith(nq)].copy()
    m_starts["_match_priority"] = 0
    
    # Then contains matches
    m_contains = df[df["__searchkey"].str.contains(nq, regex=False)].copy()
    m_contains["_match_priority"] = 1
    
    # Combine, deduplicate, sort by priority then name
    results = pd.concat([m_starts, m_contains]).drop_duplicates(subset=["Institution"])
    results = results.sort_values(["_match_priority", "Institution"]).head(max_results)
    results = results.drop(columns=["_match_priority"])
    
    return results


def label_institution(row) -> str:
    """
    Create display label for institution with country.
    
    Args:
        row: DataFrame row or Series with Institution and Country/Region
        
    Returns:
        Formatted string like "Harvard University (United States)"
    """
    name = row["Institution"]
    country = str(row.get("Country/Region", "")).strip()
    
    if country:
        return f"{name} ({country})"
    return name


def get_arwu_years() -> list:
    """Get list of available ARWU years."""
    return sorted(load_arwu()["Year"].unique().tolist())


def get_gras_years() -> list:
    """Get list of available GRAS years."""
    return sorted(load_gras()["Year"].unique().tolist())


def get_gras_fields() -> list:
    """Get list of available GRAS fields."""
    return sorted(load_gras()["Field"].unique().tolist())


def get_gras_subjects(field: str = None) -> list:
    """
    Get list of available GRAS subjects.
    
    Args:
        field: Optional field to filter subjects
        
    Returns:
        Sorted list of subject names
    """
    gras = load_gras()
    if field:
        gras = gras[gras["Field"] == field]
    return sorted(gras["Subject"].unique().tolist())