# Acme SDK v3 — File uploads

page_id: v3-files
sdk_version: v3
page_type: reference

# File uploads

Uploads in SDK v3 go through `Client.files.upload()`.

## Upload parameters

| Parameter | Type | Default | Required | Description |
|---|---|---|---|---|
| file_path | str | — | yes | Local path of the file to upload. |
| max_file_size_mb | int | 25 | no | Maximum accepted upload size in megabytes; larger files raise `PayloadTooLargeError`. |
| part_size_mb | int | 5 | no | Size of each multipart chunk when uploading large files. |

The default maximum upload size is 25 MB; larger files must use multipart mode, which activates automatically above `part_size_mb`.

```python
client.files.upload(file_path="dataset.csv", max_file_size_mb=25)
```

## Resumable uploads

Interrupted multipart uploads can be resumed within 24 hours by passing the returned `upload_id` back to `Client.files.upload()`.
