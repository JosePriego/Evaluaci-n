import streamlit as st  
import requests

# --- FUNCIONES DE APOYO ---

def obtener_datos_openalex(doi):
    url = f"https://api.openalex.org/works/doi:{doi}"
    res = requests.get(url)
    if res.status_code == 200:
        d = res.json()
        return d.get('cited_by_count', 0), d.get('fwci', 'N/A')
    return 0, 'N/A'

def obtener_datos_dimensions(doi):
    url = f"https://metrics-api.dimensions.ai/doi/{doi}"
    res = requests.get(url)
    if res.status_code == 200:
        d = res.json()
        return d.get('times_cited', 0), d.get('field_citation_ratio', 'N/A')
    return 0, 'N/A'

def obtener_datos_altmetric(doi):
    url = f"https://api.altmetric.com/v1/doi/{doi}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            d = res.json()
            return round(d.get('score', 0))
        return None
    except: return None

def obtener_datos_scopus(doi):
    """
    Estrategia híbrida:
    1. Busca datos básicos (Citas, ISSN, Año).
    2. Intenta obtener el FWCI desde el endpoint de métricas.
    3. Intenta obtener SJR/CiteScore de la revista.
    """
    try:
        api_key = st.secrets["SCOPUS_API_KEY"]
    except:
        return None, "Falta_Clave"

    headers = {"X-ELS-APIKey": api_key, "Accept": "application/json"}
    
    # --- PASO 1: Datos Básicos del Artículo ---
    url_search = f"https://api.elsevier.com/content/search/scopus?query=DOI({doi})"
    try:
        res_search = requests.get(url_search, headers=headers, timeout=10)
        if res_search.status_code != 200: return None, f"Error API Search: {res_search.status_code}"
        
        data_s = res_search.json()
        entry = data_s.get('search-results', {}).get('entry', [])[0] if data_s.get('search-results', {}).get('entry') else None
        if not entry: return None, 404

        res_final = {
            "citas": entry.get('citedby-count', 0),
            "año": entry.get('prism:coverDate', '').split('-')[0],
            "issn": entry.get('prism:issn') or entry.get('prism:eIssn'),
            "fwci": "N/A",
            "sjr": "N/A",
            "cs": "N/A",
            "permisos_revista": True
        }

        # --- PASO 2: EL "TRUCO" PARA EL FWCI ---
        # Intentamos el endpoint de Metrics que es menos restrictivo que el de Abstract
        url_metrics = f"https://api.elsevier.com/content/abstract/citations?doi={doi}"
        res_met = requests.get(url_metrics, headers=headers, timeout=10)
        if res_met.status_code == 200:
            # Si responde, buscamos el valor de impacto ponderado
            d_met = res_met.json()
            # A veces viene en una estructura llamada 'citation-count-response'
            # Si no lo encontramos aquí, nos quedamos con el N/A
            pass 

        # --- PASO 3: Métricas de la Revista ---
        if res_final["issn"]:
            issn_l = res_final["issn"].replace("-", "")
            url_rev = f"https://api.elsevier.com/content/serial/title/issn/{issn_l}?view=ENHANCED"
            res_rev = requests.get(url_rev, headers=headers, timeout=10)
            if res_rev.status_code == 200:
                d_rev = res_rev.json().get('serial-metadata-response', {}).get('entry', [{}])[0]
                for s in d_rev.get('SJRList', {}).get('SJR', []):
                    if s.get('@year') == res_final["año"]: res_final["sjr"] = s.get('$')
                for c in d_rev.get('citeScoreYearInfoList', {}).get('citeScoreYearInfo', []):
                    if c.get('@year') == res_final["año"]: res_final["cs"] = c.get('citeScore')
            elif res_rev.status_code == 401:
                res_final["permisos_revista"] = False

        return res_final, 200
    except:
        return None, "Error_Conexion"

# --- INTERFAZ STREAMLIT ---

st.title("Evaluador de Investigación Profesional 🔬")
doi_input = st.text_input("Introduce el DOI:", value="10.1126/science.1199644")

if st.button("Buscar Métricas"):
    doi_l = doi_input.replace("https://doi.org/", "").strip()
    
    # Columnas para métricas rápidas
    c1, c2 = st.columns(2)
    
    # OpenAlex
    cit_oa, fw_oa = obtener_datos_openalex(doi_l)
    c1.success(f"**OpenAlex**\nCitas: {cit_oa} | FWCI: {fw_oa}")
    
    # Dimensions
    cit_di, fcr_di = obtener_datos_dimensions(doi_l)
    c2.info(f"**Dimensions**\nCitas: {cit_di} | FCR: {fcr_di}")
    
    # Scopus
    with st.spinner('Conectando con Scopus...'):
        dat, status = obtener_datos_scopus(doi_l)
        if status == 200:
            st.success(f"**Scopus:** {dat['citas']} citas | **FWCI: {dat['fwci']}** | Año: {dat['año']}")
            if dat["permisos_revista"]:
                m1, m2 = st.columns(2)
                m1.metric(f"SJR ({dat['año']})", dat['sjr'])
                m2.metric(f"CiteScore ({dat['año']})", dat['cs'])
            else:
                st.warning("🔒 Sin permiso para métricas de revista (SJR/CS).")
        else:
            st.error(f"Error Scopus: {status}")

    # Altmetric
    score = obtener_datos_altmetric(doi_l)
    if score: st.warning(f"**Altmetric Attention Score:** {score}")

    st.divider()
    st.link_button("🔗 Ver artículo en la web original", f"https://doi.org/{doi_l}")
