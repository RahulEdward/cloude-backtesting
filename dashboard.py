"""
Dashboard for final surviving strategies.
Professional dark-theme layout with equity curves, drawdown charts, and sortable table.
"""

import logging
import webbrowser
import threading

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dash import Dash, html, dcc, dash_table, Input, Output

import config

logger = logging.getLogger(__name__)

# ── Color Palette ──
BG = "#0a0e17"
SURFACE = "#111827"
CARD = "#1a2035"
BORDER = "#2d3654"
TEXT = "#e5e7eb"
MUTED = "#6b7280"
CYAN = "#06b6d4"
GREEN = "#10b981"
RED = "#ef4444"
AMBER = "#f59e0b"
BLUE = "#3b82f6"
ORANGE = "#f97316"
PINK = "#ec4899"
PURPLE = "#8b5cf6"

FONT = "'Inter','Segoe UI',system-ui,-apple-system,sans-serif"
MONO = "'JetBrains Mono','Fira Code','Cascadia Code','Consolas',monospace"
COLORS = [CYAN, GREEN, PINK, AMBER, BLUE, ORANGE, PURPLE, RED]


def _rgba(hex_color, alpha):
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


# ─────────────────────── Layout Components ───────────────────────


def _stat_card(label, value, color, icon=""):
    return html.Div(style={
        "flex": "1 1 180px", "minWidth": "160px",
        "background": f"linear-gradient(135deg, {_rgba(color, 0.08)}, {_rgba(color, 0.02)})",
        "border": f"1px solid {_rgba(color, 0.25)}",
        "borderRadius": "12px", "padding": "20px 24px",
        "textAlign": "center", "position": "relative", "overflow": "hidden",
    }, children=[
        html.Div(style={
            "position": "absolute", "top": "0", "left": "0", "right": "0",
            "height": "3px", "background": f"linear-gradient(90deg, {color}, {_rgba(color, 0.3)})",
        }),
        html.Div(label, style={
            "fontSize": "11px", "fontWeight": "600", "color": MUTED,
            "textTransform": "uppercase", "letterSpacing": "1.2px", "marginBottom": "10px",
        }),
        html.Div(f"{icon}{value}", style={
            "fontSize": "28px", "fontWeight": "800", "color": color,
            "lineHeight": "1", "fontFamily": MONO,
        }),
    ])


# ─────────────────────── Charts ───────────────────────


def _build_equity_chart(survivors, indices, phase_key, title):
    """Build equity + drawdown stacked chart with proper sizing."""
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        row_heights=[0.72, 0.28], vertical_spacing=0.04,
        subplot_titles=["Portfolio Value ($)", "Drawdown (%)"],
    )

    has_data = False
    for i, idx in enumerate(indices):
        if idx >= len(survivors):
            continue
        r = survivors[idx]
        pf = r[phase_key].get("portfolio")
        if pf is None:
            continue
        color = COLORS[i % len(COLORS)]
        name = r["strategy"]

        try:
            eq = pf.value()
            fig.add_trace(go.Scatter(
                x=eq.index, y=eq.values, mode="lines", name=name,
                line=dict(color=color, width=2, shape="spline", smoothing=0.8),
                legendgroup=name, showlegend=True,
                hovertemplate=f"<b>{name}</b><br>Value: $%{{y:,.0f}}<br>%{{x|%b %d, %Y}}<extra></extra>",
            ), row=1, col=1)

            dd = pf.drawdown() * 100
            fig.add_trace(go.Scatter(
                x=dd.index, y=dd.values, mode="lines", name=f"{name} DD",
                line=dict(color=color, width=1.2, shape="spline", smoothing=0.8),
                fill="tozeroy", fillcolor=_rgba(color, 0.08),
                legendgroup=name, showlegend=False,
                hovertemplate=f"<b>{name}</b><br>Drawdown: %{{y:.1f}}%<br>%{{x|%b %d, %Y}}<extra></extra>",
            ), row=2, col=1)
            has_data = True
        except Exception as e:
            logger.warning(f"Chart error for {name} {phase_key}: {e}")

    # Reference lines
    fig.add_hline(y=config.INITIAL_CAPITAL, line_dash="dot",
                  line_color=_rgba(MUTED, 0.4), line_width=1, row=1, col=1,
                  annotation_text="Initial Capital", annotation_font_color=MUTED,
                  annotation_font_size=9)
    fig.add_hline(y=-config.MAX_DRAWDOWN_THRESHOLD * 100, line_dash="dot",
                  line_color=_rgba(RED, 0.6), line_width=1, row=2, col=1,
                  annotation_text=f"Max DD Threshold ({config.MAX_DRAWDOWN_THRESHOLD:.0%})",
                  annotation_font_color=RED, annotation_font_size=9)

    fig.update_layout(
        title=dict(
            text=f"<b>{title}</b>",
            font=dict(size=16, color=TEXT, family=FONT),
            x=0.5, y=0.98, xanchor="center",
        ),
        height=520,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, color=TEXT, size=11),
        legend=dict(
            orientation="h", yanchor="top", y=-0.08, xanchor="center", x=0.5,
            font=dict(size=11, color=TEXT), bgcolor="rgba(0,0,0,0)",
            bordercolor="rgba(0,0,0,0)",
        ),
        margin=dict(l=60, r=20, t=45, b=50),
        hovermode="x unified",
    )

    # Clean axes - no grid lines
    for row in [1, 2]:
        fig.update_xaxes(
            showgrid=False, zeroline=False,
            tickfont=dict(size=10, color=MUTED),
            linecolor=_rgba(BORDER, 0.3), linewidth=1,
            row=row, col=1,
        )
        fig.update_yaxes(
            showgrid=False, zeroline=False,
            tickfont=dict(size=10, color=MUTED),
            linecolor=_rgba(BORDER, 0.3), linewidth=1,
            row=row, col=1,
        )

    # Subplot title styling
    for ann in fig.layout.annotations:
        ann.font.size = 11
        ann.font.color = MUTED

    return fig


def _empty_fig(msg="Select strategies to view charts"):
    fig = go.Figure()
    fig.add_annotation(
        text=msg, xref="paper", yref="paper", x=0.5, y=0.5,
        showarrow=False, font=dict(size=14, color=MUTED),
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT), height=520,
        xaxis=dict(visible=False), yaxis=dict(visible=False),
    )
    return fig


# ─────────────────────── Table ───────────────────────


def _build_table_data(survivors):
    rows = []
    for i, r in enumerate(survivors):
        rows.append({
            "#": i + 1,
            "Strategy": r["strategy"],
            "IS Return": r["in_sample"]["total_return"],
            "IS DD": abs(r["in_sample"]["max_drawdown"]),
            "IS Sharpe": r["in_sample"]["sharpe_ratio"],
            "IS Sortino": r["in_sample"].get("sortino_ratio", 0.0),
            "IS Trades": r["in_sample"]["num_trades"],
            "IS Win%": r["in_sample"]["win_rate"],
            "OOS Return": r["out_of_sample"]["total_return"],
            "OOS DD": abs(r["out_of_sample"]["max_drawdown"]),
            "OOS Sharpe": r["out_of_sample"]["sharpe_ratio"],
            "OOS Sortino": r["out_of_sample"].get("sortino_ratio", 0.0),
            "OOS Trades": r["out_of_sample"]["num_trades"],
            "OOS Win%": r["out_of_sample"]["win_rate"],
        })
    return pd.DataFrame(rows)


def _format_table(df):
    out = df.copy()
    for c in ["IS Return", "OOS Return", "IS Win%", "OOS Win%", "IS DD", "OOS DD"]:
        if c in out.columns:
            out[c] = out[c].apply(lambda v: f"{v:.1%}")
    for c in ["IS Sharpe", "OOS Sharpe", "IS Sortino", "OOS Sortino"]:
        if c in out.columns:
            out[c] = out[c].apply(lambda v: f"{v:.2f}")
    return out


def _conditional_styles(n_rows):
    styles = []
    # Alternating row colors
    styles.append({
        "if": {"row_index": "odd"},
        "backgroundColor": "#0d1117",
    })
    styles.append({
        "if": {"row_index": "even"},
        "backgroundColor": SURFACE,
    })
    # Top 3 gold/silver/bronze
    medals = [(0, "#ffd700", "4px"), (1, "#c0c0c0", "3px"), (2, "#cd7f32", "3px")]
    for rank, color, width in medals:
        if rank < n_rows:
            styles.append({
                "if": {"row_index": rank},
                "borderLeft": f"{width} solid {color}",
            })
    # Active cell (clicked)
    styles.append({
        "if": {"state": "active"},
        "backgroundColor": _rgba(CYAN, 0.12),
        "border": f"1px solid {CYAN}",
        "color": TEXT,
    })
    # Selected cell
    styles.append({
        "if": {"state": "selected"},
        "backgroundColor": _rgba(CYAN, 0.08),
        "border": f"1px solid {_rgba(CYAN, 0.4)}",
        "color": TEXT,
    })
    return styles


# ─────────────────────── Dashboard ───────────────────────


def launch_dashboard(results: list[dict], pipeline_stats: dict):

    survivors = [r for r in results if r["final_passed"]]

    if not survivors:
        logger.warning("No strategies survived both phases")
        print("\n" + "=" * 60)
        print("  NO STRATEGIES SURVIVED BOTH PHASES")
        print("  Adjust MAX_DRAWDOWN_THRESHOLD in config.py")
        print("=" * 60)
        return

    survivors.sort(key=lambda r: r["out_of_sample"]["total_return"], reverse=True)
    logger.info(f"Launching dashboard with {len(survivors)} final survivors")

    raw_df = _build_table_data(survivors)
    display_df = _format_table(raw_df)

    n_combos = pipeline_stats["combos_tested"]
    n_is = pipeline_stats["is_survivors"]
    n_final = pipeline_stats["final_survivors"]
    best_ret = pipeline_stats["best_oos_return"]
    low_dd = pipeline_stats["lowest_oos_drawdown"]

    # Dropdown options
    dropdown_opts = []
    for i, r in enumerate(survivors):
        ret = r["out_of_sample"]["total_return"]
        dd = abs(r["out_of_sample"]["max_drawdown"])
        dropdown_opts.append({
            "label": f"#{i+1}  {r['strategy']}  |  Return: {ret:.1%}  |  DD: {dd:.1%}",
            "value": i,
        })
    default_selected = list(range(min(3, len(survivors))))

    app = Dash(__name__)

    # Full dark theme CSS
    app.index_string = '''<!DOCTYPE html>
<html>
<head>
    {%metas%}
    <title>Backtest Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    {%css%}
    <style>
        * { box-sizing: border-box; }
        body { margin: 0; background: ''' + BG + '''; font-family: 'Inter', system-ui, sans-serif; }
        ::-webkit-scrollbar { width: 8px; height: 8px; }
        ::-webkit-scrollbar-track { background: ''' + SURFACE + '''; }
        ::-webkit-scrollbar-thumb { background: ''' + BORDER + '''; border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: ''' + MUTED + '''; }

        /* ── Dash 4.0 dropdown dark theme ── */
        /* Dropdown wrapper & trigger */
        .dash-dropdown-wrapper,
        .dash-dropdown {
            background: ''' + SURFACE + ''' !important;
            border-color: ''' + BORDER + ''' !important;
            color: ''' + TEXT + ''' !important;
        }
        .dash-dropdown-trigger {
            color: ''' + TEXT + ''' !important;
        }
        .dash-dropdown-value {
            color: ''' + TEXT + ''' !important;
        }
        .dash-dropdown-value-item {
            background: ''' + _rgba(CYAN, 0.12) + ''' !important;
            border: 1px solid ''' + _rgba(CYAN, 0.25) + ''' !important;
            border-radius: 5px !important;
            color: ''' + CYAN + ''' !important;
            padding: 2px 8px !important;
            margin: 2px 4px 2px 0 !important;
        }
        .dash-dropdown-value-item span {
            color: ''' + CYAN + ''' !important;
            font-size: 11px !important;
        }
        .dash-dropdown-value-count {
            color: ''' + MUTED + ''' !important;
        }
        .dash-dropdown-clear,
        .dash-dropdown-clear svg {
            color: ''' + MUTED + ''' !important;
        }
        .dash-dropdown-clear:hover,
        .dash-dropdown-clear:hover svg {
            color: ''' + RED + ''' !important;
        }

        /* Popup content / menu */
        .dash-dropdown-content {
            background: ''' + CARD + ''' !important;
            border: 1px solid ''' + BORDER + ''' !important;
            border-radius: 8px !important;
            box-shadow: 0 8px 32px rgba(0,0,0,0.5) !important;
        }

        /* Search box */
        .dash-dropdown-search-container {
            background: ''' + SURFACE + ''' !important;
            border-bottom: 1px solid ''' + BORDER + ''' !important;
        }
        .dash-dropdown-search,
        .dash-dropdown-search input {
            background: ''' + SURFACE + ''' !important;
            color: ''' + TEXT + ''' !important;
            border-color: ''' + BORDER + ''' !important;
        }
        .dash-dropdown-search::placeholder {
            color: ''' + MUTED + ''' !important;
        }

        /* Select All / Deselect All buttons */
        .dash-dropdown-actions {
            background: ''' + _rgba(SURFACE, 0.8) + ''' !important;
            border-bottom: 1px solid ''' + BORDER + ''' !important;
            padding: 8px 12px !important;
        }
        .dash-dropdown-action-button {
            color: ''' + CYAN + ''' !important;
            background: transparent !important;
            border: none !important;
            cursor: pointer !important;
            font-size: 12px !important;
        }
        .dash-dropdown-action-button:hover {
            color: ''' + TEXT + ''' !important;
            text-decoration: underline !important;
        }

        /* Options list */
        .dash-options-list,
        .dash-dropdown-options {
            background: ''' + CARD + ''' !important;
        }

        /* Individual options */
        .dash-options-list-option,
        .dash-dropdown-option {
            background: ''' + CARD + ''' !important;
            color: ''' + TEXT + ''' !important;
            border-bottom: 1px solid ''' + _rgba(BORDER, 0.3) + ''' !important;
            padding: 10px 14px !important;
            font-size: 12px !important;
        }
        .dash-options-list-option:hover,
        .dash-dropdown-option:hover {
            background: ''' + _rgba(CYAN, 0.1) + ''' !important;
            color: ''' + CYAN + ''' !important;
        }
        .dash-options-list-option.selected,
        .dash-dropdown-option.selected {
            background: ''' + _rgba(CYAN, 0.08) + ''' !important;
        }
        .dash-options-list-option label,
        .dash-dropdown-option label {
            color: inherit !important;
        }

        /* Checkbox inside options */
        .dash-options-list-option input[type="checkbox"],
        .dash-dropdown-option input[type="checkbox"] {
            accent-color: ''' + CYAN + ''';
        }

        /* DataTable cell focus/select/active - override white defaults */
        .dash-spreadsheet-container .dash-spreadsheet-inner td.focused,
        .dash-spreadsheet-container .dash-spreadsheet-inner td.cell--selected,
        .dash-spreadsheet-container .dash-spreadsheet-inner td.cell--active,
        .dash-cell-value,
        td.dash-cell.focused,
        td.focused,
        td.cell--selected {
            background-color: ''' + _rgba(CYAN, 0.1) + ''' !important;
            color: ''' + TEXT + ''' !important;
            border: 1px solid ''' + _rgba(CYAN, 0.4) + ''' !important;
        }
        .dash-spreadsheet-container .dash-spreadsheet-inner input:not([type="checkbox"]) {
            background-color: ''' + SURFACE + ''' !important;
            color: ''' + TEXT + ''' !important;
        }
        .dash-spreadsheet-menu {
            background: ''' + CARD + ''' !important;
            border-color: ''' + BORDER + ''' !important;
        }

        /* DataTable pagination dark theme */
        .previous-next-container { background: transparent !important; }
        .previous-next-container button { color: ''' + TEXT + ''' !important; background: ''' + SURFACE + ''' !important; border: 1px solid ''' + BORDER + ''' !important; border-radius: 6px !important; }
        .previous-next-container button:hover { background: ''' + CARD + ''' !important; border-color: ''' + CYAN + ''' !important; }
        .page-number { color: ''' + TEXT + ''' !important; }
        .current-page-container input { color: ''' + TEXT + ''' !important; background: ''' + SURFACE + ''' !important; border: 1px solid ''' + BORDER + ''' !important; }
    </style>
</head>
<body>
    {%app_entry%}
    <footer>{%config%}{%scripts%}{%renderer%}</footer>
</body>
</html>'''

    app.layout = html.Div(style={
        "backgroundColor": BG, "minHeight": "100vh",
        "fontFamily": FONT, "color": TEXT,
    }, children=[

        # ── Header ──
        html.Div(style={
            "background": f"linear-gradient(180deg, {_rgba(CYAN, 0.06)}, transparent)",
            "borderBottom": f"1px solid {BORDER}",
            "padding": "24px 0",
        }, children=[
            html.Div(style={"maxWidth": "1480px", "margin": "0 auto", "padding": "0 36px"}, children=[
                html.Div(style={"display": "flex", "alignItems": "center", "justifyContent": "space-between", "flexWrap": "wrap", "gap": "12px"}, children=[
                    html.Div(children=[
                        html.H1("Backtest Dashboard", style={
                            "margin": "0", "fontSize": "26px", "fontWeight": "800",
                            "background": f"linear-gradient(135deg, {TEXT}, {CYAN})",
                            "WebkitBackgroundClip": "text", "WebkitTextFillColor": "transparent",
                            "letterSpacing": "-0.5px",
                        }),
                        html.P("Strategy survival analysis across in-sample and out-of-sample periods",
                               style={"margin": "4px 0 0 0", "color": MUTED, "fontSize": "12px"}),
                    ]),
                    html.Div(style={
                        "display": "flex", "gap": "8px", "flexWrap": "wrap",
                    }, children=[
                        _pill(f"{config.SYMBOL}"),
                        _pill(f"{config.TIMEFRAME}"),
                        _pill(f"{config.LOOKBACK_DAYS}d lookback"),
                        _pill(f"{config.TRAIN_RATIO:.0%} / {1-config.TRAIN_RATIO:.0%} split"),
                        _pill(f"Max DD: {config.MAX_DRAWDOWN_THRESHOLD:.0%}"),
                        _pill(f"${config.INITIAL_CAPITAL:,.0f}"),
                    ]),
                ]),
            ]),
        ]),

        # ── Body ──
        html.Div(style={"maxWidth": "1480px", "margin": "0 auto", "padding": "28px 36px 60px"}, children=[

            # ── Stats Row ──
            html.Div(style={"display": "flex", "gap": "16px", "marginBottom": "28px", "flexWrap": "wrap"}, children=[
                _stat_card("Combos Tested", str(n_combos), BLUE),
                _stat_card("IS Survivors", str(n_is), AMBER),
                _stat_card("Final Survivors", str(n_final), GREEN),
                _stat_card("Best OOS Return", f"{best_ret:.1%}", CYAN),
                _stat_card("Lowest OOS DD", f"{low_dd:.1%}", ORANGE),
            ]),

            # ── Strategy Selector ──
            html.Div(style={
                "backgroundColor": CARD, "border": f"1px solid {BORDER}",
                "borderRadius": "14px", "padding": "24px 28px", "marginBottom": "24px",
            }, children=[
                html.Div(style={"display": "flex", "alignItems": "center", "gap": "12px", "marginBottom": "12px"}, children=[
                    html.Div(style={
                        "width": "8px", "height": "8px", "borderRadius": "50%",
                        "backgroundColor": GREEN, "boxShadow": f"0 0 8px {_rgba(GREEN, 0.5)}",
                    }),
                    html.H3("Strategy Selector", style={"margin": "0", "fontSize": "16px", "fontWeight": "700"}),
                    html.Span(f"{len(survivors)} strategies survived", style={
                        "color": MUTED, "fontSize": "12px",
                        "backgroundColor": _rgba(MUTED, 0.1), "padding": "2px 10px",
                        "borderRadius": "12px", "border": f"1px solid {_rgba(MUTED, 0.2)}",
                    }),
                ]),
                dcc.Dropdown(
                    id="strategy-dropdown",
                    options=dropdown_opts,
                    value=default_selected,
                    multi=True,
                    placeholder="Search and select strategies to compare...",
                    style={"fontSize": "12px"},
                ),
            ]),

            # ── Charts ──
            html.Div(style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "20px", "marginBottom": "28px"}, children=[
                html.Div(style={
                    "backgroundColor": CARD, "border": f"1px solid {BORDER}",
                    "borderRadius": "14px", "padding": "20px", "overflow": "hidden",
                }, children=[dcc.Graph(id="oos-chart", figure=_empty_fig(), config={"displayModeBar": True, "displaylogo": False})]),
                html.Div(style={
                    "backgroundColor": CARD, "border": f"1px solid {BORDER}",
                    "borderRadius": "14px", "padding": "20px", "overflow": "hidden",
                }, children=[dcc.Graph(id="is-chart", figure=_empty_fig(), config={"displayModeBar": True, "displaylogo": False})]),
            ]),

            # ── Table ──
            html.Div(style={
                "backgroundColor": CARD, "border": f"1px solid {BORDER}",
                "borderRadius": "14px", "padding": "24px 28px",
            }, children=[
                html.Div(style={"display": "flex", "alignItems": "center", "justifyContent": "space-between", "marginBottom": "16px"}, children=[
                    html.Div(children=[
                        html.H3("Surviving Strategies", style={"margin": "0 0 4px 0", "fontSize": "16px", "fontWeight": "700"}),
                        html.P("Passed max-drawdown filter in both in-sample and out-of-sample phases. Ranked by OOS return.",
                               style={"color": MUTED, "fontSize": "11px", "margin": "0"}),
                    ]),
                    html.Div(f"{n_final} strategies", style={
                        "color": GREEN, "fontSize": "13px", "fontWeight": "600",
                        "backgroundColor": _rgba(GREEN, 0.1), "padding": "6px 14px",
                        "borderRadius": "8px", "border": f"1px solid {_rgba(GREEN, 0.25)}",
                    }),
                ]),
                dash_table.DataTable(
                    id="survivors-table",
                    columns=[{"name": c, "id": c} for c in display_df.columns],
                    data=display_df.to_dict("records"),
                    sort_action="native",
                    page_action="native",
                    page_size=15,
                    style_table={"overflowX": "auto", "borderRadius": "10px"},
                    style_cell={
                        "textAlign": "center", "padding": "10px 14px",
                        "backgroundColor": SURFACE, "color": TEXT,
                        "border": f"1px solid {_rgba(BORDER, 0.6)}",
                        "fontSize": "11px", "fontFamily": MONO,
                        "whiteSpace": "nowrap", "minWidth": "75px",
                    },
                    style_cell_conditional=[
                        {"if": {"column_id": "Strategy"}, "textAlign": "left", "minWidth": "200px", "fontFamily": FONT, "fontWeight": "600"},
                        {"if": {"column_id": "#"}, "minWidth": "40px", "maxWidth": "50px", "fontWeight": "700", "color": MUTED},
                    ],
                    style_header={
                        "fontWeight": "700", "backgroundColor": _rgba(CYAN, 0.06),
                        "color": CYAN, "border": f"1px solid {_rgba(BORDER, 0.6)}",
                        "fontSize": "10px", "textTransform": "uppercase",
                        "letterSpacing": "0.8px", "fontFamily": FONT,
                        "padding": "12px 14px",
                    },
                    style_data_conditional=_conditional_styles(len(display_df)),
                ),
            ]),

            # ── Footer ──
            html.Div(style={"textAlign": "center", "marginTop": "40px", "color": MUTED, "fontSize": "11px"}, children=[
                html.Span("Built with vectorbt + Plotly Dash  |  "),
                html.Span(f"{config.SYMBOL} {config.TIMEFRAME}  |  "),
                html.Span(f"{n_combos} combos tested  |  {n_final} survivors"),
            ]),
        ]),
    ])

    # ── Callbacks ──
    @app.callback(
        [Output("oos-chart", "figure"), Output("is-chart", "figure")],
        Input("strategy-dropdown", "value"),
    )
    def update_charts(selected):
        if not selected:
            return _empty_fig(), _empty_fig()
        indices = selected if isinstance(selected, list) else [selected]
        oos = _build_equity_chart(survivors, indices, "out_of_sample", "Out-of-Sample Performance")
        is_ = _build_equity_chart(survivors, indices, "in_sample", "In-Sample Performance")
        return oos, is_

    url = f"http://{config.DASHBOARD_HOST}:{config.DASHBOARD_PORT}"
    print(f"\n{'='*60}")
    print(f"  Dashboard live at {url}")
    print(f"  {n_final} final survivors from {n_combos} combos tested")
    print(f"{'='*60}\n")

    threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    app.run(host=config.DASHBOARD_HOST, port=config.DASHBOARD_PORT, debug=False)


def _pill(text):
    return html.Span(text, style={
        "display": "inline-block", "padding": "4px 12px",
        "backgroundColor": _rgba(MUTED, 0.1), "border": f"1px solid {_rgba(MUTED, 0.2)}",
        "borderRadius": "20px", "fontSize": "11px", "color": MUTED, "fontWeight": "500",
    })
