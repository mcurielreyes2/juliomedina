# classes/reference_maker.py
import os
import logging
from rapidfuzz import process, fuzz
from urllib.parse import quote
import re

logger = logging.getLogger(__name__)

class ReferenceMaker:
    def __init__(self, docs_directory: str, threshold: int = 80):
        """
        Inicializa el ReferenceMaker.

        Args:
            docs_directory (str): Ruta al directorio que contiene los documentos.
            threshold (int, opcional): Umbral de similitud mínima (porcentaje). Defaults to 80.
        """
        self.docs_directory = docs_directory
        self.threshold = threshold

        if not os.path.exists(self.docs_directory):
            raise ValueError(f"El directorio de documentos no existe: {self.docs_directory}")

        self.docs_list = self.load_documents()

    def load_documents(self):
        """
        Carga dinámicamente la lista de documentos desde el directorio especificado.

        Returns:
            list: Lista de nombres de archivos.
        """
        try:
            files = os.listdir(self.docs_directory)
            # Filtrar solo archivos (puedes ajustar las extensiones si es necesario)
            files = [f for f in files if os.path.isfile(os.path.join(self.docs_directory, f))]
            logger.info(f"Documentos cargados: {files}")
            return files
        except Exception as e:
            logger.error(f"Error al cargar documentos: {e}")
            return []

    def find_closest_filename(self, reference_name: str) -> str:
        """
        Encuentra el nombre de archivo más similar basado en el nombre de referencia.

        Args:
            reference_name (str): El nombre de referencia generado por el sistema.

        Returns:
            str: El nombre exacto del archivo si se encuentra una coincidencia adecuada.
            None: Si no se encuentra ninguna coincidencia por encima del umbral.
        """
        # Normalizar el nombre de referencia
        normalized_ref = self.normalize_reference_name(reference_name)
        logger.info(f"Procesando referencia: {reference_name} (normalizada: {normalized_ref})")

        # Usar rapidfuzz para encontrar la mejor coincidencia
        match, score, _ = process.extractOne(
            normalized_ref,
            self.docs_list,
            scorer=fuzz.ratio  # o fuzz.token_sort_ratio, etc.
        )

        if score >= self.threshold:
            logger.info(f"Coincidencia más cercana encontrada: {match} (similaridad: {score}%)")
            return match
        else:
            logger.warning(f"No se encontró una coincidencia suficientemente similar para '{reference_name}'. Mejor coincidencia: '{match}' con {score}% de similaridad.")
            return None

    def generate_document_link(self, exact_filename: str) -> str:
        """
        Genera un enlace funcional para el archivo dado.

        Args:
            exact_filename (str): El nombre exacto del archivo encontrado en el directorio.

        Returns:
            str: El enlace generado.
        """
        encoded_filename = self.encode_filename_for_url(exact_filename)
        link = f"/static/docs/{encoded_filename}"
        logger.info(f"Enlace generado: {link}")
        return link

    def process_text_references_with_citations(self, text: str) -> str:
        """
        Procesa texto para agregar citas con referencias válidas y un bloque de referencias al final.
        """
        import re

        # Regex para capturar texto entre ** **
        doc_regex = re.compile(r'\*\*([^*]+)\*\*')
        matches = doc_regex.findall(text)

        if not matches:
            return text  # Sin referencias encontradas

        # Mapeo de referencia original a índice y detalles de referencia
        ref_map = {}
        ref_details = {}
        current_index = 1

        for ref_str in matches:
            # Evitar procesar referencias repetidas
            if ref_str in ref_map:
                continue

            # Buscar archivo más cercano
            matched_filename = self.find_closest_filename(ref_str)

            # Solo procesar si hay una coincidencia válida
            if matched_filename:
                ref_map[ref_str] = current_index
                ref_details[current_index] = {
                    "ref_str": ref_str,
                    "matched_filename": matched_filename
                }
                current_index += 1

        # Reemplazo in-place con [i] solo para referencias válidas
        for ref_str in matches:
            if ref_str in ref_map:
                i = ref_map[ref_str]
                if i in ref_details:  # Confirmar que es una referencia válida
                    matched = ref_details[i]["matched_filename"]
                    if matched:
                        new_fragment=f"**{ref_str}** <span class=\"doc-citation-number\">[{i}]</span>"
                        old_fragment = f"**{ref_str}**"
                        text = text.replace(old_fragment, new_fragment)

        # Construir el bloque de referencias
        references_block = "\n\n<b>Referencias:</b>\n"
        for i in sorted(ref_details.keys()):
            info = ref_details[i]
            ref_str = info["ref_str"]
            matched = info["matched_filename"]
            if matched:  # Solo incluir referencias válidas
                link = f"/static/docs/{self.encode_filename_for_url(matched)}"
                references_block += f"[{i}] <a href=\"{link}\" target=\"_blank\">{matched}</a>\n"

        # Agregar bloque de referencias al texto
        text += references_block
        return text

    @staticmethod
    def normalize_reference_name(reference_name: str) -> str:
        """
        Normaliza el nombre de referencia reemplazando codificaciones comunes.

        Args:
            reference_name (str): El nombre de referencia a normalizar.

        Returns:
            str: El nombre de referencia normalizado.
        """
        return reference_name.replace("+", " ").replace("%20", " ").replace("%28", "(").replace("%29", ")")

    @staticmethod
    def encode_filename_for_url(filename: str) -> str:
        """
        Codifica el nombre del archivo para ser seguro en una URL.

        Args:
            filename (str): El nombre del archivo a codificar.

        Returns:
            str: El nombre del archivo codificado.
        """
        return quote(filename)
