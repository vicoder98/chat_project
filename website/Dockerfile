# Sử dụng Python 3.8 làm image cơ sở
FROM python:3.8

# Thiết lập thư mục làm việc trong container
WORKDIR /app

# Sao chép file requirements.txt vào container
COPY requirements.txt .

# Cài đặt các thư viện từ requirements.txt
RUN pip install -r requirements.txt

# Cài đặt bcrypt phiên bản cụ thể để tránh lỗi AttributeError
RUN pip install bcrypt==3.2.0

# Sao chép tất cả các file vào thư mục làm việc
COPY . .

# Khởi động ứng dụng với uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
