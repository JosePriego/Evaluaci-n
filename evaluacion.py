# Importamos solo las librerías esenciales
import streamlit as st  
import requests

# --- DOCUMENTACIÓN DE FUNCIONES ---

def obtener_datos_openalex(doi):
    url = f"https://api.openalex.org/works/doi:{doi}"
    respuesta = requests.get(url)
    if respuesta.status_code == 200:
        datos = respuesta.json()
        citas = datos.get('cited_by_count', 'No disponible')
        fwci = datos.get('fwci', 'No disponible')
        return citas, fwci
    return None, None

def obtener_datos_dimensions(doi):
    url = f"https://metrics-api.dimensions.ai/doi/{doi}"
    respuesta = requests.get(url)
    if respuesta.status_code == 200:
        datos = respuesta.json()
        citas = datos.get('times_cited', 'No disponible')
        fcr = datos.get('field_citation_ratio', 'No disponible')
        return citas, fcr
    return None, None

def obtener_datos_altmetric(doi):
    url = f"https://api.altmetric.com/v1/doi/{doi}"
    cabeceras = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
    try:
        respuesta = requests.get(url, headers=cabeceras, timeout=10)
        if respuesta.status_code == 200:
            datos = respuesta.json()
            score = round(datos.get('score', 0)) if isinstance(datos.get('score'), (int, float)) else 'No disponible'
            desglose = {
                "X (Twitter)": datos.get('cited_by_tweeters_count', 0),
                "Noticias": datos.get('cited_by_msm_count', 0),
                "Wikipedia": datos.get('cited_by_wikipedia_count', 0)
            }
            return score, desglose, respuesta.status_code
        return None, None, respuesta.status_code
    except Exception:
        return None, None, "Error_Conexion"

def obtener_datos_scopus(doi):
    try:
        api_key = st.secrets["SCOPUS_API_KEY"]
    except KeyError:
        return None, "Falta_Clave"

    cabeceras = {
        "X-ELS-APIKey": api_key,
        "Accept": "application/json"
    }
    
    # --- PASO 1: Buscar el Artículo con vista DETALLADA para forzar el FWCI ---
    # Usamos el endpoint de 'abstract' en lugar de 'search' porque es más completo
    url_articulo = f"https://api.elsevier.com/content/abstract/doi/{doi}?field=abstractstats,authors,item"
    
    try:
        res_articulo = requests.get(url_articulo, headers=cabeceras, timeout=10)
        
        # Si el endpoint de abstract falla (a veces pasa por licencias), volvemos al search
        if res_articulo.status_code != 200:
            url_articulo = f"https://api.elsevier.com/content/search/scopus?query=DOI({doi})"
            res_articulo = requests.get(url_articulo, headers=cabeceras, timeout=10)
        
        datos = res_articulo.json()
        
        # Estructura para 'abstract' vs 'search'
        if 'abstracts-retrieval-response' in datos:
            core = datos['abstracts-retrieval-response'].get('coredata', {})
            stats = datos['abstracts-retrieval-response'].get('abstractstats', {})
            citas = core.get('citedby-count', 'No disponible')
            año_pub = core.get('prism:coverDate', '').split('-')[0]
            issn = core.get('prism:issn') or core.get('prism:eIssn')
            fwci = stats.get('fieldWeightedCitationImpact', 'N/A')
        else:
            # Lógica de respaldo (search)
            entradas = datos.get('search-results', {}).get('entry', [])
            if not entradas: return None, 404
            articulo = entradas[0]
            citas = articulo.get('citedby-count', 'No disponible')
            año_pub = articulo.get('prism:coverDate', '').split('-')[0]
            issn = articulo.get('prism:issn') or articulo.get('prism:eIssn')
            fwci = articulo.get('fieldWeightedCitationImpact', 'N/A')

        resultados_scopus = {
            "citas": citas, "año": año_pub, "issn": issn, "fwci": fwci,
            "sjr_historico": "No disponible", "citescore_historico": "No disponible",
            "permisos_revista": True 
        }
        
        # --- PASO 2: Buscar Métricas de la Revista ---
        if issn and año_pub:
            issn_limpio = str(issn).replace("-", "").strip()
            url_revista = f"https://api.elsevier.com/content/serial/title/issn/{issn_limpio}?view=ENHANCED"
            res_revista = requests.get(url_revista, headers=cabeceras, timeout=10)
            
            if res_revista.status_code == 200:
                datos_rev = res_revista.json()
                entry = datos_rev.get('serial-metadata-response', {}).get('entry', [{}])[0]
                
                for item in entry.get('SJRList', {}).get('SJR', []):
                    if str(item.get('@year')) == str(año_pub):
                        resultados_scopus["sjr_historico"] = item.get('$', 'No disponible')
                        break
                for item in entry.get('citeScoreYearInfoList', {}).get('citeScoreYearInfo', []):
                    if str(item.get('@year')) == str(año_pub):
                        resultados_scopus["citescore_historico"] = item.get('citeScore', 'No disponible')
                        break
            elif res_revista.status_code == 401:
                resultados_scopus["permisos_revista"] = False
                        
        return resultados_scopus, 200
    except Exception:
        return None, "Error_Conexion"

# --- INTERFAZ ---
st.title("Evaluador de Investigación Profesional 🔬")
doi_input = st.text_input("Introduce el DOI:")

if st.button("Buscar Métricas"):
    if doi_input:
        doi_limpio = doi_input.replace("https://doi.org/", "").strip()
        
        # OpenAlex
        c_oa, f_oa = obtener_datos_openalex(doi_limpio)
        st.success(f"**OpenAlex:** {c_oa} citas | FWCI: {f_oa}")
        
        # Dimensions
        c_dim, f_dim = obtener_datos_dimensions(doi_limpio)
        st.info(f"**Dimensions:** {c_dim} citas | FCR: {f_dim}")
        
        # Scopus
        with st.spinner('Consultando Scopus...'):
            d_sco, s_sco = obtener_datos_scopus(doi_limpio)
            if s_sco == 200:
                st.success(f"**Scopus:** {d_sco['citas']} citas | FWCI: {d_sco['fwci']} | Año: {d_sco['año']}")
                if d_sco["permisos_revista"]:
                    col1, col2 = st.columns(2)
                    col1.metric(f"SJR ({d_sco['año']})", d_sco['sjr_historico'])
                    col2.metric(f"CiteScore ({d_sco['año']})", d_sco['citescore_historico'])
                else:
                    st.warning("🔒 Sin permiso para métricas de revista (Error 401).")
            else:
                st.error(f"Error Scopus: {s_sco}")

        # Altmetric
        s_alt, d_alt, st_alt = obtener_datos_altmetric(doi_limpio)
        if s_alt:
            st.warning(f"**Altmetric:** Score {s_alt}")
            
        st.write("---")
        st.link_button("🔗 Abrir página original", f"https://doi.org/{doi_limpio}")
