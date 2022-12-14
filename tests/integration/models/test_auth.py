"""Test praw.models.auth."""
import pytest
from prawcore import InvalidToken

from praw import Reddit

from .. import IntegrationTest


class TestAuthScript(IntegrationTest):
    def test_scopes(self):
        with self.use_cassette():
            assert self.reddit.read_only is True
            assert self.reddit.auth.scopes() == {"*"}


class TestAuthWeb(IntegrationTest):
    def setup_reddit(self):
        self.reddit = Reddit(
            client_id=pytest.placeholders.client_id,
            client_secret=pytest.placeholders.client_secret,
            redirect_uri=pytest.placeholders.redirect_uri,
            user_agent=pytest.placeholders.user_agent,
            username=None,
        )

    def test_authorize(self):
        with self.use_cassette():
            token = self.reddit.auth.authorize(pytest.placeholders.auth_code)
            assert isinstance(token, str)
            assert self.reddit.read_only is False
            assert self.reddit.auth.scopes() == {"submit"}

    def test_scopes__read_only(self):
        with self.use_cassette():
            assert self.reddit.read_only is True
            assert self.reddit.auth.scopes() == {"*"}


class TestAuthImplicit(IntegrationTest):
    def setup_reddit(self):
        self.reddit = Reddit(
            client_id=pytest.placeholders.client_id,
            client_secret=None,
            user_agent=pytest.placeholders.user_agent,
        )

    def test_implicit__with_invalid_token(self):
        self.reddit.auth.implicit(
            access_token="invalid_token", expires_in=10, scope="read"
        )
        with self.use_cassette():
            with pytest.raises(InvalidToken):
                self.reddit.user.me()

    def test_scopes__read_only(self):
        with self.use_cassette():
            assert self.reddit.read_only is True
            assert self.reddit.auth.scopes() == {"*"}
