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
    postgres_user: str | None = Field(default=None, alias="POSTGRES_USER")
    postgres_password: SecretStr | None = Field(default=None, alias="POSTGRES_PASSWORD")
    postgres_host: str = Field(default="localhost", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    postgres_db: str | None = Field(default=None, alias="POSTGRES_DB")

    @property
    def database_url(self) -> str | None:
        if not self.postgres_user or not self.postgres_db:
            return None

        password = (
            self.postgres_password.get_secret_value()
            if self.postgres_password is not None
            else None
        )
        return URL.create(
            drivername=self.database_driver,
            username=self.postgres_user,
            password=password,
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
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
