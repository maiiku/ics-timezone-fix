import os
import io
import pytest
import falcon
from falcon import testing
import app as ics_app

class TestIcsTimezoneFixer:
    def setup_method(self):
        self.app = ics_app.app
        self.client = testing.TestClient(self.app)

    def test_instructions_page(self):
        response = self.client.simulate_get('/')
        assert response.status_code == 200
        assert 'ICS Timezone Fixer' in response.text
        assert response.headers['access-control-allow-origin'] == '*'

    def test_invalid_url(self):
        response = self.client.simulate_get('/', params={'ics_url': 'not_a_url'})
        assert response.status_code == 400
        assert 'Invalid URL' in response.text
        assert response.headers['access-control-allow-origin'] == '*'

    def test_non_https_url(self):
        response = self.client.simulate_get('/', params={'ics_url': 'http://example.com/calendar.ics'})
        assert response.status_code == 400
        assert 'Only HTTPS URLs are allowed' in response.text
        assert response.headers['access-control-allow-origin'] == '*'

    def test_invalid_ics_file(self, requests_mock):
        # Mock a valid HTTPS URL but with non-ICS content
        url = 'https://example.com/calendar.ics'
        requests_mock.get(url, content=b'NOT AN ICS FILE', status_code=200)
        response = self.client.simulate_get('/', params={'ics_url': url})
        assert response.status_code == 400
        assert 'BEGIN:VCALENDAR not found' in response.text
        assert response.headers['access-control-allow-origin'] == '*'

    def test_oversized_ics_file(self, requests_mock):
        url = 'https://example.com/big.ics'
        # Simulate a file just over the max size
        big_content = b'BEGIN:VCALENDAR\n' + b'A' * (ics_app.MAX_FILE_SIZE + 1)
        requests_mock.get(url, content=big_content, status_code=200)
        # Patch validate_file_content to pass (since partial content is valid)
        def dummy_validate(url):
            pass
        orig_validate = ics_app.validate_file_content
        ics_app.validate_file_content = dummy_validate
        response = self.client.simulate_get('/', params={'ics_url': url})
        assert response.status_code == 400
        assert 'exceeds the maximum allowed size' in response.text
        assert response.headers['access-control-allow-origin'] == '*'
        ics_app.validate_file_content = orig_validate

    def test_valid_ics_file(self, requests_mock, tmp_path):
        url = 'https://example.com/valid.ics'
        # Minimal valid ICS file
        ics_content = 'BEGIN:VCALENDAR\nEND:VCALENDAR'
        requests_mock.get(url, content=ics_content.encode('utf-8'), status_code=200)
        # Patch missing_timezones to a known value
        tz_content = '\nBEGIN:VTIMEZONE\nTZID:TestZone\nEND:VTIMEZONE\n'
        orig_read = ics_app.read_missing_timezones
        ics_app.read_missing_timezones = lambda fn: tz_content
        # Patch insert_missing_timezones to check insertion
        orig_insert = ics_app.insert_missing_timezones
        def test_insert(ics, tz):
            assert tz in tz_content
            return ics.replace('BEGIN:VCALENDAR', 'BEGIN:VCALENDAR' + tz)
        ics_app.insert_missing_timezones = test_insert
        response = self.client.simulate_get('/', params={'ics_url': url})
        assert response.status_code == 200
        assert 'TestZone' in response.text
        assert response.headers['content-type'].startswith('text/calendar')
        assert response.headers['access-control-allow-origin'] == '*'
        ics_app.read_missing_timezones = orig_read
        ics_app.insert_missing_timezones = orig_insert

    def test_cors_options(self):
        response = self.client.simulate_options('/')
        assert response.status_code == 200
        assert response.headers['access-control-allow-origin'] == '*'
        assert 'GET' in response.headers['access-control-allow-methods']
        assert 'OPTIONS' in response.headers['access-control-allow-methods']
        assert 'Content-Type' in response.headers['access-control-allow-headers']

    @pytest.mark.integration
    def test_real_outlook_calendar_integration(self):
        if os.environ.get('RUN_INTEGRATION_TESTS') != '1':
            pytest.skip('Set RUN_INTEGRATION_TESTS=1 to run real network integration test')
        url = 'https://outlook.office365.com/owa/calendar/36f17034f4af4056b1b19a0d355c525c@holmsecurity.com/f95e73173b294b06ac942d63aec6ce6010163340627182384649/S-1-8-3025012254-364708259-2680903488-3691858234/reachcalendar.ics'
        response = self.client.simulate_get('/', params={'ics_url': url})
        # Expect 200 on success; if 400, surface server-side message to aid diagnosis
        assert response.headers['access-control-allow-origin'] == '*'
        if response.status_code == 200:
            assert response.headers['content-type'].startswith('text/calendar')
            assert 'BEGIN:VCALENDAR' in response.text
        else:
            pytest.fail(f'Integration request failed with {response.status_code}: {response.text[:300]}') 