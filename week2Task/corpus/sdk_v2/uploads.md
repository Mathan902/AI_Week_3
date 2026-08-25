# Acme SDK v2 — File uploads

page_id: v2-uploads
sdk_version: v2
page_type: reference

# File uploads

Uploads in SDK v2 go through `Client.upload_file()`.

## Upload parameters

| Parameter | Type | Default | Required | Description |
|---|---|---|---|---|
| file_path | str | — | yes | Local path of the file to upload. |
| max_file_size_mb | int | 10 | no | Maximum accepted upload size in megabytes; larger files raise `PayloadTooLargeError`. |
| mime_type | str | auto-detected | no | MIME type sent with the upload. |

The default maximum file size in v2 is 10 MB.

```python
client.upload_file(file_path="report.pdf")
```
