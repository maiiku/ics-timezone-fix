# ICS Timezone Fix

A lightweight web service to fix timezone issues in `.ics` calendar files (from Outlook, Office365, etc.) so Google Calendar and other apps display event times correctly.

---

## Features
- Accepts a public `.ics` calendar URL and injects missing timezone definitions.
- Ensures compatibility with Google Calendar and other calendar apps.
- Fast, privacy-friendly (no data stored).
- Modern, user-friendly web interface.
- CORS enabled for easy integration.

---

## How to Run Locally

1. **Clone the repository:**
   ```bash
   git clone https://github.com/maiiku/ics-timezone-fix.git
   cd ics-timezone-fix
   ```
2. **Create and activate a virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Run the app:**
   ```bash
   python3 app.py
   ```
5. **Open in your browser:**
   Go to [http://127.0.0.1:8000/](http://127.0.0.1:8000/)

---

## Usage

- **Instructions page:**
  Open the app in your browser with no parameters to see friendly usage instructions.
- **Fix a calendar:**
  Add your `.ics` file URL as a query parameter, e.g.:
  ```
  http://127.0.0.1:8000/?ics_url=https://example.com/calendar.ics
  ```
- The app will return a fixed `.ics` file for download.

---

## Example

```
https://your-server.com/?ics_url=https://original-calendar-url.ics
```

---

## License

This project is licensed under the GNU General Public License v3.0. See [LICENSE](LICENSE) for details. 