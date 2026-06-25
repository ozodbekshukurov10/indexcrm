#!/usr/bin/env sh
set -e

if [ "${WAIT_FOR_DATABASE:-0}" = "1" ]; then
    until nc -z "${POSTGRES_HOST:-db}" "${POSTGRES_PORT:-5432}"; do
        sleep 1
    done
fi

if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
    python manage.py migrate --noinput
fi

if [ "${COLLECT_STATIC:-0}" = "1" ]; then
    python manage.py collectstatic --noinput
fi

exec "$@"
