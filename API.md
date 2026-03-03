# TTS Server API

## Base URL

Khi chạy local qua Docker:

```text
http://localhost:8000
```

Khi chạy cùng stack `docker-compose` gốc:

```text
http://localhost:${TTS_PORT}
```

## 1. Chuyển text thành giọng nói

### Endpoint

```http
POST /tts
Content-Type: application/json
```

### Request Body

```json
{
  "text": "Hello world"
}
```

### Request Schema

| Field | Type | Required | Description |
|---|---|---|---|
| `text` | `string` | Yes | Nội dung cần chuyển thành giọng nói |

### Success Response

Status:

```http
200 OK
```

Headers chính:

```http
Content-Type: audio/wav
Content-Disposition: attachment; filename="speech.wav"
```

Response body:

- Dữ liệu nhị phân của file âm thanh WAV
- Không phải JSON

### Error Responses

#### 400 Bad Request

Xảy ra khi `text` rỗng hoặc chỉ có khoảng trắng.

```json
{
  "detail": "text is empty"
}
```

#### 500 Internal Server Error

Xảy ra khi:

- Không tải được voice model
- Thiếu file voice model hoặc file config
- Lệnh `piper` chạy lỗi

Ví dụ response:

```json
{
  "detail": "Failed to download voice 'en_US-lessac-medium' from https://huggingface.co/rhasspy/piper-voices/resolve/main: ..."
}
```

Hoặc:

```json
{
  "detail": "some error message from piper"
}
```

## Ví dụ gọi API

### curl

```bash
curl -X POST "http://localhost:8000/tts" \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello world"}' \
  --output speech.wav
```

### PowerShell

```powershell
$body = '{"text":"Hello world"}'
Invoke-WebRequest `
  -Method Post `
  -Uri "http://localhost:8000/tts" `
  -ContentType "application/json" `
  -Body $body `
  -OutFile "speech.wav"
```

## Swagger UI

FastAPI tự sinh tài liệu tại:

```text
http://localhost:8000/docs
```

## Ghi chú triển khai

- Service tự tải voice model ở lần chạy đầu nếu chưa có trong `VOICES_DIR`
- Voice mặc định:

```text
en_US-lessac-medium
```

- Các biến môi trường chính:

| Variable | Default | Description |
|---|---|---|
| `VOICE_NAME` | `en_US-lessac-medium` | Tên voice Piper |
| `VOICES_DIR` | `/voices` | Thư mục chứa model `.onnx` và `.onnx.json` |
| `VOICE_DOWNLOAD_BASE_URL` | `https://huggingface.co/rhasspy/piper-voices/resolve/main` | Nguồn tải voice |
| `VOICE_DOWNLOAD_TIMEOUT_SECONDS` | `300` | Timeout khi tải voice |
