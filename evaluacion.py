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
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0",
        "Accept": "application/json"
    }
    try:
        respuesta = requests.get(url, headers=cabeceras, timeout=10)
        if respuesta.status_code == 200:
            datos = respuesta.json()
            score = datos.get('score', 'No disponible')
            if isinstance(score, (int, float)):
                score = round(score)
            desglose = {
                "X (Twitter)": datos.get('cited_by_tweeters_count', 0),
                "Noticias": datos.get('cited_by_msm_count', 0),
                "Wikipedia": datos.get('cited_by_wikipedia_count', 0),
                "Blogs": datos.get('cited_by_feeds_count', 0),
                "Facebook": datos.get('cited_by_fbwalls_count', 0)
            }
            return score, desglose, respuesta.status_code
        return None, None, respuesta.status_code
    except Exception:
        return None, None, "Error_Conexion"


# --- INTERFAZ DE USUARIO (STREAMLIT) ---

st.title("Evaluador de Investigación por DOI 🔬")
st.write("Introduce el DOI de un artículo para extraer su impacto académico y métricas sociales.")

doi_input = st.text_input("Introduce el DOI (ejemplo: 10.1038/s41586-020-2649-2):")

# Opciones para el usuario
usar_altmetric = st.checkbox("Intentar obtener datos de impacto social (Altmetric)")

if st.button("Buscar"):
    if doi_input:
        # Limpieza de datos por seguridad
        doi_limpio = doi_input.replace("https://doi.org/", "").strip()
        
        st.subheader("Resultados:")
        
        # 1. Búsqueda en OpenAlex
        citas_oa, fwci_oa = obtener_datos_openalex(doi_limpio)
        if citas_oa is not None:
            st.success(f"Para OpenAlex: La aportación tiene {citas_oa} citas y un índice FWCI de {fwci_oa}")
        else:
            st.error("No se pudo encontrar información en OpenAlex para este DOI.")
            
        # 2. Búsqueda en Dimensions
        citas_dim, fcr_dim = obtener_datos_dimensions(doi_limpio)
        if citas_dim is not None:
            st.info(f"Para Dimensions: La aportación tiene {citas_dim} citas y un índice FCR de {fcr_dim}")
        else:
            st.error("No se pudo encontrar información en Dimensions para este DOI.")
            
        # 3. Búsqueda en Altmetric
        if usar_altmetric:
            score_alt, desglose_alt, status_alt = obtener_datos_altmetric(doi_limpio)
            if score_alt is not None:
                st.warning(f"Para Altmetric: La aportación tiene un Altmetric Attention Score de {score_alt}")
                
                # Desglose en columnas
                col1, col2, col3 = st.columns(3)
                col1.metric("X (Twitter)", desglose_alt["X (Twitter)"])
                col2.metric("Noticias", desglose_alt["Noticias"])
                col3.metric("Wikipedia", desglose_alt["Wikipedia"])
            else:
                if status_alt == 403:
                    st.warning("⚠️ Limitación de la nube: Altmetric bloqueó la consulta por seguridad.")
                else:
                    st.error(f"Error al conectar con Altmetric (Código: {status_alt})")
                    
        # 4. Enlace directo a la Revista (¡La nueva solución elegante!)
        st.write("---")
        st.write("### Consulta Manual en la Revista")
        st.write("Para ver datos internos como descargas o visualizaciones, visita la página oficial del artículo:")
        
        # st.link_button crea un botón que redirige automáticamente a la URL final usando doi.org
        url_oficial = f"https://doi.org/{doi_limpio}"
        st.link_button("🔗 Abrir página del artículo", url_oficial)
            
    else:
        st.warning("Por favor, introduce un DOI en el cajón de búsqueda.")
