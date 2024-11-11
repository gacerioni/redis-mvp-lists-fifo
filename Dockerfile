FROM python:3.9-slim
LABEL authors="gabriel.cerioni@redis.com"

WORKDIR /app

# Copy requirements file and install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy the main Python script into the container
#COPY main.py .
COPY pix_mvp.py .

# Set environment variables (if you need defaults for local testing)
ENV REDIS_URL=redis://localhost:6379
ENV REDIS_LIST=source_list

# Specify the default command to run the main script
CMD ["python", "pix_mvp.py"]