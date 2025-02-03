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
        Procesa el texto para buscar fragmentos entre ** ** (posibles referencias),
        localiza el archivo correspondiente y añade [i] como cita en el texto.
        Finalmente, añade al final el bloque de "Referencias:" con enlaces.
        """
        doc_regex = re.compile(r'\*\*([^*]+)\*\*')
        matches = doc_regex.findall(text)

        if not matches:
            # Sin referencias encontradas, devolvemos el texto tal cual
            return text

        # Mapeo de (referencia original) -> índice de cita y detalles
        ref_map = {}
        ref_details = {}
        current_index = 1

        # 1) Construimos la tabla de referencias únicas y sus índices
        for ref_str in matches:
            # Evitar procesar la misma referencia más de una vez
            if ref_str in ref_map:
                continue

            matched_filename = self.find_closest_filename(ref_str)
            if matched_filename:
                ref_map[ref_str] = current_index
                ref_details[current_index] = {
                    "ref_str": ref_str,
                    "matched_filename": matched_filename
                }
                current_index += 1

        # 2) Definimos una función callback que se usará con re.sub
        def replacer(match_obj):
            ref_str_found = match_obj.group(1)  # Lo que está entre ** **
            if ref_str_found in ref_map:
                i = ref_map[ref_str_found]
                # Añadimos la marca de cita [i]
                return f"**{ref_str_found}** <span class=\"doc-citation-number\">[{i}]</span>"
            else:
                # Si no está en ref_map, devolvemos el texto original sin cambios
                return match_obj.group(0)

        # 3) Usamos re.sub con nuestro callback para reemplazar todas las referencias
        text = doc_regex.sub(replacer, text)

        # 4) Construimos el bloque de referencias al final del texto
        if ref_details:
            references_block = "\n\n<b>Referencias:</b>\n"
            for i in sorted(ref_details.keys()):
                info = ref_details[i]
                matched = info["matched_filename"]
                if matched:
                    link = f"/static/docs/{self.encode_filename_for_url(matched)}"
                    references_block += (f"<li>[{i}] <a href=\"{link}\" target=\"_blank\">{matched}</a></li>")
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
