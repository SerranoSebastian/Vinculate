import streamlit as st

PALETA_SEDECO = ["#AF2140", "#D0B786", "#922542", "#F2E6D3", "#62182F"]
ESCALA_SEDECO = ["#F2E6D3", "#D0B786", "#AF2140", "#922542", "#62182F"]


def aplicar_tema_grafica(fig):
    fig.update_layout(
        template="plotly_white",
        colorway=PALETA_SEDECO,
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font={"color": "#111111", "size": 13},
        title_font={"color": "#62182F"},
        legend={
            "font": {"color": "#111111"},
            "title": {"font": {"color": "#111111"}},
        },
        hoverlabel={
            "bgcolor": "#FFFFFF",
            "bordercolor": "#D0B786",
            "font_color": "#111111",
        },
    )
    fig.update_xaxes(
        color="#111111",
        tickfont={"color": "#111111"},
        title_font={"color": "#111111"},
        gridcolor="rgba(208,183,134,0.38)",
        linecolor="#8A6F58",
        zerolinecolor="#D0B786",
    )
    fig.update_yaxes(
        color="#111111",
        tickfont={"color": "#111111"},
        title_font={"color": "#111111"},
        gridcolor="rgba(208,183,134,0.38)",
        linecolor="#8A6F58",
        zerolinecolor="#D0B786",
    )
    fig.update_coloraxes(
        colorbar={
            "tickfont": {"color": "#111111"},
            "title": {"font": {"color": "#111111"}},
        }
    )
    fig.update_annotations(font={"color": "#111111"})
    return fig


def aplicar_estilos():
    st.markdown("""
    <style>
    :root {
        --sedeco-guinda: #AF2140;
        --sedeco-guinda-secundario: #922542;
        --sedeco-guinda-oscuro: #62182F;
        --sedeco-dorado: #D0B786;
        --sedeco-beige: #F2E6D3;
        --sedeco-blanco: #FFFFFF;
        --sedeco-transition-fast: 140ms;
        --sedeco-transition-normal: 220ms;
        --sedeco-ease: cubic-bezier(0.22, 1, 0.36, 1);
    }

    @keyframes sedeco-entrada-suave {
        from {
            opacity: 0.96;
            transform: translateY(4px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }


    @keyframes vinculate-titulo {
        from { opacity: 0; transform: translateY(8px) scale(0.99); }
        to { opacity: 1; transform: translateY(0) scale(1); }
    }

    @keyframes vinculate-brillo {
        0%, 100% { box-shadow: 0 8px 22px rgba(98,24,47,0.08); }
        50% { box-shadow: 0 10px 28px rgba(175,33,64,0.14); }
    }

    @keyframes sedeco-aviso {
        from {
            opacity: 0;
            transform: translateY(-5px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    .stApp {
        background:
            radial-gradient(circle at 92% 8%, rgba(208,183,134,0.2), transparent 25%),
            linear-gradient(135deg, #FFFFFF 0%, #FBF7F1 55%, #F2E6D3 100%);
        color: #1A1A1A;
    }

    [data-testid="stHeader"] {
        background: rgba(255,255,255,0.72);
        backdrop-filter: blur(8px);
    }

    /* Entrada discreta: evita destellos largos durante los reruns de Streamlit. */
    [data-testid="stMainBlockContainer"] {
        animation: sedeco-entrada-suave var(--sedeco-transition-normal) var(--sedeco-ease) both;
    }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #62182F 0%, #7B1D39 52%, #922542 100%);
        border-right: 1px solid rgba(208,183,134,0.65);
    }

    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] span {
        color: #FFFFFF !important;
    }

    [data-testid="stSidebar"] [role="radiogroup"] label {
        border-radius: 10px;
        transition:
            background-color var(--sedeco-transition-fast) ease,
            transform var(--sedeco-transition-fast) var(--sedeco-ease);
    }

    [data-testid="stSidebar"] [role="radiogroup"] label:hover {
        background: rgba(208,183,134,0.18);
        transform: translateX(3px);
    }

    h1, h2, h3 {
        color: #62182F;
        font-weight: 800;
    }

    p, label, [data-testid="stCaptionContainer"] {
        color: #1A1A1A;
    }

    hr {
        border-color: rgba(208,183,134,0.55) !important;
    }

    .card {
        padding: 22px;
        border-radius: 22px;
        background: rgba(255,255,255,0.9);
        border: 1px solid rgba(208,183,134,0.62);
        box-shadow: 0 10px 30px rgba(98,24,47,0.1);
        transition:
            transform var(--sedeco-transition-normal) var(--sedeco-ease),
            box-shadow var(--sedeco-transition-normal) ease,
            border-color var(--sedeco-transition-normal) ease;
    }

    .card:hover {
        transform: translateY(-2px);
        border-color: #AF2140;
        box-shadow: 0 14px 34px rgba(98,24,47,0.16);
    }

    [data-testid="stMetricValue"] {
        color: #AF2140;
        font-size: 34px;
    }

    [data-testid="stMetricLabel"] p,
    [data-testid="stMetricDelta"] {
        color: #1A1A1A !important;
    }

    [data-testid="stVerticalBlockBorderWrapper"] {
        background: rgba(255,255,255,0.92);
        border-color: rgba(208,183,134,0.72) !important;
        box-shadow: 0 8px 22px rgba(98,24,47,0.08);
    }

    .insight {
        padding: 24px;
        border-radius: 22px;
        background: linear-gradient(135deg, #62182F, #922542, #AF2140);
        border: 1px solid rgba(208,183,134,0.72);
        color: white;
        font-size: 17px;
        line-height: 1.6;
        transition:
            transform var(--sedeco-transition-normal) var(--sedeco-ease),
            box-shadow var(--sedeco-transition-normal) ease;
    }

    .insight:hover {
        transform: translateY(-2px);
        box-shadow: 0 12px 32px rgba(98,24,47,0.2);
    }

    .smallbox {
        padding: 16px;
        border-radius: 16px;
        background: rgba(255,255,255,0.84);
        border: 1px solid rgba(208,183,134,0.55);
        transition:
            background-color var(--sedeco-transition-fast) ease,
            border-color var(--sedeco-transition-fast) ease;
    }

    .smallbox:hover {
        background: #FFFFFF;
        border-color: #AF2140;
    }

    /* Botones y controles: respuesta visual inmediata sin alterar su lógica. */
    .stButton > button,
    .stDownloadButton > button,
    [data-testid="stFormSubmitButton"] > button {
        color: #FFFFFF !important;
        background: linear-gradient(135deg, #AF2140, #922542) !important;
        border-color: #D0B786 !important;
        transition:
            transform var(--sedeco-transition-fast) var(--sedeco-ease),
            box-shadow var(--sedeco-transition-fast) ease,
            border-color var(--sedeco-transition-fast) ease,
            background-color var(--sedeco-transition-fast) ease;
    }

    .stButton > button p,
    .stDownloadButton > button p,
    [data-testid="stFormSubmitButton"] > button p {
        color: #FFFFFF !important;
        font-weight: 700;
    }
    /* Fuerza texto e iconos blancos en todos los botones de acción, incluidos forms y botones secundarios. */
    .stButton > button *,
    .stDownloadButton > button *,
    [data-testid="stFormSubmitButton"] > button *,
    button[kind="primary"] *,
    button[kind="secondary"] * {
        color: #FFFFFF !important;
        fill: #FFFFFF !important;
    }

    .stButton > button span,
    .stDownloadButton > button span,
    [data-testid="stFormSubmitButton"] > button span {
        color: #FFFFFF !important;
    }

    .stButton > button:hover,
    .stDownloadButton > button:hover,
    [data-testid="stFormSubmitButton"] > button:hover {
        transform: translateY(-1px);
        color: #FFFFFF;
        border-color: #F2E6D3;
        box-shadow: 0 7px 18px rgba(98,24,47,0.25);
    }

    .stButton > button:active,
    .stDownloadButton > button:active,
    [data-testid="stFormSubmitButton"] > button:active {
        transform: translateY(0) scale(0.99);
    }

    [data-baseweb="input"],
    [data-baseweb="select"] > div,
    [data-baseweb="textarea"],
    [data-testid="stDateInput"] [data-baseweb="input"] {
        background-color: #FFFFFF !important;
        border-color: #8A6F58 !important;
        color: #111111 !important;
        box-shadow: none;
        transition:
            border-color var(--sedeco-transition-fast) ease,
            box-shadow var(--sedeco-transition-fast) ease;
    }

    [data-baseweb="input"] input,
    [data-baseweb="textarea"] textarea,
    [data-baseweb="select"] input,
    [data-baseweb="select"] span,
    [data-baseweb="select"] div {
        color: #111111 !important;
        -webkit-text-fill-color: #111111 !important;
    }

    input::placeholder,
    textarea::placeholder {
        color: #666666 !important;
        -webkit-text-fill-color: #666666 !important;
        opacity: 1 !important;
    }

    input:disabled,
    textarea:disabled,
    [aria-disabled="true"] {
        color: #333333 !important;
        -webkit-text-fill-color: #333333 !important;
        background-color: #F4EFE8 !important;
        opacity: 1 !important;
    }

    [data-baseweb="popover"],
    [data-baseweb="menu"],
    [role="listbox"],
    [role="option"] {
        background-color: #FFFFFF !important;
        color: #111111 !important;
    }

    [role="option"]:hover,
    [aria-selected="true"][role="option"] {
        background-color: #F2E6D3 !important;
        color: #111111 !important;
    }

    [data-testid="stWidgetLabel"] p,
    [data-testid="stMarkdownContainer"] p,
    [data-testid="stCaptionContainer"] {
        color: #1A1A1A;
    }

    [data-testid="stTabs"] [aria-selected="true"] {
        color: #AF2140 !important;
        border-bottom-color: #AF2140 !important;
    }

    [data-testid="stTabs"] button p,
    [role="radiogroup"] label p,
    [role="radiogroup"] label span {
        color: #1A1A1A !important;
    }

    [data-testid="stSidebar"] [role="radiogroup"] label p,
    [data-testid="stSidebar"] [role="radiogroup"] label span {
        color: #FFFFFF !important;
    }

    [data-testid="stDataFrame"],
    [data-testid="stTable"] {
        background: #FFFFFF;
        color: #111111;
    }

    [data-testid="stProgressBar"] > div > div > div {
        background-color: #AF2140;
    }

    /* Portada temporal previa al acceso al sistema. */
    .sedeco-portada {
        max-width: 760px;
        margin: 10vh auto 1.5rem auto;
        padding: 3.25rem 3rem 3rem;
        text-align: center;
        background:
            radial-gradient(circle at 50% 0%, rgba(208,183,134,0.2), transparent 38%),
            #FFFFFF;
        border: 1px solid #D0B786;
        border-radius: 30px;
        box-shadow: 0 22px 60px rgba(98,24,47,0.16);
        animation: sedeco-entrada-suave 420ms var(--sedeco-ease) both;
    }

    .sedeco-portada-marca {
        color: #AF2140;
        font-size: clamp(3.4rem, 8vw, 6.4rem);
        font-weight: 900;
        line-height: 0.95;
        letter-spacing: 0.08em;
        margin: 0;
    }

    .sedeco-portada-linea {
        width: 92px;
        height: 4px;
        margin: 1.5rem auto 1.4rem;
        border-radius: 99px;
        background: linear-gradient(90deg, #AF2140, #D0B786);
    }

    .sedeco-portada-etiqueta {
        color: #AF2140;
        font-size: 0.82rem;
        font-weight: 800;
        letter-spacing: 0.2em;
        text-transform: uppercase;
        margin: 0.5rem 0 0.8rem;
    }

    .sedeco-portada-titulo {
        color: #1A1A1A;
        font-size: clamp(2rem, 4vw, 3.6rem);
        font-weight: 850;
        line-height: 1.05;
        margin: 0;
    }

    .sedeco-portada-texto {
        color: #333333;
        font-size: 1.05rem;
        line-height: 1.6;
        max-width: 700px;
        margin: 1rem auto 0;
    }

    div.st-key-iniciar_sesion button {
        min-height: 3.25rem;
        width: 100%;
        color: #FFFFFF;
        background: linear-gradient(135deg, #AF2140, #922542);
        border: 1px solid #D0B786;
        border-radius: 14px;
        font-size: 1.05rem;
        font-weight: 800;
        box-shadow: 0 9px 24px rgba(98,24,47,0.2);
    }

    div.st-key-iniciar_sesion button p {
        color: #FFFFFF !important;
    }

    div.st-key-iniciar_sesion button:hover {
        color: #FFFFFF;
        border-color: #F2E6D3;
        box-shadow: 0 12px 28px rgba(98,24,47,0.28);
    }

    [data-testid="stAlert"],
    [data-testid="stToast"] {
        animation: sedeco-aviso var(--sedeco-transition-normal) var(--sedeco-ease) both;
    }

    [data-testid="stSpinner"] {
        animation: sedeco-aviso var(--sedeco-transition-fast) ease both;
    }

    [data-testid="stProgressBar"] > div > div {
        transition: width 300ms var(--sedeco-ease);
    }


    /* Animaciones visuales ligeras: CSS puro, sin recargar datos ni ejecutar scripts. */
    h1 {
        animation: vinculate-titulo 320ms var(--sedeco-ease) both;
    }

    [data-testid="stMetric"] {
        transition: transform var(--sedeco-transition-fast) var(--sedeco-ease), box-shadow var(--sedeco-transition-fast) ease;
    }

    [data-testid="stMetric"]:hover {
        transform: translateY(-2px);
    }

    [data-testid="stTabs"] button {
        transition: transform var(--sedeco-transition-fast) var(--sedeco-ease), color var(--sedeco-transition-fast) ease;
    }

    [data-testid="stTabs"] button:hover {
        transform: translateY(-1px);
    }

    /* Texto e iconos siempre blancos en botones de acción. */
    button[kind="primary"],
    button[kind="secondary"],
    .stButton > button,
    .stDownloadButton > button,
    [data-testid="stFormSubmitButton"] > button {
        color: #FFFFFF !important;
        -webkit-text-fill-color: #FFFFFF !important;
    }

    button[kind="primary"] *,
    button[kind="secondary"] *,
    .stButton > button *,
    .stDownloadButton > button *,
    [data-testid="stFormSubmitButton"] > button * {
        color: #FFFFFF !important;
        -webkit-text-fill-color: #FFFFFF !important;
        fill: #FFFFFF !important;
    }

    /* Accesibilidad: respeta a quien tenga desactivadas las animaciones. */
    @media (prefers-reduced-motion: reduce) {
        *,
        *::before,
        *::after {
            animation-duration: 0.01ms !important;
            animation-iteration-count: 1 !important;
            transition-duration: 0.01ms !important;
            scroll-behavior: auto !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)
