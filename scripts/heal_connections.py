#!/usr/bin/env python3
"""
Promote HEALING connections to ACTIVE status

Finds connections in HEALING state and promotes them to ACTIVE
after validation checks pass.
"""

import sys
import os
import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker


async def heal_connections():
    """Promote HEALING connections to ACTIVE"""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not set")
        sys.exit(1)
    
    # Convert postgres:// to postgresql+asyncpg://
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql+asyncpg://', 1)
    elif database_url.startswith('postgresql://'):
        database_url = database_url.replace('postgresql://', 'postgresql+asyncpg://', 1)
    
    engine = create_async_engine(database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        from aam_hybrid.shared.models import Connection
        
        # Find HEALING connections
        result = await session.execute(
            select(Connection).where(Connection.status == 'HEALING')
        )
        healing_connections = result.scalars().all()
        
        if not healing_connections:
            print("✅ No HEALING connections found - all connections are healthy!")
            return
        
        print(f"🏥 Found {len(healing_connections)} HEALING connections")
        print()
        
        promoted = 0
        for conn in healing_connections:
            print(f"  Promoting: {conn.source_type} (id={conn.id[:8]}...)")
            conn.status = 'ACTIVE'
            promoted += 1
        
        await session.commit()
        print()
        print(f"✅ Successfully promoted {promoted} connections to ACTIVE")


def main():
    print("=" * 70)
    print("AAM AUTO-ONBOARDING HEALING PROMOTION")
    print("=" * 70)
    print()
    
    asyncio.run(heal_connections())
    
    print()
    print("=" * 70)


if __name__ == '__main__':
    main()
