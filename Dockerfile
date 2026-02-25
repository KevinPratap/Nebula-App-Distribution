# Stage 1: Build React Frontend
FROM node:20 AS frontend-builder
WORKDIR /app-frontend
# Copy package.json from the SUBDIRECTORY
COPY nebula-marketing-site/package.json ./
# Install dependencies
RUN npm install --legacy-peer-deps
# Copy source files from the SUBDIRECTORY
COPY nebula-marketing-site/ .

# Accept Razorpay Key as a build argument (Defined in Railway Variables)
ARG VITE_RAZORPAY_KEY_ID
ENV VITE_RAZORPAY_KEY_ID=$VITE_RAZORPAY_KEY_ID

# Run build with verbose output to catch errors
RUN npm run build

# Stage 2: Python Flask Backend
FROM python:3.10
# Using full image to avoid missing build dependencies for bcrypt/ffi
WORKDIR /app

# Upgrade pip to avoid legacy resolver issues
RUN pip install --no-cache-dir --upgrade pip

# Copy backend requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy Flask app source code
# Copy Flask app source code
COPY licenses_server.py .
COPY entrypoint.sh .
COPY start.sh .
# COPY .env . (Removed: Env vars injected by platform)

# Copy templates for admin panel
COPY templates/ ./templates/

# Copy built frontend assets from Stage 1
# Create the local_static directory expected by licenses_server.py
RUN mkdir -p local_static
COPY --from=frontend-builder /app-frontend/dist ./local_static

# Create Python entrypoint for robust variable handling
RUN printf 'import os, subprocess\nport = os.environ.get("PORT", "5000")\nprint(f"Starting on port {port}...")\nsubprocess.run(["gunicorn", "licenses_server:app", "--bind", f"0.0.0.0:{port}"])' > entrypoint.py

# Expose port (railway sets PORT env var, but good to doc)
EXPOSE 5000

# Start command
CMD ["python", "entrypoint.py"]
