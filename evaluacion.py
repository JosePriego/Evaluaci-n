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
            # Extraemos citas y FWCI (OpenAlex los da muy bien)
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

st.set_page_config(page_title="Evaluador DOI Profesional", layout="centered")
st.title("Evaluador de Investigación Profesional 🔬")

doi_input = st.text_input("Introduce el DOI del artículo:", value="10.1126/science.1199644")

if st.button("Analizar Impacto"):
    doi_l = doi_input.replace("https://doi.org/", "").strip()
    
    st.divider()
    
    # 1. Bloque de Datos (Métricas de Citación)
    st.subheader("📊 Impacto de la Aportación")
    
    # Obtención de datos
    c_oa, f_oa = obtener_datos_openalex(doi_l)
    c_di, f_di = obtener_datos_dimensions(doi_l)
    dat_sco, stat_sco = obtener_datos_scopus(doi_l)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # CORRECCIÓN: Ahora imprimimos correctamente las citas de OpenAlex aquí
        st.metric("Citas OpenAlex", c_oa)
        st.caption(f"FWCI: {f_oa}")
        
    with col2:
        # Citas oficiales de Scopus
        st.metric("Citas Scopus", dat_sco['citas'] if stat_sco == 200 else "N/A")
        st.caption(f"Año: {dat_sco['año'] if stat_sco == 200 else '-'}")
        
    with col3:
        # Citas de Dimensions
        st.metric("Citas Dimensions", c_di)
        st.caption(f"FCR: {f_di}")

    # 2. Bloque de Revista
    st.divider()
    st.subheader("🏢 Calidad de la Revista (Scopus)")
    if stat_sco == 200:
        if dat_sco["permisos_revista"]:
            m1, m2 = st.columns(2)
            m1.metric(f"SJR ({dat_sco['año']})", dat_sco['sjr'])
            m2.metric(f"CiteScore ({dat_sco['año']})", dat_sco['cs'])
        else:
            st.warning("🔒 Licencia limitada para métricas de revista.")
    else:
        st.error("No se han podido recuperar datos de Scopus.")

    # 3. Botón FWCI (Búsqueda Exacta)
    st.divider()
    st.write("### Consulta FWCI Oficial")
    st.write("Pulsa para ir directamente a la ficha del artículo en Scopus:")
    
    # Codificamos el DOI para que la URL sea segura y usamos la sintaxis DOI("...")
    doi_encoded = urllib.parse.quote(f'DOI("{doi_l}")')
    url_scopus_exacta = f"https://www.scopus.com/results/results.uri?txtSearch={doi_encoded}&src=s&st1={doi_encoded}"
    
    st.link_button("🚀 FWCI", url_scopus_exacta, type="primary")

    st.divider()
    st.link_button("🔗 Web original (DOI.org)", f"https://doi.org/{doi_l}")
