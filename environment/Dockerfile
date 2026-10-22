FROM python:3.13.15-slim-bookworm@sha256:00faa2debb87529f9f0764e9491d8ba400a3678976616c3bd7cb193745ac20d1
COPY tests/ /tests/
COPY environment/microgrid.py /app/microgrid.py
COPY solution/microgrid.py /solution/reference.py
RUN mkdir -p /logs/verifier /output /opt/wheels && chmod 0755 /app/microgrid.py /solution/reference.py
WORKDIR /app
CMD ["sleep", "infinity"]
