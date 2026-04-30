import streamlit as st  
import requests

# --- FUNCIONES DE EXTRACCIÓN (APIs GRATUITAS) ---

def obtener_datos_openalex(doi):
    url = f"https://api.openalex.org/works/doi:{doi}"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            d = res.json()
            return d.get('cited_by_count', 0), d.get('fwci', 'N/A')
    except: pass
    return 0, 'N/A'

def obtener_datos_dimensions(doi):
    url = f"https://metrics-api.dimensions.ai/doi/{doi}"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            d = res.json()
            return d.get('times_cited', 0), d.get('field_citation_ratio', 'N/A')
    except: pass
    return 0, 'N/A'

def obtener_datos_altmetric(doi):
    url = f"https://api.altmetric.com/v1/doi/{doi}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            d = res.json()
            return round(d.get('score', 0))
    except: pass
    return None

# --- NÚCLEO DE SCOPUS (EL GRUPO DE INVESTIGACIÓN) ---

def obtener_datos_scopus(doi):
    try:
        api_key = st.secrets["SCOPUS_API_KEY"]
    except:
        return None, "Falta_Clave"

    headers = {"X-ELS-APIKey": api_key, "Accept": "application/json"}
    
    # PASO 1: Búsqueda con VISTA COMPLETA para intentar forzar el FWCI
    url_search = f"https://api.elsevier.com/content/search/scopus?query=DOI({doi})&view=COMPLETE"
    
    try:
        res_search = requests.get(url_search, headers=headers, timeout=15)
        datos_completos = res_search.json()
        
        # Extraemos la entrada del artículo
        entradas = datos_completos.get('search-results', {}).get('entry', [])
        if not entradas:
            return None, 404
        
        articulo = entradas[0]
        
        # Diccionario base de resultados
        res_final = {
            "citas": articulo.get('citedby-count', 'N/A'),
            "año": articulo.get('prism:coverDate', 'N/A').split('-')[0],
            "issn": articulo.get('prism:issn') or articulo.get('prism:eIssn'),
            "fwci": "No encontrado en el JSON",
            "sjr": "N/A",
            "cs": "N/A",
            "permisos_revista": True,
            "json_crudo": datos_completos  # Guardamos todo para el inspector
        }

        # Lógica de detección de FWCI (probamos varias claves posibles)
        claves_fwci = ['fieldWeightedCitationImpact', 'fwci', 'field-weighted-citation-impact']
        for clave in claves_fwci:
            valor = articulo.get(clave)
            if valor:
                res_final["fwci"] = valor
                break

        # PASO 2: Métricas de la Revista (SJR y CiteScore)
        if res_final["issn"]:
            issn_l = str(res_final["issn"]).replace("-", "").strip()
            url_rev = f"https://api.elsevier.com/content/serial/title/issn/{issn_l}?view=ENHANCED"
            res_rev = requests.get(url_rev, headers=headers, timeout=10)
            
            if res_rev.status_code == 200:
                d_rev = res_rev.json().get('serial-metadata-response', {}).get('entry', [{}])[0]
                # Buscar por año
                for s in d_rev.get('SJRList', {}).get('SJR', []):
                    if str(s.get('@year')) == str(res_final["año"]):
                        res_final["sjr"] = s.get('$')
                for c in d_rev.get('citeScoreYearInfoList', {}).get('citeScoreYearInfo', []):
                    if str(c.get('@year')) == str(res_final["año"]):
                        res_final["cs"] = c.get('citeScore')
            elif res_rev.status_code == 401:
                res_final["permisos_revista"] = False

        return res_final, 200
    except Exception as e:
        return None, f"Error de conexión: {str(e)}"

# --- INTERFAZ DE USUARIO (STREAMLIT) ---

st.set_page_config(page_title="Evaluador DOI Profesional", page_icon="🔬")
st.title("Evaluador de Investigación Profesional 🔬")
st.write("Introduce un DOI para auditar métricas de impacto.")

doi_input = st.text_input("DOI del artículo:", value="10.1126/science.1199644")

if st.button("Ejecutar Auditoría"):
    doi_l = doi_input.replace("https://doi.org/", "").strip()
    
    st.divider()
    
    # 1. Bloque de Datos Abiertos
    col_a, col_b = st.columns(2)
    with col_a:
        c_oa, f_oa = obtener_datos_openalex(doi_l)
        st.success(f"**OpenAlex**\nCitas: {c_oa} | FWCI: {f_oa}")
    with col_b:
        c_di, f_di = obtener_datos_dimensions(doi_l)
        st.info(f"**Dimensions**\nCitas: {c_di} | FCR: {f_di}")

    # 2. Bloque Scopus
    with st.spinner('Consultando Scopus (Vista Completa)...'):
        datos, status = obtener_datos_scopus(doi_l)
        
        if status == 200:
            st.success(f"**Scopus:** {datos['citas']} citas | **FWCI: {datos['fwci']}** | Año: {datos['año']}")
            
            if datos["permisos_revista"]:
                m1, m2 = st.columns(2)
                m1.metric(f"SJR ({datos['año']})", datos['sjr'])
                m2.metric(f"CiteScore ({datos['año']})", datos['cs'])
            else:
                st.warning("🔒 Tu API Key no tiene permiso para métricas de revista (SJR/CS).")
            
            # --- EL INSPECTOR DE DATOS CRUDOS ---
            with st.expander("🕵️‍♂️ INSPECTOR DE API: ¿Dónde está el FWCI?"):
                st.write("Usa 'Ctrl+F' y busca 'impact' o '24.92' para ver si Scopus nos envía el dato.")
                st.json(datos["json_crudo"])
                
        elif status == 404:
            st.error("DOI no encontrado en Scopus.")
        else:
            st.error(f"Fallo en Scopus: {status}")

    # 3. Altmetric
    score_alt = obtener_datos_altmetric(doi_l)
    if score_alt:
        st.warning(f"**Altmetric Attention Score:** {score_alt}")

    st.divider()
    st.link_button("🔗 Ver artículo en Scopus.com", f"https://doi.org/{doi_l}")
