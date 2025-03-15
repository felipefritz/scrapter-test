FROM --platform=linux/amd64 python:3.9-slim-bullseye

# use HTTPS
RUN sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list

# force apt to use temp cache dir /tmp
RUN mkdir -p /tmp/apt-cache && echo 'Dir::Cache::archives "/tmp/apt-cache";' > /etc/apt/apt.conf.d/99-cache-dir

# update and install debian-archive-keyring
RUN apt-get update -o Acquire::Check-Valid-Until=false \
    -o Acquire::AllowInsecureRepositories=true \
    -o Acquire::AllowDowngradeToInsecureRepositories=true \
    --allow-releaseinfo-change && \
    apt-get install -y debian-archive-keyring && \
    rm -rf /var/lib/apt/lists/*

# install sys dependencies
RUN apt-get update -o Acquire::Check-Valid-Until=false \
    -o Acquire::AllowInsecureRepositories=true \
    -o Acquire::AllowDowngradeToInsecureRepositories=true \
    --allow-releaseinfo-change && apt-get install -y \
    wget \
    curl \
    gnupg \
    unzip \
    xvfb \
    libxi6 \
    libgconf-2-4 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 && \
    rm -rf /var/lib/apt/lists/*


RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - && \
    echo "deb [arch=amd64] https://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list

# install chrome from repo
RUN apt-get update -o Acquire::Check-Valid-Until=false \
    -o Acquire::AllowInsecureRepositories=true \
    -o Acquire::AllowDowngradeToInsecureRepositories=true \
    --allow-releaseinfo-change && \
    apt-get install -y google-chrome-stable && \
    rm -rf /var/lib/apt/lists/*

# Remove any existing ChromeDriver
RUN rm -f /usr/local/bin/chromedriver || true

# Variables de entorno
ENV PYTHONUNBUFFERED=1
ENV DISPLAY=:99

WORKDIR /app

# install script dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

COPY . /app/

# add a script  entrypoint to start Xvfb
RUN echo '#!/bin/bash\nXvfb :99 -screen 0 1920x1080x16 &\nexec "$@"' > /entrypoint.sh && chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "script.py"]