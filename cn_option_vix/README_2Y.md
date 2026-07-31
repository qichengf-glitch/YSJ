# Two-year 30-minute VIX history patch

This patch leaves all VIX mathematics and aggregation functions unchanged.
It adds:

1. Persistent contract metadata caching, so the same `rq.instruments` objects are not downloaded every day.
2. Date-correct daily strike pulls only for ETF options; CFFEX index-option strikes use immutable instrument metadata.
3. A streaming, resumable two-year builder with atomic daily checkpoints.
4. A real quota preflight: the first 10 newly downloaded days are retained, traffic is measured, and the full run continues only if the projected usage fits with a 64 MiB reserve and a 1.15x safety factor.
5. Slide-ready 16:9 PNG and SVG charts.

## Install

From `/Users/wonderfulren/Desktop/coding/quant`:

```bash
cp -a cn_option_vix cn_option_vix.backup.$(date +%Y%m%d_%H%M%S)
unzip -o ~/Downloads/cn_option_vix_2y_patch.zip
```

## Run full range and plot

```bash
cd /Users/wonderfulren/Desktop/coding/quant
conda activate rqvix
export RQDATA_URI='tcp://...'

bash cn_option_vix/scripts/run_2y_and_plot.sh \
  2024-07-13 2026-07-13 vix_30m_2y
```

The builder checkpoints after every completed date. `Ctrl-C`, API errors, or a quota stop are safe; run the same command again to resume.

## Outputs

```text
cn_option_vix/outputs/vix_30m_2y.csv
cn_option_vix/outputs/vix_30m_2y.parquet
cn_option_vix/outputs/vix_30m_2y_audit.csv
cn_option_vix/outputs/vix_30m_2y_summary.json
cn_option_vix/outputs/roadshow_2y/roadshow_vix_overall_2y.png
cn_option_vix/outputs/roadshow_2y/roadshow_vix_overall_2y.svg
cn_option_vix/outputs/roadshow_2y/roadshow_vix_segments_2y.png
cn_option_vix/outputs/roadshow_2y/roadshow_vix_segments_2y.svg
```

Use the SVG in PowerPoint when possible; it remains sharp at any size. The 320-dpi PNG is provided as a compatibility fallback.
