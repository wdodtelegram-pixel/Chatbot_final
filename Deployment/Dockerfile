# =======================================================================
# Dockerfile — builds a container that has pandas (and everything else)
# installed BEFORE the bot starts. This is the fix for the
# "ModuleNotFoundError: No module named 'pandas'" crash.
#
# Works on Railway, Render, Fly.io, Google Cloud Run, AWS, or plain Docker.
# The platform builds this image, which runs pip install, so the
# dependencies are guaranteed present when bot.py runs.
# =======================================================================

# Slim Python base. 3.12 has wheels for every dependency (pandas, etc.),
# so nothing has to compile from source — the build stays fast.
FROM python:3.12-slim

# PURPOSE: never write .pyc files and never buffer stdout, so logs appear
# in the platform's log viewer in real time instead of in delayed chunks.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# All app files live under /app (this matches the /app path in your crash log).
WORKDIR /app

# -----------------------------------------------------------------------
# Install dependencies FIRST, as its own layer.
# PURPOSE: Docker caches layers. By copying only requirements.txt before
# the rest of the code, a change to bot.py does not force a reinstall of
# pandas on every deploy — the pip layer is reused. This is the single
# biggest deploy-speed win.
# -----------------------------------------------------------------------
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# -----------------------------------------------------------------------
# Now copy the application code.
# -----------------------------------------------------------------------
COPY . .

# PURPOSE: prove at BUILD time that the imports resolve. If a dependency is
# missing, the build fails here with a clear message instead of the
# container crash-looping at runtime the way it did for you.
RUN python -c "import telegram, pandas, openpyxl, requests, dotenv; print('All dependencies present.')"

# -----------------------------------------------------------------------
# Start the bot. Uses the exec form so Ctrl-C / platform shutdown signals
# reach Python directly and it stops cleanly.
# -----------------------------------------------------------------------
CMD ["python", "bot.py"]
