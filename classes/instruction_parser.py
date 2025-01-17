import json
import logging

logger = logging.getLogger(__name__)
class InstructionParser:
    def __init__(self, filepath: str):
        """
        Initialize the InstructionParser with the path to the JSON file.
        """
        self.filepath = filepath

    def load_instruction(self) -> str:
        """
        Load instruction text from a JSON file and format it into a single string.
        """
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Construct the instruction string
            instruction = data["instruction"]["general"] + "\n\n"
            instruction += "Resúmenes de Documentos:\n" + "\n".join(
                f"- {doc}" for doc in data["instruction"]["document_summaries"]
            ) + "\n\n"
            instruction += "Cómo Responder:\n" + "\n".join(
                f"- {guideline}" for guideline in data["instruction"]["response_guidelines"]
            ) + "\n\n"
            instruction += f"Priorización:\n{data['instruction']['prioritization']}\n\n"
            instruction += "Ejemplos de Citas:\n" + "\n".join(
                f"- {example}" for example in data["instruction"]["examples"]
            ) + "\n\n"
            instruction += data["instruction"]["fallback"]

            return instruction
        except FileNotFoundError:
            logger.error(f"Instruction file {self.filepath} not found.")
            raise
        except KeyError as e:
            logger.error(f"Missing key in instruction file: {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading instruction file: {e}")
            raise