from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List, Dict
import os
import shutil
import uuid
import subprocess
from datetime import datetime

from document_agent import document_agent
from vector_db import vector_db
from chat_enhancer import chat_enhancer
from travel_planner import travel_planner
from photo_service import router as photo_router

app = FastAPI(title="Tourism Recommendations API", version="1.0.0")

@app.middleware("http")
async def debug_request(request, call_next):
    print(f"请求方法: {request.method}, 请求路径: {request.url.path}")
    response = await call_next(request)
    print(f"响应状态码: {response.status_code}")
    return response

app.include_router(photo_router)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
VIDEO_DIR = os.path.join(BASE_DIR, "videos")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(VIDEO_DIR, exist_ok=True)

app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
app.mount("/videos", StaticFiles(directory=VIDEO_DIR), name="videos")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    query: str
    n_results: Optional[int] = 5

class ChatResponse(BaseModel):
    success: bool
    query: str
    intents: List[str]
    city: Optional[str]
    season: Optional[str]
    results: List[Dict]
    sources: List[str]
    count: int

@app.on_event("startup")
def startup():
    vector_db.initialize()
    print("🚀 FastAPI服务启动完成")

@app.post("/api/upload", summary="上传文档")
async def upload_file(file: UploadFile = File(...)):
    """上传文档（支持txt/docx/pdf），自动处理并入库"""
    
    try:
        file_content = await file.read()
        
        if not file_content:
            return {"success": False, "message": "文件内容为空"}
        
        result = document_agent.process_and_store(file_content, file.filename)
        
        return result
    
    except Exception as e:
        return {"success": False, "message": f"上传失败: {str(e)}"}

@app.post("/api/chat", response_model=ChatResponse, summary="对话查询")
async def chat(request: ChatRequest):
    """根据问题查询知识库，返回匹配的文档片段"""
    
    try:
        vector_db.initialize()
        
        results = vector_db.query(request.query, request.n_results)
        
        vector_results = []
        if results['documents'] and len(results['documents'][0]) > 0:
            for i in range(len(results['documents'][0])):
                vector_results.append({
                    "content": results['documents'][0][i],
                    "metadata": results['metadatas'][0][i] if results['metadatas'] else {},
                    "distance": results['distances'][0][i] if results['distances'] else 0
                })
        
        enhanced_response = chat_enhancer.generate_enhanced_response(request.query, vector_results)
        
        return ChatResponse(
            success=enhanced_response['success'],
            query=enhanced_response['query'],
            intents=enhanced_response['intents'],
            city=enhanced_response['city'],
            season=enhanced_response['season'],
            results=enhanced_response['results'],
            sources=enhanced_response['sources'],
            count=enhanced_response['count']
        )
    
    except Exception as e:
        return ChatResponse(
            success=False,
            query=request.query,
            intents=[],
            city=None,
            season=None,
            results=[],
            sources=[],
            count=0
        )

@app.get("/api/health", summary="健康检查")
async def health():
    return {"status": "ok", "message": "Tourism Recommendations API is running"}

@app.get("/api/stats", summary="统计信息")
async def stats():
    vector_db.initialize()
    count = vector_db.count()
    return {"document_count": count}

class ImageUploadResponse(BaseModel):
    success: bool
    message: str
    id: str
    filename: str
    url: str

@app.post("/api/image/upload", response_model=ImageUploadResponse, summary="上传图片")
async def upload_image(file: UploadFile = File(...)):
    allowed_extensions = [".jpg", ".jpeg", ".png", ".gif"]
    allowed_types = ["image/jpeg", "image/png", "image/jpg", "image/gif", "image/x-png", "image/pjpeg"]
    
    file_ext = os.path.splitext(file.filename)[1].lower()
    content_type = file.content_type or ""
    
    if file_ext not in allowed_extensions and content_type not in allowed_types:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: {file.filename}，仅支持图片格式")
    
    new_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, new_filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    return {
        "success": True,
        "message": "图片上传成功",
        "id": new_filename,
        "filename": file.filename,
        "url": f"/uploads/{new_filename}"
    }

@app.get("/api/images", summary="获取上传的图片列表")
async def get_images():
    images = []
    if os.path.exists(UPLOAD_DIR):
        for filename in os.listdir(UPLOAD_DIR):
            if filename.lower().endswith((".jpg", ".jpeg", ".png", ".gif")):
                images.append({
                    "id": filename,
                    "filename": filename,
                    "url": f"/uploads/{filename}",
                    "upload_time": datetime.fromtimestamp(os.path.getctime(os.path.join(UPLOAD_DIR, filename))).isoformat()
                })
    return {"images": images}

@app.delete("/api/image/{image_id}", summary="删除图片")
async def delete_image(image_id: str):
    file_path = os.path.join(UPLOAD_DIR, image_id)
    if os.path.exists(file_path):
        os.remove(file_path)
        return {"success": True, "message": "删除成功"}
    raise HTTPException(status_code=404, detail="图片不存在")

class GenerateVideoRequest(BaseModel):
    image_ids: List[str]
    title: Optional[str] = "我的旅行视频"

class GenerateVideoResponse(BaseModel):
    success: bool
    message: str
    video_url: Optional[str] = None

@app.post("/api/video/generate", response_model=GenerateVideoResponse, summary="生成视频")
async def generate_video(request: GenerateVideoRequest):
    if not request.image_ids or len(request.image_ids) == 0:
        raise HTTPException(status_code=400, detail="请选择至少一张图片")
    
    image_paths = []
    for image_id in request.image_ids:
        file_path = os.path.join(UPLOAD_DIR, image_id)
        if os.path.exists(file_path):
            image_paths.append(file_path)
        else:
            raise HTTPException(status_code=404, detail=f"图片 {image_id} 不存在")
    
    video_filename = f"{uuid.uuid4()}.gif"
    video_path = os.path.join(VIDEO_DIR, video_filename)
    
    try:
        from PIL import Image
        
        frames = []
        for img_path in image_paths:
            img = Image.open(img_path)
            frames.append(img.convert("RGB"))
        
        frames[0].save(
            video_path,
            save_all=True,
            append_images=frames[1:],
            duration=1000,
            loop=0
        )
        
        return {
            "success": True,
            "message": "视频生成成功",
            "video_url": f"/videos/{video_filename}"
        }
    except ImportError:
        raise HTTPException(status_code=500, detail="请安装 PIL 库: pip install pillow")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"视频生成失败: {str(e)}")

class TravelPlanRequest(BaseModel):
    query: str

class TravelPlanResponse(BaseModel):
    success: bool
    city: Optional[str] = None
    season: Optional[str] = None
    days: Optional[int] = None
    budget: Optional[float] = None
    budget_level: Optional[str] = None
    from_city: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    daily_plan: Optional[List[Dict]] = None
    hotels: Optional[List[Dict]] = None
    foods: Optional[List[Dict]] = None
    recommendations: Optional[List[Dict]] = None
    tips: Optional[List[str]] = None
    transport: Optional[List[Dict]] = None
    budget_details: Optional[Dict] = None

@app.post("/api/plan", response_model=TravelPlanResponse, summary="生成行程计划")
async def generate_plan(request: TravelPlanRequest):
    """根据用户需求生成详细的旅游行程计划"""
    try:
        plan = travel_planner.generate_travel_plan(request.query)
        return plan
    except Exception as e:
        return TravelPlanResponse(
            success=False,
            city=None,
            season=None,
            days=None,
            title=None,
            description=f"生成行程计划失败: {str(e)}",
            daily_plan=[],
            hotels=[],
            foods=[],
            recommendations=[],
            tips=[]
        )

@app.get("/api/knowledge/cities", summary="获取所有城市列表")
async def get_cities():
    """获取所有支持的旅游城市列表"""
    return {"cities": list(travel_planner.detailed_city_data.keys())}

@app.get("/api/knowledge/city/{city_name}", summary="获取城市详细信息")
async def get_city_info(city_name: str):
    """获取指定城市的详细信息（景点、酒店、美食、路线）"""
    if city_name not in travel_planner.detailed_city_data:
        raise HTTPException(status_code=404, detail="城市不存在")
    return travel_planner.detailed_city_data[city_name]

@app.get("/api/knowledge/budget-levels", summary="获取预算等级")
async def get_budget_levels():
    """获取预算等级配置"""
    return {"budget_levels": travel_planner.budget_levels}

@app.get("/api/knowledge/season-cities", summary="获取季节推荐城市")
async def get_season_cities():
    """获取各季节推荐的旅游城市"""
    return {"season_cities": travel_planner.season_cities}

@app.get("/api/knowledge/train-routes", summary="获取火车路线")
async def get_train_routes():
    """获取所有火车路线信息"""
    routes = []
    for (from_city, to_city), info in travel_planner.train_routes.items():
        routes.append({
            "from_city": from_city,
            "to_city": to_city,
            **info
        })
    return {"routes": routes}

@app.get("/api/knowledge/all-hotels", summary="获取所有酒店信息")
async def get_all_hotels():
    """获取所有城市的酒店信息"""
    hotels = []
    for city_name, city_data in travel_planner.detailed_city_data.items():
        if "酒店" in city_data:
            for hotel in city_data["酒店"]:
                hotels.append({
                    "city": city_name,
                    **hotel
                })
    return {"hotels": hotels}

@app.get("/api/knowledge/all-attractions", summary="获取所有景点信息")
async def get_all_attractions():
    """获取所有城市的景点信息"""
    attractions = []
    for city_name, city_data in travel_planner.detailed_city_data.items():
        if "景点" in city_data:
            for attraction in city_data["景点"]:
                attractions.append({
                    "city": city_name,
                    **attraction
                })
    return {"attractions": attractions}

@app.get("/api/knowledge/all-foods", summary="获取所有美食信息")
async def get_all_foods():
    """获取所有城市的美食信息"""
    foods = []
    for city_name, city_data in travel_planner.detailed_city_data.items():
        if "美食" in city_data:
            for food in city_data["美食"]:
                foods.append({
                    "city": city_name,
                    **food
                })
    return {"foods": foods}

@app.get("/api/knowledge/search", summary="搜索知识库")
async def search_knowledge(query: str):
    """根据关键词搜索知识库中的信息"""
    results = {
        "cities": [],
        "attractions": [],
        "hotels": [],
        "foods": [],
        "routes": []
    }
    
    query_lower = query.lower()
    
    for city_name, city_data in travel_planner.detailed_city_data.items():
        if query_lower in city_name.lower():
            results["cities"].append(city_name)
        
        if "景点" in city_data:
            for attraction in city_data["景点"]:
                if (query_lower in attraction["名称"].lower() or
                    query_lower in attraction["特色"].lower() or
                    query_lower in attraction["介绍"].lower()):
                    results["attractions"].append({"city": city_name, **attraction})
        
        if "酒店" in city_data:
            for hotel in city_data["酒店"]:
                if (query_lower in hotel["名称"].lower() or
                    query_lower in hotel["位置"].lower()):
                    results["hotels"].append({"city": city_name, **hotel})
        
        if "美食" in city_data:
            for food in city_data["美食"]:
                if (query_lower in food["名称"].lower() or
                    query_lower in food["特色"].lower()):
                    results["foods"].append({"city": city_name, **food})
    
    for (from_city, to_city), info in travel_planner.train_routes.items():
        if (query_lower in from_city.lower() or 
            query_lower in to_city.lower()):
            results["routes"].append({
                "from_city": from_city,
                "to_city": to_city,
                **info
            })
    
    return results

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)