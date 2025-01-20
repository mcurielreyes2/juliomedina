import json
# File: classes/asistente_osma.py

import os
import logging

logger = logging.getLogger(__name__)


class AsistenteOSMA:
    def __init__(self):
        json_path = os.path.join(os.path.dirname(__file__), '..', 'osma_data.json')
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
            logger.info(f"Archivo de OSMA cargado desde: {json_path}")
        except Exception as e:
            logger.error(f"Error al cargar el archivo JSON de OSMA: {e}")
            self.data = {}

        self.state = 0
        self.servicio = None          # Ahora será una lista de servicios seleccionados
        self.monitoreable = None      # Lista de monitoreables seleccionados
        self.variables = None         # Lista de variables seleccionadas
        self.rango_fechas = None
        self.intervalo = None

        self.preguntas = [
            "¿Qué servicio(s) desea seleccionar?",
            "¿Qué monitoreables desea consultar? ",
            "¿Qué variables requiere? ",
            "Indique la fecha y hora de inicio y la fecha y hora de fin (formato: 2025-01-15 08:00, 2025-01-15 17:00):",
            "¿Qué intervalo de consulta requiere? (Minuto, Hora, Día o Mes)"
        ]

    def iniciar_dialogo(self):
        self.state = 0
        self.servicio = None
        self.monitoreable = None
        self.variables = None
        self.rango_fechas = None
        self.intervalo = None
        logger.info("Iniciando diálogo de importación de datos OSMA")
        return self.preguntas[self.state]

    def procesar_respuesta(self, respuesta):
        if self.state == 0:
            selected = [s.strip() for s in respuesta.split(',')]
            valid = [s for s in selected if s in self.data.keys()]
            if not valid:
                return "Ningún servicio válido seleccionado. Por favor, intente de nuevo."
            self.servicio = valid
        elif self.state == 1:
            selected = [s.strip() for s in respuesta.split(',')]
            valid = []
            for mon in selected:
                for serv in self.servicio:
                    if mon in self.data.get(serv, {}).keys():
                        valid.append(mon)
                        break
            if not valid:
                return "Monitoreable no encontrado para los servicios seleccionados. Intente nuevamente."
            self.monitoreable = valid
        elif self.state == 2:
            selected = [s.strip() for s in respuesta.split(',')]
            self.variables = selected
        elif self.state == 3:
            self.rango_fechas = respuesta  # Aquí se podría validar el formato
        elif self.state == 4:
            self.intervalo = respuesta
        self.state += 1

        if self.state < len(self.preguntas):
            return self.preguntas[self.state]
        else:
            return self.finalizar_dialogo()

    def finalizar_dialogo(self):
        resumen = (
            f"Configuración OSMA:\n"
            f"- Servicio(s): {', '.join(self.servicio) if self.servicio else 'Ninguno'}\n"
            f"- Monitoreable(s): {', '.join(self.monitoreable) if self.monitoreable else 'Ninguno'}\n"
            f"- Variables: {', '.join(self.variables) if self.variables else 'Ninguna'}\n"
            f"- Rango de fechas/hora: {self.rango_fechas}\n"
            f"- Intervalo: {self.intervalo}\n"
        )
        logger.info("Diálogo finalizado. " + resumen)
        return resumen
