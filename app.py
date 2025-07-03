import falcon
from falcon import Request, Response
import requests
import os
import logging
import html

# Set up error logging
logging.basicConfig(
    filename='error.log',
    level=logging.ERROR,
    format='%(asctime)s %(levelname)s %(message)s'
)

MAX_FILE_SIZE = 819200  # 800 kB
MISSING_TIMEZONES_FILE = os.path.join(os.path.dirname(__file__), 'missing_timezones.txt')

INSTRUCTIONS_HTML = """
<!DOCTYPE html>
<html lang='en'>
<head>
  <meta charset='UTF-8'>
  <meta name='viewport' content='width=device-width, initial-scale=1.0'>
  <title>ICS Timezone Fixer</title>
  <link href='https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css' rel='stylesheet'>
  <style>
    body { background: #f7f9fa; }
    .container { max-width: 650px; margin: 40px auto; background: #fff; border-radius: 12px; box-shadow: 0 2px 12px rgba(0,0,0,0.07); padding: 32px 28px; }
    .example { background: #f0f6ff; border-left: 4px solid #0d6efd; padding: 12px 16px; margin: 16px 0; border-radius: 6px; }
    .footer { margin-top: 32px; color: #888; font-size: 0.95em; text-align: center; }
    @media (max-width: 700px) { .container { padding: 16px 6px; } }
  </style>
</head>
<body>
  <div class='container'>
    <h1 class='mb-3 text-primary'>ICS Timezone Fixer</h1>
    <p class='lead'>Welcome! This free tool helps you fix timezone issues in <b>.ics calendar files</b> (such as those from Outlook or Office365) so that Google Calendar and other apps display your event times correctly.</p>
    <h2 class='h5 mt-4'>How to use:</h2>
    <ol>
      <li>Find the <b>public URL</b> to your <code>.ics</code> calendar file (it must start with <code>https://</code>).</li>
      <li>Paste it as a query parameter named <code>ics_url</code> in this app's address bar.</li>
      <li>Example usage:</li>
    </ol>
    <div class='example'>
      <b>Example:</b><br>
      <code>https://your-server.com/?ics_url=https://original-calendar-url.ics</code>
    </div>
    <ol start='4'>
      <li>Use the new link as a replacement for the original one in your calendar app.</li>
    </ol>
    <div class='alert alert-warning mt-4' role='alert'>
      <b>Note:</b> This tool does not store or log your calendar data. All processing happens live, and your data is never saved.<br>
      If you need reliable access, you can <b>download and run this app on your own server</b> using the open-source code.
    </div>
    <div class='footer'>
      &copy; 2025 ICS Timezone Fixer &mdash; Made with <span style='color:#e25555'>&#9829;</span> for calendar sanity.
    </div>
  </div>
</body>
</html>
"""

ERROR_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang='en'>
<head>
  <meta charset='UTF-8'>
  <meta name='viewport' content='width=device-width, initial-scale=1.0'>
  <title>Error - ICS Timezone Fixer</title>
  <link href='https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css' rel='stylesheet'>
  <style>
    body { background: #f7f9fa; }
    .container { max-width: 600px; margin: 40px auto; background: #fff; border-radius: 12px; box-shadow: 0 2px 12px rgba(0,0,0,0.07); padding: 32px 28px; }
    .footer { margin-top: 32px; color: #888; font-size: 0.95em; text-align: center; }
  </style>
</head>
<body>
  <div class='container'>
    <div class='alert alert-danger mt-4' role='alert'>
      <h4 class='alert-heading'>Oops! Something went wrong.</h4>
      <p>{{error_message}}</p>
      <hr>
      <p class='mb-0'>Please check your link and try again. If the problem persists, the remote calendar server may be unavailable or the link may be invalid.</p>
    </div>
    <div class='footer'>
      &copy; 2025 ICS Timezone Fixer
    </div>
  </div>
</body>
</html>
"""

def validate_url(url):
    from urllib.parse import urlparse
    parsed = urlparse(url)
    if not (parsed.scheme and parsed.netloc):
        raise ValueError('Invalid URL.')
    if parsed.scheme.lower() != 'https':
        raise ValueError('Only HTTPS URLs are allowed.')


def validate_file_content(url):
    try:
        r = requests.get(url, stream=True, timeout=15, headers={'Range': 'bytes=0-1023'})
        r.raise_for_status()
        partial_content = next(r.iter_content(1024))
        if b'BEGIN:VCALENDAR' not in partial_content:
            raise ValueError('The file does not appear to be a valid ICS file (BEGIN:VCALENDAR not found).')
    except Exception as e:
        raise ValueError(f'Failed to read file content: {e}')


def fetch_ics_content(url, max_file_size):
    try:
        r = requests.get(url, stream=True, timeout=30)
        r.raise_for_status()
        ics_content = b''
        for chunk in r.iter_content(4096):
            ics_content += chunk
            if len(ics_content) > max_file_size:
                raise ValueError('The ICS file exceeds the maximum allowed size of 800 kB.')
        return ics_content.decode('utf-8', errors='replace')
    except Exception as e:
        raise ValueError(f'Unable to fetch the ICS file: {e}')


def read_missing_timezones(filename):
    if not os.path.exists(filename):
        raise FileNotFoundError('Missing timezones file not found.')
    with open(filename, 'r', encoding='utf-8') as f:
        return f.read()


def insert_missing_timezones(ics_content, missing_timezones):
    pos = ics_content.find('BEGIN:VEVENT')
    if pos == -1:
        raise ValueError('Invalid ICS file format.')
    return ics_content[:pos] + missing_timezones + '\n' + ics_content[pos:]


class IcsTimezoneFixerResource:
    def on_get(self, req: Request, resp: Response):
        ics_url = req.get_param('ics_url')
        if not ics_url:
            resp.status = falcon.HTTP_200
            resp.content_type = 'text/html; charset=utf-8'
            resp.text = INSTRUCTIONS_HTML
            resp.set_header('Access-Control-Allow-Origin', '*')
            return
        try:
            validate_url(ics_url)
            validate_file_content(ics_url)
            ics_content = fetch_ics_content(ics_url, MAX_FILE_SIZE)
            missing_timezones = read_missing_timezones(MISSING_TIMEZONES_FILE)
            modified_ics_content = insert_missing_timezones(ics_content, missing_timezones)
            resp.status = falcon.HTTP_200
            resp.content_type = 'text/calendar; charset=utf-8'
            resp.set_header('Content-Disposition', 'attachment; filename="modified_calendar.ics"')
            resp.text = modified_ics_content
            resp.set_header('Access-Control-Allow-Origin', '*')
        except Exception as e:
            logging.error(f'Error processing request for URL {ics_url}: {e}', exc_info=True)
            # Check Accept header for HTML preference
            accept = req.accept or ''
            if 'text/html' in accept or '*/*' in accept:
                error_html = ERROR_HTML_TEMPLATE.replace('{{error_message}}', html.escape(str(e)))
                resp.status = falcon.HTTP_400
                resp.content_type = 'text/html; charset=utf-8'
                resp.text = error_html
            else:
                resp.status = falcon.HTTP_400
                resp.text = f'Error: {e}'
            resp.set_header('Access-Control-Allow-Origin', '*')

    def on_options(self, req: Request, resp: Response):
        resp.status = falcon.HTTP_200
        resp.set_header('Access-Control-Allow-Origin', '*')
        resp.set_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        resp.set_header('Access-Control-Allow-Headers', 'Content-Type')
        resp.set_header('Access-Control-Max-Age', '86400')


app = falcon.App()
app.add_route('/', IcsTimezoneFixerResource())

if __name__ == '__main__':
    from wsgiref import simple_server
    with simple_server.make_server('127.0.0.1', 8000, app) as httpd:
        print('Serving on http://127.0.0.1:8000')
        httpd.serve_forever() 