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
    Se conecta a la API de Altmetric simulando ser un navegador web (Chrome).
    """
    url = f"https://api.altmetric.com/v1/doi/{doi}"
    
    # CAMBIO CLAVE: Disfrazamos nuestra petición como un navegador Chrome en Windows
    cabeceras = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }
    
    # Usamos un bloque try-except por si la conexión falla por completo
    try:
        # Añadimos un 'timeout' para que la app no se quede colgada si Altmetric tarda
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
        
    except Exception as e:
        # Si el servidor rechaza la conexión de tajo, devolvemos un error personalizado
        return None, None, "Error_Conexion"

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
            
        # 3. Búsqueda en Altmetric
        score_alt, desglose_alt, status_alt = obtener_datos_altmetric(doi_limpio)
        
        if score_alt is not None:
            st.warning(f"Para Altmetric: La aportación tiene un Altmetric Attention Score de {score_alt}")
            st.write("**Desglose de menciones sociales:**")
            
            col1, col2, col3 = st.columns(3)
            col1.metric(label="X (Twitter)", value=desglose_alt["X (Twitter)"])
            col2.metric(label="Noticias", value=desglose_alt["Noticias"])
            col3.metric(label="Wikipedia", value=desglose_alt["Wikipedia"])
            
            col4, col5 = st.columns(2)
            col4.metric(label="Blogs", value=desglose_alt["Blogs"])
            col5.metric(label="Facebook", value=desglose_alt["Facebook"])
            
        else:
            # Control de errores mejorado
            if status_alt == 404:
                st.error("Error 404: Altmetric no tiene registrado este DOI en su base de datos pública.")
            elif status_alt == 403:
                st.error("Error 403: Altmetric sigue bloqueando la conexión por seguridad.")
            elif status_alt == 429:
                st.error("Error 429: Hemos superado el límite de peticiones gratuitas. Inténtalo más tarde.")
            elif status_alt == "Error_Conexion":
                st.error("Error de conexión: No se pudo contactar con el servidor de Altmetric.")
            else:
                st.error(f"Error al conectar con Altmetric. Código HTTP: {status_alt}")
            
    else:
        st.warning("Por favor, introduce un DOI en el cajón de búsqueda.")
