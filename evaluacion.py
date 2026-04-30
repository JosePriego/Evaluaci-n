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
    cabeceras = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
        "Accept": "application/json"
    }
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
    """
    Función avanzada: Hace 2 llamadas a Elsevier.
    1. Busca el artículo (Citas, Año, ISSN).
    2. Busca la revista (SJR y CiteScore históricos).
    """
    # 1. Comprobamos que la clave secreta exista
    try:
        api_key = st.secrets["SCOPUS_API_KEY"]
    except KeyError:
        return None, "Falta_Clave"

    cabeceras = {
        "X-ELS-APIKey": api_key,
        "Accept": "application/json"
    }
    
    # ---------------- PASO 1: Buscar el Artículo ----------------
    url_articulo = f"https://api.elsevier.com/content/search/scopus?query=DOI({doi})"
    try:
        res_articulo = requests.get(url_articulo, headers=cabeceras, timeout=10)
        if res_articulo.status_code != 200:
            return None, res_articulo.status_code
            
        datos_articulo = res_articulo.json()
        entradas = datos_articulo.get('search-results', {}).get('entry', [])
        
        if not entradas:
            return None, 404 # No encontrado en Scopus
            
        articulo = entradas[0]
        citas = articulo.get('citedby-count', 'No disponible')
        
        # Extraemos fecha y limpiamos para quedarnos con el año
        fecha_completa = articulo.get('prism:coverDate', '')
        año_pub = fecha_completa.split('-')[0] if fecha_completa else None
        
        # Scopus guarda el ISSN o eISSN
        issn = articulo.get('prism:issn') or articulo.get('prism:eIssn')
        
        # Diccionario para guardar todo nuestro botín
        resultados_scopus = {
            "citas": citas,
            "año": año_pub,
            "issn": issn,
            "sjr_historico": "No disponible",
            "citescore_historico": "No disponible"
        }
        
        # ---------------- PASO 2: Buscar Métricas de la Revista ----------------
        # Solo lo intentamos si Scopus nos dio un ISSN y un Año
        if issn and año_pub:
            url_revista = f"https://api.elsevier.com/content/serial/title/issn/{issn}"
            res_revista = requests.get(url_revista, headers=cabeceras, timeout=10)
            
            if res_revista.status_code == 200:
                datos_revista = res_revista.json()
                entrada_revista = datos_revista.get('serial-metadata-response', {}).get('entry', [{}])[0]
                
                # Buscamos el SJR de ese año exacto
                sjr_lista = entrada_revista.get('SJRList', {}).get('SJR', [])
                for item in sjr_lista:
                    if item.get('@year') == año_pub:
                        resultados_scopus["sjr_historico"] = item.get('$', 'No disponible')
                        break
                        
                # Buscamos el CiteScore de ese año exacto
                cs_lista = entrada_revista.get('citeScoreYearInfoList', {}).get('citeScoreYearInfo', [])
                for item in cs_lista:
                    if item.get('@year') == año_pub:
                        resultados_scopus["citescore_historico"] = item.get('citeScore', 'No disponible')
                        break
                        
        return resultados_scopus, 200
        
    except Exception as e:
        return None, "Error_Conexion"


# --- INTERFAZ DE USUARIO (STREAMLIT) ---

st.title("Evaluador de Investigación Profesional 🔬")
st.write("Introduce un DOI para extraer métricas de OpenAlex, Dimensions, Altmetric y Scopus.")

doi_input = st.text_input("Introduce el DOI (ejemplo: 10.1038/s41586-020-2649-2):")

# Opciones para el usuario
st.write("---")
st.write("**Opciones de análisis:**")
usar_altmetric = st.checkbox("Buscar impacto social (Altmetric)", value=True)
usar_scopus = st.checkbox("Búsqueda Premium en Scopus (Requiere API Key)", value=True)
st.write("---")

if st.button("Buscar Métricas"):
    if doi_input:
        doi_limpio = doi_input.replace("https://doi.org/", "").strip()
        
        st.subheader("Resultados:")
        
        # 1. Búsqueda en OpenAlex
        citas_oa, fwci_oa = obtener_datos_openalex(doi_limpio)
        if citas_oa is not None:
            st.success(f"**OpenAlex:** {citas_oa} citas | FWCI: {fwci_oa}")
        else:
            st.error("OpenAlex: No se pudo encontrar información.")
            
        # 2. Búsqueda en Dimensions
        citas_dim, fcr_dim = obtener_datos_dimensions(doi_limpio)
        if citas_dim is not None:
            st.info(f"**Dimensions:** {citas_dim} citas | FCR: {fcr_dim}")
        else:
            st.error("Dimensions: No se pudo encontrar información.")
            
        # 3. Búsqueda en Scopus (¡NUEVO!)
        if usar_scopus:
            with st.spinner('Consultando las bases de datos de Elsevier...'):
                datos_scopus, status_scopus = obtener_datos_scopus(doi_limpio)
                
                if status_scopus == 200 and datos_scopus:
                    # Usamos un color distinto (verde oscuro o violeta a través de CSS o st.success)
                    st.success(f"**Scopus (Artículo):** {datos_scopus['citas']} citas | Año de pub: {datos_scopus['año']} | ISSN: {datos_scopus['issn']}")
                    
                    # Desglose de la revista
                    col1, col2 = st.columns(2)
                    col1.metric(f"SJR ({datos_scopus['año']})", datos_scopus['sjr_historico'])
                    col2.metric(f"CiteScore ({datos_scopus['año']})", datos_scopus['citescore_historico'])
                    
                    st.caption("Nota: El FWCI es una métrica exclusiva de SciVal. Los cuartiles (Q1-Q4) se derivan del rango del SJR/CiteScore.")
                
                elif status_scopus == "Falta_Clave":
                    st.error("⚠️ Error de seguridad: No se ha encontrado la clave de Scopus. Asegúrate de haberla añadido a los Secretos de Streamlit.")
                elif status_scopus == 401:
                    st.error("⚠️ Scopus rechazó la clave (Error 401). Verifica que la API Key es correcta.")
                elif status_scopus == 404:
                    st.warning("Scopus: El DOI proporcionado no está indexado en su base de datos.")
                else:
                    st.error(f"Error al conectar con Scopus. Código: {status_scopus}")

        # 4. Búsqueda en Altmetric
        if usar_altmetric:
            score_alt, desglose_alt, status_alt = obtener_datos_altmetric(doi_limpio)
            if score_alt is not None:
                st.warning(f"**Altmetric:** Attention Score global de {score_alt}")
                col1, col2, col3 = st.columns(3)
                col1.metric("X (Twitter)", desglose_alt["X (Twitter)"])
                col2.metric("Noticias", desglose_alt["Noticias"])
                col3.metric("Wikipedia", desglose_alt["Wikipedia"])
            else:
                if status_alt == 403:
                    st.warning("⚠️ Altmetric bloqueó la consulta desde la nube.")
                else:
                    st.error(f"Error Altmetric (Código: {status_alt})")
                    
        # 5. Enlace directo a la Revista
        st.write("---")
        st.write("### Consulta de Revista (Visualizaciones/Descargas)")
        url_oficial = f"https://doi.org/{doi_limpio}"
        st.link_button("🔗 Abrir web original del artículo", url_oficial)
            
    else:
        st.warning("Por favor, introduce un DOI válido.")
