# SPDX-FileCopyrightText: Magenta ApS
#
# SPDX-License-Identifier: MPL-2.0
FROM python:3.11

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    POETRY_VERSION="1.8.3" \
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
COPY calculate_primary ./calculate_primary
CMD [ "python","-m", "calculate_primary.main" ]
