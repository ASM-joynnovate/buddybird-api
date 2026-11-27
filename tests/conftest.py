import os

os.environ.update(
    {
        "DB_NAME": "test",
        "DB_USER": "test",
        "DB_PASSWORD": "test",
        "BACKOFFICE_PASSWORD": "test",
        "STORAGE_ENDPOINT_URL": "https://storage.test",
        "STORAGE_ACCESS_KEY": "test",
        "STORAGE_SECRET_KEY": "test",
        "STORAGE_BUCKET_NAME": "test",
        "QUEUE_URL": "http://queues.test",
    }
)
