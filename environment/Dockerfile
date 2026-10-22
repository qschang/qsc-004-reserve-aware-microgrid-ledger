FROM python:3.13-slim@sha256:27b7c9d4f13ca20bb1170148f02095d50a5dfce1f7f2dabf5ca273727e43b7ea
COPY microgrid.py /app/microgrid.py
RUN mkdir -p /logs/verifier /output && chmod 0755 /app/microgrid.py /logs/verifier
WORKDIR /app
CMD ["sleep", "infinity"]

