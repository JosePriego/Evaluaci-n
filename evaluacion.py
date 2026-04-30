# Importamos las librerías necesarias
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
    """
    Se conecta a la API de Altmetric.
    Ahora devuelve dos cosas: el Score global y un diccionario con el desglose.
    """
    url = f"https://api.altmetric.com/v1/doi/{doi}"
    respuesta = requests.get(url)
    
    if respuesta.status_code == 200:
        datos = respuesta.json()
        
        # 1. Extraemos el score global
        score = datos.get('score', 'No disponible')
        if isinstance(score, (int, float)):
            score = round(score)
            
        # 2. NUEVO: Extraemos el desglose exacto
        # Usamos .get(clave, 0) para que si la plataforma no menciona el artículo, devuelva un 0.
        desglose = {
            "X (Twitter)": datos.get('cited_by_tweeters_count', 0),
            "Noticias": datos.get('cited_by_msm_count', 0),
            "Wikipedia": datos.get('cited_by_wikipedia_count', 0),
            "Blogs": datos.get('cited_by_feeds_count', 0),
            "Facebook": datos.get('cited_by_fbwalls_count', 0)
        }
        
        return score, desglose
        
    return None, None

# --- INTERFAZ DE USUARIO (STREAMLIT) ---

st.title("Evaluador de Investigación por DOI 🔬")
st.write("Introduce el DOI de un artículo para extraer su impacto académico y social detallado.")

doi_input = st.text_input("Introduce el DOI (ejemplo: 10.1038/s41586-020-2649-2):")

if st.button("Buscar"):
    if doi_input:
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
            
        # 3. Búsqueda en Altmetric con desglose (¡NUEVO!)
        score_alt, desglose_alt = obtener_datos_altmetric(doi_limpio)
        if score_alt is not None:
            st.warning(f"Para Altmetric: La aportación tiene un Altmetric Attention Score de {score_alt}")
            
            # --- NUEVA VISUALIZACIÓN EN COLUMNAS ---
            st.write("**Desglose de menciones sociales:**")
            
            # Creamos 3 columnas para organizar los datos de forma limpia
            col1, col2, col3 = st.columns(3)
            # st.metric es un componente de Streamlit que muestra números grandes y atractivos
            col1.metric(label="X (Twitter)", value=desglose_alt["X (Twitter)"])
            col2.metric(label="Noticias", value=desglose_alt["Noticias"])
            col3.metric(label="Wikipedia", value=desglose_alt["Wikipedia"])
            
            # Creamos 2 columnas más para la siguiente fila
            col4, col5 = st.columns(2)
            col4.metric(label="Blogs", value=desglose_alt["Blogs"])
            col5.metric(label="Facebook", value=desglose_alt["Facebook"])
            
        else:
            st.error("No se pudo encontrar información de impacto social en Altmetric para este DOI.")
            
    else:
        st.warning("Por favor, introduce un DOI en el cajón de búsqueda.")
