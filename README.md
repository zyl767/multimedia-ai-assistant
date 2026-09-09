# 多媒体AI助手系统
前后端分离Web项目 Vue3 + FastAPI

## 技术栈
前端：Vue3 + TypeScript + Vite + Element Plus + Axios
后端：FastAPI + Pydantic + SQLite

## 项目简介
多媒体资源管理Web系统，实现相册素材管理、AI对话交互等功能。
本人工作侧重业务梳理、功能测试、接口校验、本地部署、BUG复现与回归验证。

## 本地启动
### 前端
```bash
npm install
npm run dev
```
### 后端
```bash
pip install -r requirements.txt
uvicorn app:app --reload
