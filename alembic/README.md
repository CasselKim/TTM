Generic single-database configuration.
1. 마이그레이션 파일 생성: `alembic upgrade head`
2. 마이그레이션 적용: `alembic upgrade head`
3. 마이그레이션 되돌리기: `alembic downgrade -1`
4. 현재 마이그레이션 상태 확인: `alembic current`
5. 특정 버전으로 업/다운 그레이드: `alembic upgrade <revision_id>`, `alembic downgrade <revision_id>`
