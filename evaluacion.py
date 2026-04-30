# Importamos las librerías necesarias
import streamlit as st  # Para crear la interfaz web
import requests         # Para hacer peticiones a las APIs de internet

# --- DOCUMENTACIÓN DE FUNCIONES ---

def obtener_datos_openalex(doi):
    """
    Esta función se conecta a la API de OpenAlex.
    Toma un DOI como parámetro, hace la consulta y devuelve las citas y el FWCI.
    """
    url = f"https://api.openalex.org/works/doi:{doi}"
    respuesta = requests.get(url)
    
    # Si la petición es exitosa (código 200)
    if respuesta.status_code == 200:
        datos = respuesta.json()
        # Extraemos los datos. Si no existen, mostramos 'No disponible'
        citas = datos.get('cited_by_count', 'No disponible')
        fwci = datos.get('fwci', 'No disponible')
        return citas, fwci
    
    # Si falla, devolvemos valores vacíos
    return None, None

def obtener_datos_dimensions(doi):
    """
    Esta función se conecta a la API de Dimensions.
    Toma un DOI como parámetro, hace la consulta y devuelve las citas y el FCR.
    """
    url = f"https://metrics-api.dimensions.ai/doi/{doi}"
    respuesta = requests.get(url)
    
    if respuesta.status_code == 200:
        datos = respuesta.json()
        citas = datos.get('times_cited', 'No disponible')
        fcr = datos.get('field_citation_ratio', 'No disponible')
        return citas, fcr
        
    return None, None

# --- INTERFAZ DE USUARIO (STREAMLIT) ---

# Título y descripción de la aplicación
st.title("Evaluador de Investigación por DOI 🔬")
st.write("Introduce el DOI de un artículo para extraer la información de impacto desde OpenAlex y Dimensions.")

# Cajón de búsqueda para que el usuario escriba
doi_input = st.text_input("Introduce el DOI (ejemplo: 10.1038/s41586-020-2649-2):")

# Botón que desencadena la acción
if st.button("Buscar"):
    # Comprobamos que el usuario haya escrito algo
    if doi_input:
        # Limpiamos el texto por si el usuario pega la URL completa en lugar de solo el DOI
        doi_limpio = doi_input.replace("https://doi.org/", "").strip()
        
        st.subheader("Resultados:")
        
        # 1. Buscamos en OpenAlex
        citas_oa, fwci_oa = obtener_datos_openalex(doi_limpio)
        if citas_oa is not None:
            # st.success muestra un recuadro verde
            st.success(f"Para OpenAlex: La aportación tiene {citas_oa} citas y un índice FWCI de {fwci_oa}")
        else:
            # st.error muestra un recuadro rojo si hay un fallo
            st.error("No se pudo encontrar información en OpenAlex para este DOI.")
            
        # 2. Buscamos en Dimensions
        citas_dim, fcr_dim = obtener_datos_dimensions(doi_limpio)
        if citas_dim is not None:
            # st.info muestra un recuadro azul
            st.info(f"Para Dimensions: La aportación tiene {citas_dim} citas y un índice FCR de {fcr_dim}")
        else:
            st.error("No se pudo encontrar información en Dimensions para este DOI.")
    else:
        # Advertencia si se pulsa buscar con el cajón vacío
        st.warning("Por favor, introduce un DOI en el cajón de búsqueda.")