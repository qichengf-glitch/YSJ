"""Data-quality summary for the VIX history."""

def summarize_quality(df):
    """df: history DataFrame with columns n_instruments, dq_flags.
    Returns a small dict summary."""
    return {
        "n_days": int(len(df)),
        "days_with_flags": int((df["dq_flags"] > 0).sum()) if "dq_flags" in df else 0,
        "mean_instruments": float(df["n_instruments"].mean()) if "n_instruments" in df else None,
        "min_instruments": int(df["n_instruments"].min()) if "n_instruments" in df else None,
    }
