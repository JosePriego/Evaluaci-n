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
    try:
        api_key = st.secrets["SCOPUS_API_KEY"]
    except:
        return None, "Falta_Clave"

    headers = {"X-ELS-APIKey": api_key, "Accept": "application/json"}
    
    # 1. Búsqueda del artículo
    url_search = f"https://api.elsevier.com/content/search/scopus?query=DOI({doi})"
    try:
        res_search = requests.get(url_search, headers=headers, timeout=10)
        if res_search.status_code != 200: return None, res_search.status_code
        
        data_s = res_search.json()
        entradas = data_s.get('search-results', {}).get('entry', [])
        if not entradas: return None, 404
        
        entry = entradas[0]

        # --- AQUÍ ESTÁ LA CORRECCIÓN QUE HAS DETECTADO ---
        res_final = {
            "citas": entry.get('citedby-count', 'N/A'),
            "año": entry.get('prism:coverDate', '').split('-')[0],
            "issn": entry.get('prism:issn') or entry.get('prism:eIssn'),
            # Intentamos capturar el FWCI directamente del entry
            "fwci": entry.get('fieldWeightedCitationImpact', 'N/A'), 
            "sjr": "N/A",
            "cs": "N/A",
            "permisos_revista": True
        }

        # 2. Búsqueda de métricas de la revista
        if res_final["issn"]:
            issn_l = res_final["issn"].replace("-", "").strip()
            url_rev = f"https://api.elsevier.com/content/serial/title/issn/{issn_l}?view=ENHANCED"
            res_rev = requests.get(url_rev, headers=headers, timeout=10)
            if res_rev.status_code == 200:
                d_rev = res_rev.json().get('serial-metadata-response', {}).get('entry', [{}])[0]
                # Extraer SJR del año correspondiente
                for s in d_rev.get('SJRList', {}).get('SJR', []):
                    if str(s.get('@year')) == str(res_final["año"]): 
                        res_final["sjr"] = s.get('$')
                # Extraer CiteScore del año correspondiente
                for c in d_rev.get('citeScoreYearInfoList', {}).get('citeScoreYearInfo', []):
                    if str(c.get('@year')) == str(res_final["año"]): 
                        res_final["cs"] = c.get('citeScore')
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
    
    st.subheader("Impacto en Bases de Datos:")
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
                st.warning("🔒 Tu licencia no permite ver métricas de revista (SJR/CS).")
        else:
            st.error(f"Error Scopus: {status}")

    # Altmetric
    score = obtener_datos_altmetric(doi_l)
    if score: st.warning(f"**Altmetric Attention Score:** {score}")

    st.divider()
    st.link_button("🔗 Ver artículo en la web original", f"https://doi.org/{doi_l}")
