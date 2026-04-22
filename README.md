# Atajator

Sugiere atajos de teclado en tiempo real cada vez que haces clic con el ratón.

## Uso

```
python atajator.py
```

O compila el ejecutable portable (no requiere Python instalado):

```
build.bat
```

## Requisitos

- Python 3.9+ (solo para ejecutar desde fuente)
- Windows 10/11
- Sin permisos de administrador

## Cómo funciona

1. Instala un hook global de ratón (Win32 `WH_MOUSE_LL`) sin permisos admin
2. En cada clic detecta la aplicación activa y el control bajo el cursor
3. Clasifica la región de la ventana (toolbar, menú, contenido, etc.)
4. Consulta la base de datos de atajos (`shortcuts/*.json`)
5. Muestra un overlay no intrusivo con el atajo disponible durante 3 segundos

## Aplicaciones con atajos incluidos

| Archivo           | Aplicación              |
|-------------------|-------------------------|
| chrome.json       | Google Chrome           |
| edge.json         | Microsoft Edge          |
| firefox.json      | Mozilla Firefox         |
| excel.json        | Microsoft Excel         |
| word.json         | Microsoft Word          |
| outlook.json      | Microsoft Outlook       |
| vscode.json       | Visual Studio Code      |
| notepad.json      | Bloc de Notas           |
| explorer.json     | Explorador de Windows   |

## Añadir atajos para otras apps

Crea `shortcuts/<nombre_proceso>.json` con esta estructura:

```json
{
  "name": "Mi Aplicación",
  "shortcuts": [
    {
      "action": "Descripción de la acción",
      "shortcut": "Ctrl+X",
      "keywords": ["texto del botón", "nombre del menú"],
      "class_names": ["NombreClaseWin32"],
      "regions": ["toolbar", "menubar", "content", "statusbar"]
    }
  ]
}
```

Añade el mapeo `proceso.exe → nombre_archivo` en `PROCESS_MAP` dentro de `shortcut_matcher.py`.

## Dependencias

Ninguna. Solo Python stdlib:
- `ctypes` — Win32 API (hooks, detección de app, bandeja del sistema)
- `tkinter` — Overlay de notificación (incluido en Python)
