from typing import Dict, Any
from .utils import load_env_vars  # Use relative import

class Config:
    def __init__(self):
        self.reload()

    def reload(self) -> None:
        """Reload environment variables and validate them."""
        env_vars = load_env_vars()
        self.github_token = self._validate_token(env_vars['GITHUB_TOKEN'], 'GITHUB_TOKEN')
        self.openai_api_key = self._validate_token(env_vars['OPENAI_API_KEY'], 'OPENAI_API_KEY')
        self.cache_expiration_minutes = int(env_vars['CACHE_EXPIRATION_MINUTES'])
        self.debug = env_vars['DEBUG']
        self.source_code_lines_offset = int(env_vars['SOURCE_CODE_LINES_OFFSET'])

    def _validate_token(self, token: str, token_name: str) -> str:
        """Validate that a token is not empty."""
        if not token:
            raise ValueError(f"{token_name} is required. Please set it in your .env file.")
        return token

    def to_dict(self) -> Dict[str, Any]:
        """Return the configuration as a dictionary."""
        return {
            'github_token': self.github_token,
            'openai_api_key': self.openai_api_key,
            'cache_expiration_minutes': self.cache_expiration_minutes,
            'debug': self.debug,
            'source_code_lines_offset': self.source_code_lines_offset,
        }
