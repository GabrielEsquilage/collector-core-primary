import re

with open('app/api/transparencia.py', 'r') as f:
    content = f.read()

content = content.replace('from app.database import get_db', 'from app.database import get_db, get_async_db\nfrom sqlalchemy.ext.asyncio import AsyncSession')

# Find all async endpoints and replace db: Session = Depends(get_db) with db: AsyncSession = Depends(get_async_db)
content = re.sub(
    r'(async def [a-zA-Z_]+\([^)]*)\bdb:\s*Session\s*=\s*Depends\(get_db\)',
    r'\1db: AsyncSession = Depends(get_async_db)',
    content
)

with open('app/api/transparencia.py', 'w') as f:
    f.write(content)

