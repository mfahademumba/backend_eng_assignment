from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = Field(default="backend-eng-assignment", alias="APP_NAME")
    app_host: str = Field(default="127.0.0.1", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    app_reload: bool = Field(default=True, alias="APP_RELOAD")

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_api_requests: bool = Field(default=True, alias="LOG_API_REQUESTS")

    database_driver: str = Field(default="postgresql+asyncpg", alias="DATABASE_DRIVER")
    database_username: str | None = Field(default=None, alias="DATABASE_USERNAME")
    database_password: SecretStr | None = Field(default=None, alias="DATABASE_PASSWORD")
    database_host: str = Field(default="localhost", alias="DATABASE_HOST")
    database_port: int = Field(default=5432, alias="DATABASE_PORT")
    database_name: str | None = Field(default=None, alias="DATABASE_NAME")

    @property
    def database_url(self) -> str | None:
        if not self.database_username or not self.database_name:
            return None

        password = (
            self.database_password.get_secret_value()
            if self.database_password is not None
            else None
        )
        return URL.create(
            drivername=self.database_driver,
            username=self.database_username,
            password=password,
            host=self.database_host,
            port=self.database_port,
            database=self.database_name,
        ).render_as_string(hide_password=False)

    jwt_secret_key: SecretStr | None = Field(default=None, alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(
        default=15, alias="ACCESS_TOKEN_EXPIRE_MINUTES"
    )
    refresh_token_expire_days: int = Field(default=7, alias="REFRESH_TOKEN_EXPIRE_DAYS")


@lru_cache
def get_settings() -> Settings:
    return Settings()
