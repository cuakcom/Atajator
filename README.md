# Atajator

Sugiere atajos de teclado en tiempo real cada vez que haces clic con el ratón.

## Uso

```
python atajator.py
```

O compila el ejecutable portable:

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
3. Consulta la base de datos de atajos (`shortcuts/*.json`)
4. Muestra un overlay no intrusivo con el atajo disponible

## Aplicaciones con atajos incluidos

| Archivo              | Aplicación               |
|----------------------|--------------------------|
| chrome.json          | Google Chrome            |
| edge.json            | Microsoft Edge           |
| firefox.json         | Mozilla Firefox          |
| excel.json           | Microsoft Excel          |
| word.json            | Microsoft Word           |
| outlook.json         | Microsoft Outlook        |
| vscode.json          | Visual Studio Code       |
| notepad.json         | Bloc de Notas            |
| explorer.json        | Explorador de Windows    |

## Añadir atajos propios

Crea un archivo `shortcuts/<proceso>.json` siguiendo esta estructura:

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

El nombre del archivo debe coincidir con el proceso de Windows (ej: `miapp.exe` → `miapp.json`).
Para añadir el mapeo proceso→archivo edita `PROCESS_MAP` en `shortcut_matcher.py`.

## Dependencias

Ninguna. Solo Python stdlib:
- `ctypes` — Win32 API (hooks, detección de app, tray)
- `tkinter` — Overlay de notificación (incluido en Python)
