import pandas as pd
import json


def excel_to_json(file_path, sheet_name='Hoja1'):
    # Cargar el archivo Excel
    df = pd.read_excel(file_path, sheet_name=sheet_name)

    # Normalizar los nombres de las columnas eliminando espacios
    df.columns = df.columns.str.strip()

    # Llenar valores NaN hacia adelante para mantener la jerarquía
    df.fillna(method='ffill', inplace=True)

    # Crear estructura jerárquica
    result = {}
    for servicio, group in df.groupby('servicio'):
        result[servicio] = {}
        for monitoreable, sub_group in group.groupby('Monitoreable'):
            # Convertir las columnas seleccionadas a diccionario
            if {'Variable', 'idVariable'}.issubset(sub_group.columns):
                result[servicio][monitoreable] = sub_group[['Variable', 'idVariable']].to_dict(orient='records')
            else:
                raise KeyError("Las columnas 'Variable' o 'idVariable' no están presentes en los datos.")

    # Convertir el resultado a JSON
    return json.dumps(result, indent=4, ensure_ascii=False)

# Usar la función para el archivo cargado
file_path = 'Heidi.xlsx'
json_result = excel_to_json(file_path)

# Guardar el resultado en un archivo JSON
output_path = 'Heidi.json'
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(json_result)

output_path