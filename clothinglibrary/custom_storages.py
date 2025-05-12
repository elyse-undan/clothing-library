# Resource: ChatGPT 4o
# Prompt: "How do I set the S3 cache control for my model's image field?"
# Date: April 6, 2025 12:29am
from storages.backends.s3boto3 import S3Boto3Storage


class ProfilePhotoStorage(S3Boto3Storage):
    def get_object_parameters(self, name):
        params = super().get_object_parameters(name)
        params["CacheControl"] = "max-age=31536000"  # Cache for 1 year
        return params
