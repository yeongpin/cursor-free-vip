# syntax=docker/dockerfile:1.7
FROM python:3.13-slim AS base

ARG WITH_BROWSER=false
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    TZ=UTC \
    LANG=C.UTF-8

# Base OS deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl tzdata locales git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first for better caching
COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

# Optionally install Chromium + driver and runtime libs for Selenium/DrissionPage
RUN if [ "$WITH_BROWSER" = "true" ]; then \
      set -eux; \
      apt-get update; \
      apt-get install -y --no-install-recommends \
        chromium chromium-driver \
        fonts-liberation libasound2 \
        libatk1.0-0 libatk-bridge2.0-0 \
        libc6 libdbus-1-3 libdrm2 libexpat1 \
        libgbm1 libgcc1 libglib2.0-0 libgtk-3-0 \
        libnspr4 libnss3 libu2f-udev libuuid1 \
        libx11-6 libx11-xcb1 libxcb1 libxcomposite1 \
        libxcursor1 libxdamage1 libxext6 libxfixes3 \
        libxi6 libxrandr2 libxrender1 libxss1 libxtst6 \
        wget xdg-utils; \
      rm -rf /var/lib/apt/lists/*; \
    fi

# Copy the rest of the source
COPY . .

# Labels
LABEL org.opencontainers.image.source="https://github.com/${GITHUB_REPOSITORY}" \
      org.opencontainers.image.description="Cursor Free VIP containerized" \
      org.opencontainers.image.licenses="CC-BY-NC-ND-4.0"

# Default command; can be overridden with `docker run ... python other.py`
CMD ["python", "main.py"]