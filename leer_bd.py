from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# Crear la conexión al motor de base de datos
engine = create_engine(DATABASE_URL)

# Consultar los datos en la tabla `feedback`
try:
    with engine.connect() as connection:
        # Ejecutar la consulta
        query = text("SELECT * FROM feedback;")
        result = connection.execute(query)

        # Iterar sobre los resultados
        print("Contenido de la tabla feedback:")
        for row in result:
            print(row)

except Exception as e:
    print(f"Error al consultar la tabla feedback: {e}")