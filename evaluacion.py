import streamlit as st  
import requests

# --- FUNCIONES DE EXTRACCIÓN ---

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

def obtener_datos_scopus(doi):
    try:
        api_key = st.secrets["SCOPUS_API_KEY"]
    except:
        return None, "Falta_Clave"

    headers = {"X-ELS-APIKey": api_key, "Accept": "application/json"}
    
    # 1. Búsqueda estándar (la más compatible)
    # Limpiamos el DOI de espacios o prefijos raros
    doi_clean = doi.strip()
    url_search = f"https://api.elsevier.com/content/search/scopus?query=DOI({doi_clean})"
    
    try:
        res_search = requests.get(url_search, headers=headers, timeout=15)
        data = res_search.json()
        
        # Guardamos para el inspector pase lo que pase
        json_debug = data
        
        entradas = data.get('search-results', {}).get('entry', [])
        
        # Si no hay resultados o la entrada es un error
        if not entradas or "error" in entradas[0]:
            return {"json_crudo": json_debug}, 404
        
        articulo = entradas[0]
        
        # Datos básicos encontrados
        res_final = {
            "citas": articulo.get('citedby-count', 'N/A'),
            "año": articulo.get('prism:coverDate', 'N/A').split('-')[0],
            "issn": articulo.get('prism:issn') or articulo.get('prism:eIssn'),
            "fwci": "N/A", # Por defecto N/A hasta que lo encontremos
            "json_crudo": json_debug
        }

        # 2. INTENTO DE CAZAR EL FWCI (Vía Abstract)
        # Hacemos una segunda petición específica para métricas detalladas
        url_abstract = f"https://api.elsevier.com/content/abstract/doi/{doi_clean}?view=META_METRICS"
        res_abs = requests.get(url_abstract, headers=headers, timeout=10)
        
        if res_abs.status_code == 200:
            data_abs = res_abs.json()
            # Añadimos este JSON al debug para que lo veas todo
            res_final["json_crudo_abstract"] = data_abs
            
            # Intentamos navegar por la estructura del FWCI en esta vista
            try:
                metrics = data_abs.get('abstracts-retrieval-response', {}).get('coredata', {})
                # A veces el FWCI vive en un campo específico aquí
                res_final["fwci"] = data_abs.get('abstracts-retrieval-response', {}).get('impactMetrics', {}).get('fieldWeightedCitationImpact', 'N/A')
            except: pass

        return res_final, 200
    except Exception as e:
        return None, f"Error: {str(e)}"

# --- INTERFAZ ---

st.set_page_config(page_title="Auditoría DOI", layout="wide")
st.title("Evaluador de Investigación Profesional 🔬")

doi_input = st.text_input("Introduce el DOI:", value="10.1126/science.1199644")

if st.button("Ejecutar Auditoría"):
    doi_l = doi_input.replace("https://doi.org/", "").strip()
    
    st.divider()
    
    # Bloque de Datos Abiertos
    c_oa, f_oa = obtener_datos_openalex(doi_l)
    c_di, f_di = obtener_datos_dimensions(doi_l)
    
    col1, col2 = st.columns(2)
    col1.success(f"**OpenAlex**\nCitas: {c_oa} | FWCI: {f_oa}")
    col2.info(f"**Dimensions**\nCitas: {c_di} | FCR: {f_di}")

    # Bloque Scopus
    with st.spinner('Consultando Scopus...'):
        datos, status = obtener_datos_scopus(doi_l)
        
        if status == 200:
            st.success(f"**Scopus:** {datos['citas']} citas | **FWCI: {datos['fwci']}** | Año: {datos['año']}")
            
            with st.expander("🕵️‍♂️ INSPECTOR DE API"):
                st.write("Datos de Búsqueda:")
                st.json(datos.get("json_crudo"))
                if "json_crudo_abstract" in datos:
                    st.write("Datos de Métricas Detalladas:")
                    st.json(datos["json_crudo_abstract"])
        else:
            st.error(f"Scopus no devolvió datos para este DOI (Código {status}).")
            if datos and "json_crudo" in datos:
                with st.expander("Ver error técnico"):
                    st.json(datos["json_crudo"])

    st.divider()
    st.link_button("🔗 Abrir en Scopus.com", f"https://doi.org/{doi_l}")
