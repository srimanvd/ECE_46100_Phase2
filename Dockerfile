# Dockerfile
FROM node:18-bullseye
WORKDIR /app

# System deps for building Python + git (GitPython)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl ca-certificates build-essential \
    libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev \
    libncursesw5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev \
    libffi-dev liblzma-dev \
 && rm -rf /var/lib/apt/lists/*

# Optional node tool
RUN npm install -g typescript

# ---- Install Python 3.11 via pyenv ----
ENV PYENV_ROOT=/opt/pyenv
ENV PATH=$PYENV_ROOT/bin:$PYENV_ROOT/shims:$PATH

RUN curl -fsSL https://pyenv.run | bash \
 && /opt/pyenv/bin/pyenv install 3.11.9 \
 && /opt/pyenv/bin/pyenv global 3.11.9 \
 && /opt/pyenv/shims/python -m ensurepip --upgrade \
 && /opt/pyenv/shims/python -m pip install --upgrade pip

# Project deps + test tooling
COPY requirements.txt .
RUN /opt/pyenv/shims/python -m pip install --no-cache-dir -r requirements.txt || true \
 && /opt/pyenv/shims/python -m pip install --no-cache-dir pytest pytest-cov pytest-mock coverage

# Make src importable
ENV PYTHONPATH=/app:/app/src

# Bring in code
COPY . .
RUN (sed -i 's/\r$//' run && chmod +x run) || true

# Default for local dev (change to autograder for submission if required)
CMD ["/opt/pyenv/shims/python", "run.py"]
# ENTRYPOINT ["/opt/pyenv/shims/python", "autograder.py"]
