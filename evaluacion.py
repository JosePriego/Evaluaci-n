# Importamos las librerías necesarias
import streamlit as st  
import requests
from bs4 import BeautifulSoup # NUEVA LIBRERÍA: Para leer el código HTML de las páginas web

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
                "Wikipedia": datos.get('cited_by_wikipedia_count', 0)
            }
            return score, desglose, respuesta.status_code
        return None, None, respuesta.status_code
    except Exception:
        return None, None, "Error_Conexion"

def explorar_pagina_revista(doi):
    """
    Sigue un DOI hasta su página web final y extrae el título usando Web Scraping.
    """
    url_base = f"https://doi.org/{doi}"
    cabeceras = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0"
    }
    
    try:
        # allow_redirects=True permite seguir el salto desde doi.org hasta la revista final
        respuesta = requests.get(url_base, headers=cabeceras, allow_redirects=True, timeout=15)
        url_final = respuesta.url
        
        if respuesta.status_code == 200:
            html_pagina = respuesta.text
            # Convertimos el texto HTML en algo que Python pueda navegar
            sopa = BeautifulSoup(html_pagina, "html.parser")
            # Extraemos la etiqueta <title> de la web
            titulo_web = sopa.title.string if sopa.title else "Título no encontrado en el HTML"
            
            return url_final, titulo_web, 200
        else:
            return url_final, None, respuesta.status_code
            
    except Exception as e:
        return None, None, "Error_Conexion"


# --- INTERFAZ DE USUARIO (STREAMLIT) ---

st.title("Evaluador de Investigación por DOI 🔬")
st.write("Introduce el DOI de un artículo para extraer su impacto académico, social y explorar la fuente web.")

doi_input = st.text_input("Introduce el DOI (ejemplo: 10.1038/s41586-020-2649-2):")

# Opciones avanzadas para el usuario
st.write("---")
st.write("**Opciones de análisis avanzado:**")
usar_altmetric = st.checkbox("Intentar obtener datos de impacto social (Altmetric)")
usar_scraping = st.checkbox("Intentar rastrear la página web de la revista (Web Scraping)")
st.write("---")

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
        if usar_altmetric:
            score_alt, desglose_alt, status_alt = obtener_datos_altmetric(doi_limpio)
            if score_alt is not None:
                st.warning(f"Para Altmetric: La aportación tiene un Altmetric Attention Score de {score_alt}")
            else:
                if status_alt == 403:
                    st.warning("⚠️ Limitación de la nube: Altmetric bloqueó la consulta de impacto social por seguridad.")
                else:
                    st.error(f"Error al conectar con Altmetric (Código: {status_alt})")
                    
        # 4. Exploración Web (Web Scraping)
        if usar_scraping:
            st.write("### Explorador de Revista")
            with st.spinner('Rastreando el enlace hacia la revista...'):
                url_destino, titulo_web, status_scraping = explorar_pagina_revista(doi_limpio)
                
                if status_scraping == 200:
                    st.success("¡Conexión exitosa con la web de la revista!")
                    st.write(f"**URL detectada:** [{url_destino}]({url_destino})")
                    st.write(f"**Título de la web (Extraído del HTML):** {titulo_web}")
                    st.info("💡 Nota de desarrollo: Para extraer el número de visualizaciones o descargas, necesitaríamos inspeccionar el código HTML específico de esta URL y programar una regla de búsqueda a medida usando BeautifulSoup.")
                elif status_scraping == 403:
                    st.warning(f"⚠️ La revista bloqueó nuestro escáner en la nube por seguridad (Error 403). URL final: {url_destino}")
                elif status_scraping == "Error_Conexion":
                    st.error("Ocurrió un error al intentar seguir el enlace del DOI.")
                else:
                    st.error(f"El servidor de la revista devolvió el código HTTP {status_scraping}")
            
    else:
        st.warning("Por favor, introduce un DOI en el cajón de búsqueda.")
