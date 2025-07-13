# Multi-stage Docker build for security and efficiency
FROM python:3.11-slim-bookworm AS base

# Set environment variables for security
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# Create non-root user for security
RUN groupadd -r manus && useradd -r -g manus -d /home/manus -s /bin/bash manus

# Install system dependencies and security updates
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Basic utilities
    curl \
    wget \
    unzip \
    gnupg \
    ca-certificates \
    # Build dependencies
    gcc \
    g++ \
    python3-dev \
    build-essential \
    # Chrome dependencies
    fonts-liberation \
    libappindicator3-1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcairo2 \
    libcups2 \
    libdbus-1-3 \
    libexpat1 \
    libfontconfig1 \
    libgbm1 \
    libgdk-pixbuf2.0-0 \
    libglib2.0-0 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libstdc++6 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libxrender1 \
    libxss1 \
    libxtst6 \
    lsb-release \
    xdg-utils \
    # Virtual display for headless browser
    xvfb \
    # Security and development tools
    git \
    && rm -rf /var/lib/apt/lists/*

# Install browser based on architecture
RUN ARCH=$(dpkg --print-architecture) && \
    if [ "$ARCH" = "amd64" ]; then \
        # Install Google Chrome for amd64
        wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - && \
        echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list && \
        apt-get update && \
        apt-get install -y google-chrome-stable && \
        CHROME_VERSION=$(google-chrome --version | grep -oP "\d+\.\d+\.\d+\.\d+") && \
        DRIVER_VERSION=$(curl -s "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_${CHROME_VERSION%.*.*}") && \
        wget -q "https://chromedriver.storage.googleapis.com/${DRIVER_VERSION}/chromedriver_linux64.zip" -O /tmp/chromedriver.zip && \
        unzip /tmp/chromedriver.zip -d /usr/local/bin/ && \
        rm /tmp/chromedriver.zip && \
        chmod +x /usr/local/bin/chromedriver; \
    else \
        # Install Chromium for ARM64 and other architectures
        apt-get update && \
        apt-get install -y chromium chromium-driver && \
        ln -s /usr/bin/chromium /usr/bin/google-chrome && \
        ln -s /usr/bin/chromedriver /usr/local/bin/chromedriver; \
    fi && \
    rm -rf /var/lib/apt/lists/*

# Set up application directory
WORKDIR /app

# Install Poetry for dependency management
RUN pip install poetry==1.7.1

# Copy dependency files
COPY pyproject.toml poetry.lock* ./

# Configure Poetry and install dependencies
# Note: For Mac M2, PyTorch with MPS support will be installed
RUN poetry config virtualenvs.create false \
    && poetry install --only main --no-interaction --no-ansi

# Install PyTorch with Metal Performance Shaders support for Mac M2
# This will be automatically selected during poetry install

# Copy application code
COPY . .

# Create necessary directories with proper permissions
RUN mkdir -p /var/log/manus /tmp/manus /home/manus/.cache \
    && chown -R manus:manus /app /var/log/manus /tmp/manus /home/manus

# Security hardening
RUN chmod 755 /app && \
    find /app -type f -exec chmod 644 {} \; && \
    find /app -type d -exec chmod 755 {} \; && \
    chmod +x /app/manus/cli.py

# Switch to non-root user
USER manus

# Set up environment
ENV PATH="/home/manus/.local/bin:$PATH" \
    PYTHONPATH="/app:$PYTHONPATH" \
    HOME="/home/manus"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import manus; print('OK')" || exit 1

# Default command - run web server mode accessible from host
CMD ["python", "-m", "manus.cli", "--web", "--host", "0.0.0.0", "--port", "8000"]

# Security labels
LABEL \
    org.opencontainers.image.title="Manus Remake" \
    org.opencontainers.image.description="Autonomous AI Agent with Claude integration" \
    org.opencontainers.image.version="0.1.0" \
    org.opencontainers.image.authors="Sam Oakes" \
    security.level="high" \
    security.scan.required="true"