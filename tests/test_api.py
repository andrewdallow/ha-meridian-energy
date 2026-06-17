"""Tests for the Meridian Energy API module."""

from unittest.mock import Mock, patch

import pytest

from custom_components.meridian_energy.api import MeridianEnergyApi


@pytest.mark.unit
class TestMeridianEnergyApi:
    """Test suite for MeridianEnergyApi."""

    def test_api_initialization(self):
        """Test API initialization."""
        email = "test@example.com"
        password = "test_password"

        api = MeridianEnergyApi(email, password)

        assert api._email == email
        assert api._password == password
        assert api._url_base == "https://secure.meridianenergy.co.nz/"
        assert api._token is None
        assert api._data is None
        assert api._session is not None

    @patch("custom_components.meridian_energy.api.BeautifulSoup")
    @patch("custom_components.meridian_energy.api.requests.Session")
    def test_token_retrieval_success(self, mock_session_class, mock_soup):
        """Test successful token retrieval."""
        api = MeridianEnergyApi("test@example.com", "password")

        # Mock the session and response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = (
            "<html><input name='authenticity_token' value='test_token'/></html>"
        )

        api._session.get = Mock(return_value=mock_response)

        # Mock BeautifulSoup
        mock_soup_instance = Mock()
        mock_token_input = Mock()
        mock_token_input.__getitem__ = Mock(return_value="test_token")
        mock_soup_instance.find = Mock(return_value=mock_token_input)
        mock_soup.return_value = mock_soup_instance

        # Mock login
        api.login = Mock()

        api.token()

        api._session.get.assert_called_once_with(api._url_base)
        assert api._token == "test_token"
        api.login.assert_called_once()

    @patch("custom_components.meridian_energy.api.requests.Session")
    def test_token_retrieval_failure(self, mock_session_class):
        """Test token retrieval with non-200 status."""
        api = MeridianEnergyApi("test@example.com", "password")

        # Mock failed response
        mock_response = Mock()
        mock_response.status_code = 500
        api._session.get = Mock(return_value=mock_response)

        api.token()

        api._session.get.assert_called_once()
        assert api._token is None

    @patch("custom_components.meridian_energy.api.requests.Session")
    def test_login_success(self, mock_session_class):
        """Test successful login."""
        api = MeridianEnergyApi("test@example.com", "test_password")
        api._token = "test_token"
        api.get_data = Mock(return_value="data")

        mock_response = Mock()
        mock_response.status_code = 200
        api._session.post = Mock(return_value=mock_response)

        result = api.login()

        assert result is True
        api._session.post.assert_called_once()
        api.get_data.assert_called_once()

        # Verify form data
        call_args = api._session.post.call_args
        assert call_args[1]["data"]["email"] == "test@example.com"
        assert call_args[1]["data"]["password"] == "test_password"
        assert call_args[1]["data"]["authenticity_token"] == "test_token"

    @patch("custom_components.meridian_energy.api.requests.Session")
    def test_login_failure(self, mock_session_class):
        """Test failed login."""
        api = MeridianEnergyApi("test@example.com", "wrong_password")
        api._token = "test_token"

        mock_response = Mock()
        mock_response.status_code = 401
        api._session.post = Mock(return_value=mock_response)

        result = api.login()

        assert result is False
        api._session.post.assert_called_once()

    @patch("custom_components.meridian_energy.api.requests.Session")
    def test_get_data_success(self, mock_session_class):
        """Test successful data retrieval."""
        api = MeridianEnergyApi("test@example.com", "password")

        expected_data = "HDR,1,Electricity\nDET,1,50001234"
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = expected_data
        api._session.get = Mock(return_value=mock_response)

        result = api.get_data()

        assert result == expected_data
        api._session.get.assert_called_once()

        # Verify URL construction contains date parameters
        call_url = api._session.get.call_args[0][0]
        assert "date_from=" in call_url
        assert "date_to=" in call_url
        assert "download=true" in call_url

    @patch("custom_components.meridian_energy.api.requests.Session")
    def test_get_data_empty_response(self, mock_session_class):
        """Test data retrieval with empty response."""
        api = MeridianEnergyApi("test@example.com", "password")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = ""
        api._session.get = Mock(return_value=mock_response)

        result = api.get_data()

        assert result is False

    @patch("custom_components.meridian_energy.api.requests.Session")
    def test_get_data_failure(self, mock_session_class):
        """Test data retrieval failure."""
        api = MeridianEnergyApi("test@example.com", "password")

        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "error data"
        api._session.get = Mock(return_value=mock_response)

        result = api.get_data()

        assert result is False

    @patch("custom_components.meridian_energy.api.datetime")
    @patch("custom_components.meridian_energy.api.requests.Session")
    def test_get_data_date_range(self, mock_session_class, mock_datetime):
        """Test get_data constructs correct date range."""
        from datetime import datetime as dt

        api = MeridianEnergyApi("test@example.com", "password")

        # Mock datetime
        test_date = dt(2026, 1, 15)
        mock_datetime.now.return_value = test_date
        mock_datetime.strptime = dt.strptime

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "data"
        api._session.get = Mock(return_value=mock_response)

        api.get_data()

        call_url = api._session.get.call_args[0][0]
        # Should contain today's date and 365 days ago
        assert "15/01/2026" in call_url
