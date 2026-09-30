# 数据库

开发使用 SQLite，审计表 audit(id,event,payload,created_at)。生产建议 PostgreSQL 与 Alembic。