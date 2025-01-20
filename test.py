from sqlalchemy import create_engine, text


DATABASE_URL = "postgresql://infectologia_postgresql_user:tvwuOJZVzxf8wiC4cMvHf4aXc1rHvWcW@dpg-cu78983tq21c738e3qjg-a.oregon-postgres.render.com:5432/infectologia_postgresql?sslmode=require"

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