from fastapi import FastAPI, File, UploadFile, HTTPException, APIRouter
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel
from datetime import datetime
import os
import shutil
import sqlite3
import uuid
import json
import subprocess
import requests

router = APIRouter(prefix="/api/album", tags=["旅行相册"])

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
MUSIC_DIR = os.path.join(UPLOAD_DIR, "music")
VIDEO_OUTPUT_DIR = os.path.join(UPLOAD_DIR, "videos")
DB_PATH = os.path.join(BASE_DIR, "travel_album.db")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(MUSIC_DIR, exist_ok=True)
os.makedirs(VIDEO_OUTPUT_DIR, exist_ok=True)

class MediaItem(BaseModel):
    id: str
    filename: str
    original_name: str
    media_type: str
    upload_time: str
    travel_date: str | None = None
    location_name: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    ai_description: str | None = None
    thumbnail: str | None = None

class UpdateMediaRequest(BaseModel):
    travel_date: str | None = None
    location_name: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    ai_description: str | None = None

class GenerateDescriptionRequest(BaseModel):
    location_name: str | None = None
    travel_date: str | None = None
    additional_context: str = ""

class VlogItem(BaseModel):
    id: str
    title: str
    media_ids: list[str]
    created_at: str

class CreateVlogRequest(BaseModel):
    title: str
    media_ids: list[str]
    music_id: str | None = None
    video_path: str | None = None

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS media (
            id TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            original_name TEXT NOT NULL,
            media_type TEXT NOT NULL,
            upload_time TEXT NOT NULL,
            travel_date TEXT,
            location_name TEXT,
            latitude REAL,
            longitude REAL,
            ai_description TEXT,
            thumbnail TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vlogs (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            media_ids TEXT NOT NULL,
            music_id TEXT,
            video_path TEXT,
            created_at TEXT NOT NULL
        )
    ''')
    try:
        cursor.execute('ALTER TABLE vlogs ADD COLUMN video_path TEXT')
    except sqlite3.OperationalError:
        pass
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS music (
            id TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            original_name TEXT NOT NULL,
            title TEXT,
            artist TEXT,
            duration REAL,
            upload_time TEXT NOT NULL,
            url TEXT
        )
    ''')
    try:
        cursor.execute('ALTER TABLE music ADD COLUMN url TEXT')
    except sqlite3.OperationalError:
        pass
    
    cursor.execute('SELECT COUNT(*) FROM music')
    if cursor.fetchone()[0] == 0:
        default_music = [
            ("bgm1", "bgm1.mp3", "bgm1.mp3", "轻柔时光", "轻音乐", 180.0, "2024-01-01T00:00:00", "https://music.163.com/song/media/outer/url?id=523251112.mp3"),
            ("bgm2", "bgm2.mp3", "bgm2.mp3", "旅行日记", "轻音乐", 240.0, "2024-01-01T00:00:01", "https://music.163.com/song/media/outer/url?id=488622128.mp3"),
            ("bgm3", "bgm3.mp3", "bgm3.mp3", "美好回忆", "轻音乐", 200.0, "2024-01-01T00:00:02", "https://music.163.com/song/media/outer/url?id=492015972.mp3"),
            ("bgm4", "bgm4.mp3", "bgm4.mp3", "夏日微风", "轻音乐", 160.0, "2024-01-01T00:00:03", "https://music.163.com/song/media/outer/url?id=486171807.mp3"),
            ("bgm5", "bgm5.mp3", "bgm5.mp3", "星空漫步", "轻音乐", 220.0, "2024-01-01T00:00:04", "https://music.163.com/song/media/outer/url?id=489845772.mp3"),
        ]
        for music in default_music:
            cursor.execute('''
                INSERT INTO music (id, filename, original_name, title, artist, duration, upload_time, url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', music)
    
    conn.commit()
    conn.close()

init_db()

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@router.post("/upload")
async def upload_media(file: UploadFile = File(...)):
    allowed_extensions = [".jpg", ".jpeg", ".png", ".gif", ".mp4", ".mov", ".webm"]
    allowed_types = ["image/jpeg", "image/png", "image/jpg", "image/gif", "image/x-png", "image/pjpeg",
                     "video/mp4", "video/mov", "video/webm", "video/quicktime", "video/x-m4v"]
    
    file_ext = os.path.splitext(file.filename)[1].lower()
    content_type = file.content_type or ""
    
    if file_ext not in allowed_extensions and content_type not in allowed_types:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: {file.filename}")
    
    media_type = "image" if (content_type.startswith("image/") or 
                            file_ext in [".jpg", ".jpeg", ".png", ".gif"]) else "video"
    file_ext = os.path.splitext(file.filename)[1].lower()
    new_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, new_filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    thumbnail = None
    if media_type == "video":
        thumbnail_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}.jpg")
        try:
            subprocess.run(
                ["ffmpeg", "-i", file_path, "-ss", "00:00:01", "-vframes", "1", thumbnail_path],
                capture_output=True,
                timeout=30
            )
            if os.path.exists(thumbnail_path):
                thumbnail = f"/uploads/{os.path.basename(thumbnail_path)}"
        except:
            pass
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO media (id, filename, original_name, media_type, upload_time, thumbnail)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (new_filename, new_filename, file.filename, media_type, datetime.now().isoformat(), thumbnail))
    conn.commit()
    conn.close()
    
    return {"message": "上传成功", "id": new_filename, "media_type": media_type, "thumbnail": thumbnail}

@router.get("/media")
async def get_media_list():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM media ORDER BY travel_date DESC, upload_time DESC')
    rows = cursor.fetchall()
    conn.close()
    
    media_list = []
    for row in rows:
        media_item = MediaItem(
            id=row["id"],
            filename=row["filename"],
            original_name=row["original_name"],
            media_type=row["media_type"],
            upload_time=row["upload_time"],
            travel_date=row["travel_date"],
            location_name=row["location_name"],
            latitude=row["latitude"],
            longitude=row["longitude"],
            ai_description=row["ai_description"],
            thumbnail=row["thumbnail"]
        )
        media_list.append(media_item.dict())
    
    return media_list

@router.get("/media/{media_id}")
async def get_media_detail(media_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM media WHERE id = ?', (media_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="媒体文件不存在")
    
    media_item = MediaItem(
        id=row["id"],
        filename=row["filename"],
        original_name=row["original_name"],
        media_type=row["media_type"],
        upload_time=row["upload_time"],
        travel_date=row["travel_date"],
        location_name=row["location_name"],
        latitude=row["latitude"],
        longitude=row["longitude"],
        ai_description=row["ai_description"],
        thumbnail=row["thumbnail"]
    )
    
    return media_item.dict()

@router.put("/media/{media_id}")
async def update_media(media_id: str, request: UpdateMediaRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    updates = []
    params = []
    
    if request.travel_date is not None:
        updates.append("travel_date = ?")
        params.append(request.travel_date)
    if request.location_name is not None:
        updates.append("location_name = ?")
        params.append(request.location_name)
    if request.latitude is not None:
        updates.append("latitude = ?")
        params.append(request.latitude)
    if request.longitude is not None:
        updates.append("longitude = ?")
        params.append(request.longitude)
    if request.ai_description is not None:
        updates.append("ai_description = ?")
        params.append(request.ai_description)
    
    if not updates:
        raise HTTPException(status_code=400, detail="没有提供更新字段")
    
    params.append(media_id)
    cursor.execute(f'UPDATE media SET {", ".join(updates)} WHERE id = ?', params)
    conn.commit()
    conn.close()
    
    return {"message": "更新成功"}

@router.post("/media/{media_id}/description")
async def generate_description(media_id: str, request: GenerateDescriptionRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM media WHERE id = ?', (media_id,))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="媒体文件不存在")
    
    location_name = request.location_name or row["location_name"] or "未知地点"
    travel_date = request.travel_date or row["travel_date"] or datetime.now().strftime("%Y年%m月%d日")
    
    prompt = f"""
请为这张旅行照片或视频生成一段优美、富有感染力的文案解说。

图片信息：
- 地点：{location_name}
- 日期：{travel_date}
- 额外信息：{request.additional_context}

要求：
1. 语言风格：温暖、浪漫、富有诗意
2. 长度：50-150字
3. 内容：描述画面中的美好瞬间，表达旅行的感受和回忆
4. 使用第二人称"你"
"""
    
    try:
        API_KEY = "sk-ws-H.RPYEEXE.k2df.MEQCIBOOHb84Hg8U5lQTzyXYw5KApDLl9s5UHYhGZKnCkGGiAiAHePJjmda8t7X9JKim930_ALAtpFmoTbd9dxOzT6Fbsg"
        API_URL = "https://ws-o26yurg8g8gfpy22.cn-beijing.maas.aliyuncs.com/compatible-mode/v1/chat/completions"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}"
        }
        
        payload = {
            "model": "qwen-turbo",
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 500
        }
        
        response = requests.post(API_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        
        data = response.json()
        description = data["choices"][0]["message"]["content"].strip()
        
        if not description:
            description = f"在{location_name}的美好时光，{travel_date}留下了珍贵的回忆。画面中的每一个细节都诉说着旅途的故事，这是一段值得珍藏的旅行记忆。"
        
        cursor.execute('UPDATE media SET ai_description = ? WHERE id = ?', (description, media_id))
        conn.commit()
        
        return {"message": "生成成功", "description": description}
    
    except Exception as e:
        fallback_description = f"在{location_name}的美好时光，{travel_date}留下了珍贵的回忆。画面中的每一个细节都诉说着旅途的故事，这是一段值得珍藏的旅行记忆。"
        cursor.execute('UPDATE media SET ai_description = ? WHERE id = ?', (fallback_description, media_id))
        conn.commit()
        
        return {"message": "使用默认文案", "description": fallback_description}
    finally:
        conn.close()

@router.delete("/media/{media_id}")
async def delete_media(media_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM media WHERE id = ?', (media_id,))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="媒体文件不存在")
    
    try:
        file_path = os.path.join(UPLOAD_DIR, row["filename"])
        print(f"尝试删除文件: {file_path}")
        print(f"文件是否存在: {os.path.exists(file_path)}")
        
        if os.path.exists(file_path):
            os.remove(file_path)
            print("文件删除成功")
        else:
            print("文件不存在")
        
        if row["thumbnail"]:
            thumbnail_path = os.path.join(BASE_DIR, "..", row["thumbnail"].lstrip("/"))
            print(f"尝试删除缩略图: {thumbnail_path}")
            if os.path.exists(thumbnail_path):
                os.remove(thumbnail_path)
                print("缩略图删除成功")
            else:
                print("缩略图不存在")
        
        cursor.execute('DELETE FROM media WHERE id = ?', (media_id,))
        conn.commit()
        conn.close()
        
        return {"message": "删除成功"}
    except Exception as e:
        conn.rollback()
        conn.close()
        print(f"删除失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")

@router.post("/vlog")
async def create_vlog(request: CreateVlogRequest):
    title = request.title
    media_ids_list = request.media_ids
    music_id = request.music_id
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    for media_id in media_ids_list:
        cursor.execute('SELECT * FROM media WHERE id = ?', (media_id,))
        if not cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=404, detail=f"媒体文件 {media_id} 不存在")
    
    if music_id:
        cursor.execute('SELECT * FROM music WHERE id = ?', (music_id,))
        if not cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=404, detail=f"音乐文件 {music_id} 不存在")
    
    vlog_id = str(uuid.uuid4())
    video_path = request.video_path
    cursor.execute('''
        INSERT INTO vlogs (id, title, media_ids, music_id, video_path, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (vlog_id, title, json.dumps(media_ids_list), music_id, video_path, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    
    return {"message": "Vlog创建成功", "id": vlog_id, "video_path": video_path}

@router.get("/vlog/{vlog_id}")
async def get_vlog(vlog_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM vlogs WHERE id = ?', (vlog_id,))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Vlog不存在")
    
    media_ids = json.loads(row["media_ids"])
    media_list = []
    
    for media_id in media_ids:
        cursor.execute('SELECT * FROM media WHERE id = ?', (media_id,))
        media_row = cursor.fetchone()
        if media_row:
            media_item = MediaItem(
                id=media_row["id"],
                filename=media_row["filename"],
                original_name=media_row["original_name"],
                media_type=media_row["media_type"],
                upload_time=media_row["upload_time"],
                travel_date=media_row["travel_date"],
                location_name=media_row["location_name"],
                latitude=media_row["latitude"],
                longitude=media_row["longitude"],
                ai_description=media_row["ai_description"],
                thumbnail=media_row["thumbnail"]
            )
            media_list.append(media_item.dict())
    
    music_info = None
    if row["music_id"]:
        cursor.execute('SELECT * FROM music WHERE id = ?', (row["music_id"],))
        music_row = cursor.fetchone()
        if music_row:
            music_info = {
                "id": music_row["id"],
                "filename": music_row["filename"],
                "original_name": music_row["original_name"],
                "title": music_row["title"],
                "artist": music_row["artist"],
                "duration": music_row["duration"]
            }
    
    conn.close()
    
    return {
        "id": row["id"],
        "title": row["title"],
        "media_list": media_list,
        "music": music_info,
        "video_path": row["video_path"],
        "created_at": row["created_at"]
    }

@router.get("/vlogs")
async def get_vlogs():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM vlogs ORDER BY created_at DESC')
    rows = cursor.fetchall()
    conn.close()
    
    vlogs = []
    for row in rows:
        vlogs.append({
            "id": row["id"],
            "title": row["title"],
            "music_id": row["music_id"],
            "created_at": row["created_at"],
            "media_count": len(json.loads(row["media_ids"]))
        })
    
    return vlogs

@router.post("/music")
async def upload_music(file: UploadFile = File(...)):
    allowed_types = ["audio/mpeg", "audio/wav", "audio/ogg", "audio/flac", "audio/mp3"]
    
    if file.content_type not in allowed_types and not file.filename.lower().endswith(('.mp3', '.wav', '.ogg', '.flac')):
        raise HTTPException(status_code=400, detail="不支持的音频文件类型")
    
    file_ext = os.path.splitext(file.filename)[1].lower()
    new_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(MUSIC_DIR, new_filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    duration = 0.0
    try:
        import mutagen
        audio = mutagen.File(file_path)
        if audio:
            duration = audio.info.length
    except:
        pass
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO music (id, filename, original_name, title, artist, duration, upload_time)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (new_filename, new_filename, file.filename or 'unknown', None, None, duration, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    
    return {"message": "音乐上传成功", "id": new_filename, "duration": duration}

@router.get("/music")
async def get_music_list():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM music ORDER BY upload_time DESC')
    rows = cursor.fetchall()
    conn.close()
    
    music_list = []
    for row in rows:
        music_list.append({
            "id": row["id"],
            "filename": row["filename"],
            "original_name": row["original_name"],
            "title": row["title"],
            "artist": row["artist"],
            "duration": row["duration"],
            "upload_time": row["upload_time"],
            "url": row["url"]
        })
    
    return music_list

@router.get("/music/{music_id}")
async def get_music_detail(music_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM music WHERE id = ?', (music_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="音乐文件不存在")
    
    return {
        "id": row["id"],
        "filename": row["filename"],
        "original_name": row["original_name"],
        "title": row["title"],
        "artist": row["artist"],
        "duration": row["duration"],
        "upload_time": row["upload_time"]
    }

@router.delete("/music/{music_id}")
async def delete_music(music_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM music WHERE id = ?', (music_id,))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="音乐文件不存在")
    
    file_path = os.path.join(MUSIC_DIR, row["filename"])
    if os.path.exists(file_path):
        os.remove(file_path)
    
    cursor.execute('DELETE FROM music WHERE id = ?', (music_id,))
    conn.commit()
    conn.close()
    
    return {"message": "删除成功"}

@router.get("/music/{music_id}/stream")
async def stream_music(music_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM music WHERE id = ?', (music_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="音乐文件不存在")
    
    music_url = row["url"]
    if music_url:
        try:
            headers = {
                'Referer': 'https://music.163.com/',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': '*/*',
                'Origin': 'https://music.163.com'
            }
            response = requests.get(music_url, stream=True, headers=headers, timeout=30, allow_redirects=True)
            if response.status_code == 200:
                content_type = response.headers.get('Content-Type', 'audio/mpeg')
                print(f"音乐流成功，Content-Type: {content_type}")
                return StreamingResponse(
                    response.iter_content(chunk_size=1024*1024), 
                    media_type=content_type,
                    headers={
                        'Access-Control-Allow-Origin': '*',
                        'Content-Disposition': 'inline'
                    }
                )
            else:
                print(f"音乐下载失败，状态码: {response.status_code}")
        except Exception as e:
            print(f"音乐代理失败: {e}")
    
    file_path = os.path.join(MUSIC_DIR, row["filename"])
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type='audio/mpeg')
    
    raise HTTPException(status_code=404, detail="音乐文件不存在")

@router.post("/vlog/upload")
async def upload_vlog_video(file: UploadFile = File(...)):
    file_ext = os.path.splitext(file.filename)[1].lower() or '.webm'
    new_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(VIDEO_OUTPUT_DIR, new_filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    return {"message": "视频上传成功", "filename": new_filename}

@router.delete("/vlog/{vlog_id}")
async def delete_vlog(vlog_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM vlogs WHERE id = ?', (vlog_id,))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Vlog不存在")
    
    if row["video_path"]:
        video_path = os.path.join(VIDEO_OUTPUT_DIR, row["video_path"])
        if os.path.exists(video_path):
            os.remove(video_path)
    
    cursor.execute('DELETE FROM vlogs WHERE id = ?', (vlog_id,))
    conn.commit()
    conn.close()
    
    return {"message": "删除成功"}