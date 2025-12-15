from sqlalchemy.ext.asyncio import AsyncSession

class DatabaseClient:
    """Клиент для работы с БД"""
    
    def __init__(self, plugin_id: str):
        self.plugin_id = plugin_id
        self._session: Optional[AsyncSession] = None
    
    async def query(self, sql: str, *params) -> List[Dict]:
        """Выполнить SELECT запрос"""
        # Валидация что плагин обращается только к своим таблицам
        if not self._validate_table_access(sql):
            raise PermissionError(f"Plugin {self.plugin_id} cannot access these tables")
        
        # Выполнение запроса
        result = await self._session.execute(sql, params)
        return [dict(row) for row in result.fetchall()]
    
    async def execute(self, sql: str, *params):
        """Выполнить INSERT/UPDATE/DELETE"""
        if not self._validate_table_access(sql):
            raise PermissionError(f"Plugin {self.plugin_id} cannot access these tables")
        
        await self._session.execute(sql, params)
        await self._session.commit()
    
    async def register_model(self, model_class):
        """Зарегистрировать SQLAlchemy модель"""
        # Автоматически создает таблицу с префиксом {plugin_id}_
        table_name = f"{self.plugin_id}_{model_class.__tablename__}"
        # ... создание таблицы