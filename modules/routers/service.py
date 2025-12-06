from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from modules.routers.models import Router
from modules.routers.schemas import RouterCreate, RouterUpdate

class RouterService:
    async def get_all(self, session: AsyncSession) -> List[Router]:
        result = await session.execute(select(Router))
        return result.scalars().all()

    async def get_by_id(self, session: AsyncSession, router_id: int) -> Optional[Router]:
        return await session.get(Router, router_id)

    async def create(self, session: AsyncSession, router_in: RouterCreate) -> Router:
        router_db = Router(**router_in.model_dump())
        session.add(router_db)
        await session.commit()
        await session.refresh(router_db)
        return router_db

    async def update(self, session: AsyncSession, router_id: int, router_in: RouterUpdate) -> Optional[Router]:
        router_db = await self.get_by_id(session, router_id)
        if not router_db:
            return None
        
        router_data = router_in.model_dump(exclude_unset=True)
        for key, value in router_data.items():
            setattr(router_db, key, value)
            
        session.add(router_db)
        await session.commit()
        await session.refresh(router_db)
        return router_db

    async def delete(self, session: AsyncSession, router_id: int) -> bool:
        router_db = await self.get_by_id(session, router_id)
        if not router_db:
            return False
            
        await session.delete(router_db)
        await session.commit()
        return True

router_service = RouterService()
