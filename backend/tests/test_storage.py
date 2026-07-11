"""
Storage backend tests — local disk, CDN-base rewrite, and S3 (mocked via moto).

Run: pytest tests/test_storage.py -v   (or python tests/test_storage.py)
"""
import importlib
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _reload_with(env: dict):
    for k, v in env.items():
        os.environ[k] = v
    import app.config as cfg
    importlib.reload(cfg)
    import app.services.storage as storage
    importlib.reload(storage)
    storage.reset_storage()
    return storage


def test_local_backend(tmp_root=None):
    root = tmp_root or tempfile.mkdtemp()
    storage = _reload_with({"STORAGE_TYPE": "local", "STORAGE_PATH": root, "MEDIA_CDN_BASE_URL": ""})
    url = storage.get_storage().save_bytes("generated/a.png", b"hello", "image/png")
    assert url == "/api/v1/media/generated/a.png", url
    assert open(os.path.join(root, "generated/a.png"), "rb").read() == b"hello"
    print("✅ local backend:", url)


def test_local_cdn():
    root = tempfile.mkdtemp()
    storage = _reload_with({"STORAGE_TYPE": "local", "STORAGE_PATH": root,
                            "MEDIA_CDN_BASE_URL": "https://cdn.betty.example"})
    url = storage.get_storage().save_bytes("generated/b.png", b"x", "image/png")
    assert url == "https://cdn.betty.example/api/v1/media/generated/b.png", url
    print("✅ local+CDN:", url)


def test_s3_backend_moto():
    import boto3
    from moto import mock_aws
    with mock_aws():
        boto3.client("s3", region_name="us-east-1").create_bucket(Bucket="betty-media")
        storage = _reload_with({
            "STORAGE_TYPE": "s3", "AWS_S3_BUCKET": "betty-media",
            "AWS_ACCESS_KEY_ID": "test", "AWS_SECRET_ACCESS_KEY": "test",
            "AWS_REGION": "us-east-1", "AWS_S3_ENDPOINT_URL": "",
            "S3_PUBLIC_BASE_URL": "https://cdn.betty.example", "S3_KEY_PREFIX": "media",
        })
        be = storage.get_storage()
        assert be.kind == "s3", be.kind
        url = be.save_bytes("generated/c.png", b"binary-bytes", "image/png")
        assert url == "https://cdn.betty.example/media/generated/c.png", url
        # object really landed in the (mock) bucket
        obj = boto3.client("s3", region_name="us-east-1").get_object(
            Bucket="betty-media", Key="media/generated/c.png")
        assert obj["Body"].read() == b"binary-bytes"
        assert obj["ContentType"] == "image/png"
        print("✅ s3 (moto):", url)


if __name__ == "__main__":
    test_local_backend()
    test_local_cdn()
    test_s3_backend_moto()
    # restore local mode for the running app
    _reload_with({"STORAGE_TYPE": "local", "STORAGE_PATH": "/tmp/aivideo-media",
                  "MEDIA_CDN_BASE_URL": ""})
    print("\nALL STORAGE TESTS PASSED")
