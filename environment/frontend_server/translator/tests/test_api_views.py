"""
Tests for External Agent REST API endpoints.

This module tests the API views for external agent integration,
covering the endpoints defined in api_views.py.

Tests use Django's test client and mock the filesystem to avoid
needing actual simulation data.
"""
import json
import os
import tempfile
import shutil
from unittest.mock import patch, MagicMock

from django.test import TestCase, Client, override_settings
from django.urls import reverse


class APIAuthenticationTestCase(TestCase):
    """Tests for API authentication decorator."""
    
    def setUp(self):
        self.client = Client()
    
    @override_settings(REQUIRE_API_AUTH=True, API_KEYS=['test-key-123'])
    def test_missing_api_key_returns_401(self):
        """Request without API key should return 401."""
        response = self.client.get('/api/v1/simulation/status')
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.content)
        self.assertIn('error', data)
        self.assertIn('Missing API key', data['error'])
    
    @override_settings(REQUIRE_API_AUTH=True, API_KEYS=['test-key-123'])
    def test_invalid_api_key_returns_403(self):
        """Request with invalid API key should return 403."""
        response = self.client.get(
            '/api/v1/simulation/status',
            HTTP_X_API_KEY='invalid-key'
        )
        self.assertEqual(response.status_code, 403)
        data = json.loads(response.content)
        self.assertIn('error', data)
        self.assertIn('Invalid API key', data['error'])
    
    @override_settings(REQUIRE_API_AUTH=True, API_KEYS=['test-key-123'])
    def test_valid_api_key_header(self):
        """Request with valid API key header should succeed."""
        response = self.client.get(
            '/api/v1/simulation/status',
            HTTP_X_API_KEY='test-key-123'
        )
        # Should not return auth error (may be 200 or 404 depending on simulation state)
        self.assertNotEqual(response.status_code, 401)
        self.assertNotEqual(response.status_code, 403)
    
    @override_settings(REQUIRE_API_AUTH=True, API_KEYS=['test-key-123'])
    def test_valid_api_key_query_param(self):
        """Request with valid API key query param should succeed."""
        response = self.client.get('/api/v1/simulation/status?api_key=test-key-123')
        # Should not return auth error
        self.assertNotEqual(response.status_code, 401)
        self.assertNotEqual(response.status_code, 403)
    
    @override_settings(REQUIRE_API_AUTH=False)
    def test_auth_disabled(self):
        """When auth is disabled, requests should succeed without key."""
        response = self.client.get('/api/v1/simulation/status')
        # Should not return auth error
        self.assertNotEqual(response.status_code, 401)
        self.assertNotEqual(response.status_code, 403)


class SimulationStatusAPITestCase(TestCase):
    """Tests for /api/v1/simulation/status endpoint."""
    
    def setUp(self):
        self.client = Client()
        # Create temp directory for simulation storage
        self.temp_dir = tempfile.mkdtemp()
        self.storage_dir = os.path.join(self.temp_dir, 'storage')
        self.temp_storage_dir = os.path.join(self.temp_dir, 'temp_storage')
        os.makedirs(self.storage_dir)
        os.makedirs(self.temp_storage_dir)
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
    
    @override_settings(REQUIRE_API_AUTH=False)
    def test_no_active_simulation(self):
        """Test response when no simulation is active."""
        with patch('translator.api_views.check_if_file_exists', return_value=False):
            response = self.client.get('/api/v1/simulation/status')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'inactive')


class ListAgentsAPITestCase(TestCase):
    """Tests for /api/v1/agents endpoint."""
    
    def setUp(self):
        self.client = Client()
    
    @override_settings(REQUIRE_API_AUTH=False)
    def test_no_active_simulation_returns_404(self):
        """Test response when no simulation is active."""
        with patch('translator.api_views.get_current_simulation', return_value=(None, None)):
            response = self.client.get('/api/v1/agents')
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.content)
        self.assertIn('error', data)


class AgentStateAPITestCase(TestCase):
    """Tests for /api/v1/agents/<name>/state endpoint."""
    
    def setUp(self):
        self.client = Client()
    
    @override_settings(REQUIRE_API_AUTH=False)
    def test_no_active_simulation_returns_404(self):
        """Test response when no simulation is active."""
        with patch('translator.api_views.get_current_simulation', return_value=(None, None)):
            response = self.client.get('/api/v1/agents/Isabella_Rodriguez/state')
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.content)
        self.assertIn('error', data)
    
    @override_settings(REQUIRE_API_AUTH=False)
    def test_agent_not_found_returns_404(self):
        """Test response when agent doesn't exist."""
        with patch('translator.api_views.get_current_simulation', return_value=('test-sim', 0)):
            with patch('translator.api_views.validate_persona_name', return_value=None):
                response = self.client.get('/api/v1/agents/NonExistent_Agent/state')
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.content)
        self.assertIn('error', data)


class AgentWhisperAPITestCase(TestCase):
    """Tests for /api/v1/agents/<name>/whisper endpoint."""
    
    def setUp(self):
        self.client = Client()
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @override_settings(REQUIRE_API_AUTH=False)
    def test_post_required(self):
        """Test that GET method is not allowed."""
        response = self.client.get('/api/v1/agents/Isabella_Rodriguez/whisper')
        self.assertEqual(response.status_code, 405)
    
    @override_settings(REQUIRE_API_AUTH=False)
    def test_no_active_simulation_returns_404(self):
        """Test response when no simulation is active."""
        with patch('translator.api_views.get_current_simulation', return_value=(None, None)):
            response = self.client.post(
                '/api/v1/agents/Isabella_Rodriguez/whisper',
                data=json.dumps({'content': 'Test whisper', 'type': 'thought'}),
                content_type='application/json'
            )
        
        self.assertEqual(response.status_code, 404)
    
    @override_settings(REQUIRE_API_AUTH=False)
    def test_invalid_json_returns_400(self):
        """Test response when request body is not valid JSON."""
        with patch('translator.api_views.get_current_simulation', return_value=('test-sim', 0)):
            with patch('translator.api_views.validate_persona_name', return_value='Isabella Rodriguez'):
                response = self.client.post(
                    '/api/v1/agents/Isabella_Rodriguez/whisper',
                    data='not valid json',
                    content_type='application/json'
                )
        
        self.assertEqual(response.status_code, 400)
    
    @override_settings(REQUIRE_API_AUTH=False)
    def test_missing_content_returns_400(self):
        """Test response when content field is missing."""
        with patch('translator.api_views.get_current_simulation', return_value=('test-sim', 0)):
            with patch('translator.api_views.validate_persona_name', return_value='Isabella Rodriguez'):
                response = self.client.post(
                    '/api/v1/agents/Isabella_Rodriguez/whisper',
                    data=json.dumps({'type': 'thought'}),
                    content_type='application/json'
                )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)
        self.assertIn('content', data['error'])


class WorldSnapshotAPITestCase(TestCase):
    """Tests for /api/v1/world/snapshot endpoint."""
    
    def setUp(self):
        self.client = Client()
    
    @override_settings(REQUIRE_API_AUTH=False)
    def test_no_active_simulation_returns_404(self):
        """Test response when no simulation is active."""
        with patch('translator.api_views.get_current_simulation', return_value=(None, None)):
            response = self.client.get('/api/v1/world/snapshot')
        
        self.assertEqual(response.status_code, 404)


class ListSimulationsAPITestCase(TestCase):
    """Tests for /api/v1/simulations endpoint."""
    
    def setUp(self):
        self.client = Client()
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
    
    @override_settings(REQUIRE_API_AUTH=False)
    def test_empty_storage(self):
        """Test response when no simulations exist."""
        with patch('translator.api_views.os.path.exists', return_value=False):
            response = self.client.get('/api/v1/simulations')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['count'], 0)
        self.assertEqual(data['simulations'], [])


class ListScenariosAPITestCase(TestCase):
    """Tests for /api/v1/scenarios endpoint."""
    
    def setUp(self):
        self.client = Client()
    
    @override_settings(REQUIRE_API_AUTH=False)
    def test_scenarios_endpoint(self):
        """Test the scenarios list endpoint."""
        response = self.client.get('/api/v1/scenarios')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('count', data)
        self.assertIn('scenarios', data)


class ListAgentTemplatesAPITestCase(TestCase):
    """Tests for /api/v1/agent-templates endpoint."""
    
    def setUp(self):
        self.client = Client()
    
    @override_settings(REQUIRE_API_AUTH=False)
    def test_agent_templates_endpoint(self):
        """Test the agent templates list endpoint."""
        response = self.client.get('/api/v1/agent-templates')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('count', data)
        self.assertIn('templates', data)


class InputSanitizationTestCase(TestCase):
    """Tests for input sanitization and path validation."""
    
    def test_normalize_input_removes_path_traversal(self):
        """Test that normalize_input removes path traversal attempts."""
        from translator.api_views import normalize_input
        
        # Test path traversal
        self.assertEqual(normalize_input('../../../etc/passwd'), 'etcpasswd')
        self.assertEqual(normalize_input('..\\..\\windows\\system32'), 'windowssystem32')
        
        # Test null bytes
        self.assertEqual(normalize_input('test\x00name'), 'test name')
        
        # Test special characters
        self.assertEqual(normalize_input('test<script>'), 'testscript')
    
    def test_normalize_input_preserves_valid_names(self):
        """Test that normalize_input preserves valid agent names."""
        from translator.api_views import normalize_input
        
        # Test valid names are normalized correctly
        self.assertEqual(normalize_input('Isabella Rodriguez'), 'isabella rodriguez')
        self.assertEqual(normalize_input('Klaus_Mueller'), 'klaus mueller')
        self.assertEqual(normalize_input('Maria-Lopez'), 'maria-lopez')
