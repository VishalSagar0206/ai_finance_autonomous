# Use a slim Python 3.11 image for a small, secure footprint
FROM python:3.11-slim

# Set security boundaries: Create a non-root user for execution
RUN useradd -m quant_user
WORKDIR /home/quant_user

# Install core quantitative and financial libraries
# Note: We pin versions in a real production scenario
RUN pip install --no-cache-dir \
    pandas \
    numpy \
    yfinance \
    scipy \
    matplotlib \
    scikit-learn

# Copy the execution script (provided by the Coder agent at runtime)
# In a real system, the script would be mounted or piped in.
# For now, we prepare the environment.

USER quant_user

# Default command: run the backtest script
CMD ["python", "backtest.py"]
