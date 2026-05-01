def exportar_excel(datos, res):
    import pandas as pd
    from datetime import datetime
    import io

    registro = preparar_registro_gs(datos, res)

    df = pd.DataFrame([registro])

    # Guardar en memoria (no en disco)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Registro')

    output.seek(0)

    nombre_archivo = f"MAPA_{datos.get('nombre','Paciente')}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"

    return output, nombre_archivo
