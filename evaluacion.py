import streamlit as st
import requests
import urllib.parse

# --- FUNCIONES DE EXTRACCIÓN ---

def obtener_datos_openalex(doi):
    url = f"https://api.openalex.org/works/doi:{doi}"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            d = res.json()
            return d.get('cited_by_count', 0), d.get('fwci', 'N/A')
    except: pass
    return "N/A", "N/A"

def obtener_datos_dimensions(doi):
    url = f"https://metrics-api.dimensions.ai/doi/{doi}"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            d = res.json()
            return d.get('times_cited', 0), d.get('field_citation_ratio', 'N/A')
    except: pass
    return "N/A", "N/A"

def obtener_datos_scopus(doi):
    try:
        api_key = st.secrets["SCOPUS_API_KEY"]
    except:
        return None, "Falta_Clave"

    headers = {"X-ELS-APIKey": api_key, "Accept": "application/json"}
    url = f"https://api.elsevier.com/content/search/scopus?query=DOI({doi})"
    
    try:
        res = requests.get(url, headers=headers, timeout=15)
        data = res.json()
        entradas = data.get('search-results', {}).get('entry', [])
        
        if not entradas or "error" in entradas[0]:
            return None, 404
        
        articulo = entradas[0]
        año = articulo.get('prism:coverDate', 'N/A').split('-')[0]
        issn = articulo.get('prism:issn') or articulo.get('prism:eIssn')
        
        res_final = {
            "citas": articulo.get('citedby-count', 'N/A'),
            "año": año,
            "issn": issn,
            "sjr": "N/A",
            "cs": "N/A",
            "permisos_revista": True
        }

        if issn:
            issn_l = str(issn).replace("-", "").strip()
            url_rev = f"https://api.elsevier.com/content/serial/title/issn/{issn_l}?view=ENHANCED"
            res_rev = requests.get(url_rev, headers=headers, timeout=10)
            if res_rev.status_code == 200:
                d_rev = res_rev.json().get('serial-metadata-response', {}).get('entry', [{}])[0]
                for s in d_rev.get('SJRList', {}).get('SJR', []):
                    if str(s.get('@year')) == str(año): res_final["sjr"] = s.get('$')
                for c in d_rev.get('citeScoreYearInfoList', {}).get('citeScoreYearInfo', []):
                    if str(c.get('@year')) == str(año): res_final["cs"] = c.get('citeScore')
            elif res_rev.status_code == 401:
                res_final["permisos_revista"] = False

        return res_final, 200
    except: return None, "Error_Conexion"

# --- INTERFAZ STREAMLIT ---

st.set_page_config(page_title="Evaluador de Investigación", layout="wide")
st.title("Evaluador de Investigación Profesional 🔬")

doi_input = st.text_input("Introduce el DOI del artículo:", value="10.1126/science.1199644")

if st.button("Analizar Impacto"):
    doi_l = doi_input.replace("https://doi.org/", "").strip()
    
    # 1. BLOQUE: IMPACTO DE LA APORTACIÓN
    st.header("📊 Impacto de la Aportación")
    
    # Obtención de datos
    c_oa, f_oa = obtener_datos_openalex(doi_l)
    dat_sco, stat_sco = obtener_datos_scopus(doi_l)
    c_di, f_di = obtener_datos_dimensions(doi_l)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("Scopus")
        st.metric("Citas", dat_sco['citas'] if stat_sco == 200 else "N/A")
        st.write(f"**Año:** {dat_sco['año'] if stat_sco == 200 else 'N/A'}")
        st.caption("Fuente oficial Elsevier")

    with col2:
        st.subheader("Dimensions")
        st.metric("Citas", c_di)
        st.write(f"**FCR:** {f_di}")
        st.caption("Field Citation Ratio")

    with col3:
        st.subheader("OpenAlex")
        st.metric("Citas", c_oa)
        st.write(f"**FWCI:** {f_oa}")
        st.caption("Field Weighted Citation Impact")

    # 2. BLOQUE: CALIDAD EDITORIAL (REVISTA)
    st.divider()
    st.header("🏢 Calidad de la Revista")
    
    if stat_sco == 200:
        if dat_sco["permisos_revista"]:
            m1, m2 = st.columns(2)
            m1.metric(f"SJR ({dat_sco['año']})", dat_sco['sjr'])
            m2.metric(f"CiteScore ({dat_sco['año']})", dat_sco['cs'])
        else:
            st.warning("🔒 Licencia de API limitada: Consulta el SJR/CiteScore manualmente en los enlaces inferiores.")
            st.info(f"ISSN: {dat_sco['issn']}")
    else:
        st.error("No se pudo recuperar información de la revista desde Scopus.")

    # 3. BLOQUE: ENLACES DE CONSULTA
    st.divider()
    st.header("🔗 Enlaces de Consulta")
    
    # Preparar URLs
    doi_query = urllib.parse.quote(f'DOI("{doi_l}")')
    url_scopus = f"https://www.scopus.com/results/results.uri?txtSearch={doi_query}&src=s&st1={doi_query}"
    url_wos = f"https://www.webofscience.com/wos/woscc/basic-search?query={doi_l}"
    
    c_enlace1, c_enlace2, c_enlace3 = st.columns(3)
    
    with c_enlace1:
        st.markdown(f"**Scopus Oficial**")
        st.write("Para consultar el FWCI real, percentiles y métricas detalladas.")
        st.link_button("Ir a Scopus", url_scopus)

    with c_enlace2:
        st.markdown(f"**Web of Science**")
        st.write("Consulta manual en WoS y JCR (requiere estar en red VPN/Uni).")
        st.link_button("Ir a WoS", url_wos)

    with c_enlace3:
        st.markdown(f"**Página del Artículo**")
        st.write("Enlace directo a la web original de la editorial (vía DOI).")
        st.link_button("Ir al DOI", f"https://doi.org/{doi_l}")
