from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, AsyncEngine
from sqlalchemy import text, Table, MetaData
from typing import Optional, List, Dict, Any, Type, TYPE_CHECKING
import re
import logging

if TYPE_CHECKING:
    from sqlalchemy.orm import DeclarativeBase

logger = logging.getLogger(__name__)


class DatabaseClient:
    """Клиент для работы с БД в плагинах"""
    
    def __init__(self, plugin_id: str, session_maker: async_sessionmaker):
        """
        Args:
            plugin_id: ID плагина
            session_maker: async_sessionmaker для создания сессий
        """
        self.plugin_id = plugin_id
        self._session_maker = session_maker
        self._session: Optional[AsyncSession] = None
        self._metadata = MetaData()
        self._models: Dict[str, Any] = {}
    
    async def get_session(self) -> AsyncSession:
        """Получить текущую сессию или создать новую"""
        if self._session is None:
            self._session = self._session_maker()
        # mypy hint - сессия всегда будет создана выше
        assert self._session is not None
        return self._session
    
    async def query(self, sql: str, params: Optional[Dict[str, Any]] = None) -> List[Dict]:
        """
        Выполнить SELECT запрос
        
        Args:
            sql: SQL запрос
            params: Параметры запроса
            
        Returns:
            Список словарей с результатами
        """
        # Валидация что плагин обращается только к своим таблицам
        if not self._validate_table_access(sql):
            raise PermissionError(f"Plugin {self.plugin_id} cannot access these tables")
        
        session = await self.get_session()
        result = await session.execute(text(sql), params or {})
        return [dict(row._mapping) for row in result.fetchall()]
    
    async def execute(self, sql: str, params: Optional[Dict[str, Any]] = None):
        """
        Выполнить INSERT/UPDATE/DELETE
        
        Args:
            sql: SQL запрос
            params: Параметры запроса
        """
        if not self._validate_table_access(sql):
            raise PermissionError(f"Plugin {self.plugin_id} cannot access these tables")
        
        session = await self.get_session()
        await session.execute(text(sql), params or {})
        await session.commit()
    
    async def register_model(self, model_class: Any):
        """
        Зарегистрировать SQLAlchemy модель
        
        Автоматически создает таблицу с префиксом {plugin_id}_
        
        Args:
            model_class: SQLAlchemy модель (declarative_base)
        """
        original_tablename = getattr(model_class, '__tablename__', 'unknown')
        prefixed_tablename = f"{self.plugin_id}_{original_tablename}"
        
        # Изменяем имя таблицы
        model_class.__tablename__ = prefixed_tablename
        
        # Сохраняем модель
        self._models[original_tablename] = model_class
        
        # Создаем таблицу
        session = await self.get_session()
        
        # Получаем engine из session
        def _create_tables(sync_session):
            # Используем engine для создания таблиц
            engine = sync_session.get_bind()
            model_class.metadata.create_all(engine)
        
        async with session.begin():
            await session.run_sync(_create_tables)
        
        logger.info(f"Registered model {original_tablename} as {prefixed_tablename}")
    
    def _validate_table_access(self, sql: str) -> bool:
        """
        Проверить что SQL запрос обращается только к таблицам плагина
        
        Args:
            sql: SQL запрос
            
        Returns:
            True если доступ разрешен
        """
        sql_lower = sql.lower()
        
        # Извлекаем имена таблиц из SQL
        # Простой regex для FROM, JOIN, INTO, UPDATE
        table_patterns = [
            r'from\s+([a-z0-9_]+)',
            r'join\s+([a-z0-9_]+)',
            r'into\s+([a-z0-9_]+)',
            r'update\s+([a-z0-9_]+)',
        ]
        
        tables = []
        for pattern in table_patterns:
            matches = re.findall(pattern, sql_lower)
            tables.extend(matches)
        
        # Проверяем что все таблицы начинаются с префикса плагина
        plugin_prefix = f"{self.plugin_id}_"
        for table in tables:
            if not table.startswith(plugin_prefix):
                logger.warning(
                    f"Plugin {self.plugin_id} tried to access table {table} without prefix"
                )
                return False
        
        return True
    
    async def close(self):
        """Закрыть сессию"""
        if self._session:
            await self._session.close()
            self._session = None
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()