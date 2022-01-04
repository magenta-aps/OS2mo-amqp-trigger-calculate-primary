# SPDX-FileCopyrightText: Magenta ApS
#
# SPDX-License-Identifier: MPL-2.0
FROM python:3.9-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1
RUN pip install --no-cache-dir poetry==1.0.3

WORKDIR /opt
COPY poetry.lock pyproject.toml ./
RUN poetry install --no-dev

RUN apt-get update && apt-get install -y git
RUN git clone https://github.com/OS2mo/os2mo-data-import-and-export && \
    pip install --no-cache-dir -e os2mo-data-import-and-export/os2mo_data_import && \
    pip install --no-cache-dir -r os2mo-data-import-and-export/integrations/calculate_primary/requirements.txt

ENV PYTHONPATH="${PYTHONPATH}:/opt/os2mo-data-import-and-export"

RUN pip install ra_utils pydantic tqdm

WORKDIR /app
COPY main.py .
CMD [ "python", "./main.py" ]
