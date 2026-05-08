from flask import Blueprint, request, send_file
from app.database import get_connection
from app.utils.response import success, error
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment
from io import BytesIO
from app.utils.jwt import verificar_token, requiere_admin

bp_excel = Blueprint("productos_excel", __name__)

# ─────────────────────────────────────────
# GET /productos/plantilla/<id_cat> → Descargar plantilla Excel
# ─────────────────────────────────────────
@bp_excel.route("/plantilla/<int:id_cat>", methods=["GET"])
def descargar_plantilla(id_cat):
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()

        # Verificar que la categoría existe
        cur.execute("SELECT id_cat, nombre FROM categorias WHERE id_cat = %s", (id_cat,))
        categoria = cur.fetchone()
        if categoria is None:
            return error(message="La categoría seleccionada no existe", status=404)

        # Traer subcategorías de esa categoría
        cur.execute("""
            SELECT s.id_subcat, s.nombre, s.descripcion, s.unidad
            FROM subcategorias s
            LEFT JOIN categoria_subcategoria cs ON cs.id_subcat = s.id_subcat
            WHERE cs.id_cat = %s
            ORDER BY s.id_subcat ASC
        """, (id_cat,))
        subcategorias = cur.fetchall()

        wb = Workbook()

        # ── Hoja principal: Productos ──
        ws_productos = wb.active
        ws_productos.title = "Productos"

        # Estilo de encabezados
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill("solid", start_color="2F5496")
        header_alignment = Alignment(horizontal="center", vertical="center")

        encabezados = ["folio", "descripcion", "precio", "costo", "subcategorias_ids"]
        for col, encabezado in enumerate(encabezados, start=1):
            cell = ws_productos.cell(row=1, column=col, value=encabezado)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment

        # Fila de ejemplo
        ejemplo_font = Font(italic=True, color="808080")
        ejemplos = [
            "PROD-001",
            "Descripción del producto",
            100.00,
            50.00,
            "1,2,3" if subcategorias else ""
        ]
        for col, valor in enumerate(ejemplos, start=1):
            cell = ws_productos.cell(row=2, column=col, value=valor)
            cell.font = ejemplo_font

        # Ancho de columnas
        ws_productos.column_dimensions["A"].width = 15
        ws_productos.column_dimensions["B"].width = 35
        ws_productos.column_dimensions["C"].width = 12
        ws_productos.column_dimensions["D"].width = 12
        ws_productos.column_dimensions["E"].width = 25

        # Nota informativa
        ws_productos.cell(row=4, column=1, value="NOTAS:").font = Font(bold=True)
        ws_productos.cell(row=5, column=1, value=f"• Todos los productos se registrarán en la categoría: {categoria['nombre']}")
        ws_productos.cell(row=6, column=1, value="• Los campos 'folio' y 'costo' son obligatorios.")
        ws_productos.cell(row=7, column=1, value="• En 'subcategorias_ids' escribe los IDs separados por coma. Ejemplo: 1,3,5")
        ws_productos.cell(row=8, column=1, value="• Consulta la hoja 'Catálogo Subcategorías' para ver los IDs disponibles.")
        ws_productos.cell(row=9, column=1, value="• Borra la fila de ejemplo (fila 2) antes de subir el archivo.")

        for row in range(4, 10):
            ws_productos.cell(row=row, column=1).font = Font(italic=True, color="595959")

        # ── Hoja catálogo: Subcategorías ──
        ws_subcat = wb.create_sheet(title="Catálogo Subcategorías")

        cat_encabezados = ["id_subcat", "nombre", "descripcion", "unidad"]
        for col, encabezado in enumerate(cat_encabezados, start=1):
            cell = ws_subcat.cell(row=1, column=col, value=encabezado)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment

        if subcategorias:
            for row, subcat in enumerate(subcategorias, start=2):
                ws_subcat.cell(row=row, column=1, value=subcat["id_subcat"])
                ws_subcat.cell(row=row, column=2, value=subcat["nombre"])
                ws_subcat.cell(row=row, column=3, value=subcat["descripcion"])
                ws_subcat.cell(row=row, column=4, value=subcat["unidad"])
        else:
            ws_subcat.cell(row=2, column=1, value="No hay subcategorías registradas para esta categoría.")
            ws_subcat.cell(row=2, column=1).font = Font(italic=True, color="808080")

        ws_subcat.column_dimensions["A"].width = 12
        ws_subcat.column_dimensions["B"].width = 25
        ws_subcat.column_dimensions["C"].width = 35
        ws_subcat.column_dimensions["D"].width = 15

        # Guardar en memoria y enviar
        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"plantilla_productos_{categoria['nombre'].replace(' ', '_')}.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        return error(message=str(e), status=500)
    finally:
        if conn:
            cur.close()
            conn.close()


# ─────────────────────────────────────────
# POST /productos/carga-masiva/<id_cat> → Cargar productos desde Excel
# ─────────────────────────────────────────
@bp_excel.route("/carga-masiva/<int:id_cat>", methods=["POST"])
def carga_masiva(id_cat):
    conn = None
    try:
        # Verificar que viene el archivo
        if "archivo" not in request.files:
            return error(message="No se encontró el archivo en la solicitud", status=400)

        archivo = request.files["archivo"]
        if archivo.filename == "":
            return error(message="No se seleccionó ningún archivo", status=400)
        if not archivo.filename.endswith(".xlsx"):
            return error(message="El archivo debe ser de tipo .xlsx", status=400)

        conn = get_connection()
        cur = conn.cursor()

        # Verificar que la categoría existe
        cur.execute("SELECT id_cat, nombre FROM categorias WHERE id_cat = %s", (id_cat,))
        categoria = cur.fetchone()
        if categoria is None:
            return error(message="La categoría seleccionada no existe", status=404)

        # Leer el archivo Excel
        wb = load_workbook(archivo, data_only=True)
        ws = wb.active

        errores = []
        productos_a_crear = []

        # Validar todas las filas antes de insertar cualquier cosa
        for num_fila, fila in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            # Ignorar filas completamente vacías y las filas de notas (columna A empieza con •)
            if not any(fila):
                continue
            if str(fila[0] or "").startswith("•") or str(fila[0] or "").strip() in ["NOTAS:", ""]:
                continue

            folio, descripcion, precio, costo, subcategorias_raw = (list(fila) + [None] * 5)[:5]

            # Validar campos obligatorios
            if not folio:
                errores.append({"fila": num_fila, "motivo": "El campo 'folio' es obligatorio"})
                continue
            if not costo:
                errores.append({"fila": num_fila, "motivo": "El campo 'costo' es obligatorio"})
                continue

            # Verificar folio duplicado en BD
            cur.execute("SELECT folio FROM productos WHERE folio = %s", (str(folio),))
            if cur.fetchone() is not None:
                errores.append({"fila": num_fila, "motivo": f"El folio '{folio}' ya existe en la base de datos"})
                continue

            # Verificar folio duplicado dentro del mismo archivo
            folios_en_archivo = [p["folio"] for p in productos_a_crear]
            if str(folio) in folios_en_archivo:
                errores.append({"fila": num_fila, "motivo": f"El folio '{folio}' está duplicado en el archivo"})
                continue

            # Parsear subcategorías
            subcategorias_ids = []
            if subcategorias_raw:
                try:
                    subcategorias_ids = [int(id.strip()) for id in str(subcategorias_raw).split(",") if id.strip()]
                except ValueError:
                    errores.append({"fila": num_fila, "motivo": "El campo 'subcategorias_ids' contiene valores inválidos, deben ser números separados por coma"})
                    continue

            productos_a_crear.append({
                "folio": str(folio),
                "descripcion": descripcion,
                "precio": precio,
                "costo": costo,
                "subcategorias_ids": subcategorias_ids,
                "fila": num_fila
            })

        # Si hay errores, no crear nada y reportar
        if errores:
            return error(
                message=f"Se encontraron {len(errores)} error(es) en el archivo. No se creó ningún producto.",
                status=400,
                data={"errores": errores}
            )

        if not productos_a_crear:
            return error(message="El archivo no contiene productos para registrar", status=400)

        # Insertar todos los productos
        ids_creados = []
        for producto in productos_a_crear:
            cur.execute("""
                INSERT INTO productos (folio, descripcion, precio, costo)
                VALUES (%s, %s, %s, %s)
                RETURNING id_producto
            """, (
                producto["folio"],
                producto["descripcion"],
                producto["precio"],
                producto["costo"],
            ))
            nuevo_id = cur.fetchone()["id_producto"]

            # Asignar categoría
            cur.execute("""
                INSERT INTO producto_categoria (id_prod, id_cat)
                VALUES (%s, %s)
            """, (nuevo_id, id_cat))

            # Asignar subcategorías
            for id_subcat in producto["subcategorias_ids"]:
                cur.execute("""
                    INSERT INTO producto_subcategoria (id_producto, id_subcat)
                    VALUES (%s, %s)
                """, (nuevo_id, id_subcat))

            ids_creados.append(nuevo_id)

        conn.commit()
        return success(
            data={
                "productos_creados": len(ids_creados),
                "ids": ids_creados
            },
            message=f"Se crearon {len(ids_creados)} producto(s) correctamente",
            status=201
        )

    except Exception as e:
        if conn:
            conn.rollback()
        return error(message=str(e), status=500)
    finally:
        if conn:
            cur.close()
            conn.close()
