# SPDX-FileCopyrightText: Magenta ApS
#
# SPDX-License-Identifier: MPL-2.0

# Builder
FROM python:3.9 as builder

RUN apt-get update && apt-get -y install unixodbc-dev freetds-dev unixodbc tdsodbc libkrb5-dev libmariadb-dev

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    POETRY_VERSION="1.2.0" \
    POETRY_HOME=/opt/poetry \
    VIRTUAL_ENV="/venv"
ENV PATH="$VIRTUAL_ENV/bin:$POETRY_HOME/bin:$PATH"

# Install poetry in an isolated environment
RUN python -m venv $POETRY_HOME \
    && pip install --no-cache-dir poetry==${POETRY_VERSION}

WORKDIR /opt
COPY .git ./
COPY poetry.lock pyproject.toml ./

RUN poetry version --short > VERSION
RUN git rev-parse --verify HEAD > HASH
RUN cat VERSION HASH

# Install project in another isolated environment
RUN python -m venv $VIRTUAL_ENV
RUN poetry install --no-root --only=main

WORKDIR /app
RUN cp /opt/VERSION .
RUN cp /opt/HASH .
COPY calculate_primary/main.py .
CMD [ "python", "./main.py" ]
