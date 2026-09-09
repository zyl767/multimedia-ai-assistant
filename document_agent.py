import json
import re
from typing import List, Dict, Optional
from langchain_text_splitters import RecursiveCharacterTextSplitter
import docx

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

from vector_db import vector_db


class DocumentAgent:
    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            separators=["\n\n", "\n", "。", "！", "？", "；", "，", "、", " "]
        )
    
    def read_file(self, file_content: bytes, filename: str) -> str:
        """读取文件内容，支持txt/docx/pdf"""
        file_ext = filename.lower().split('.')[-1]
        
        if file_ext == 'txt':
            return file_content.decode('utf-8', errors='ignore')
        elif file_ext == 'docx':
            return self._read_docx(file_content)
        elif file_ext == 'pdf':
            return self._read_pdf(file_content)
        else:
            return file_content.decode('utf-8', errors='ignore')
    
    def _read_docx(self, file_content: bytes) -> str:
        """读取Word文档"""
        import io
        doc = docx.Document(io.BytesIO(file_content))
        full_text = []
        for para in doc.paragraphs:
            full_text.append(para.text)
        return '\n'.join(full_text)
    
    def _read_pdf(self, file_content: bytes) -> str:
        """读取PDF文档"""
        if pdfplumber is None:
            return "⚠️ PDF解析功能不可用，请安装pdfplumber库\n\n" + file_content.decode('utf-8', errors='ignore')
        import io
        text = ""
        with pdfplumber.open(io.BytesIO(file_content)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text
    
    def process_document_with_ai(self, content: str, filename: str) -> List[Dict]:
        """模拟大模型处理文档，添加元数据"""
        print("🔄 正在处理文档...")
        
        structured_docs = []
        
        sections = re.split(r'(?=\n[\u4e00-\u9fa5]{2,10}[、：:])', content)
        
        for idx, section in enumerate(sections):
            section = section.strip()
            if len(section) < 10:
                continue
            
            product_name = "未命名产品"
            doc_type = "产品文档"
            
            lines = section.split('\n')[:3]
            for line in lines:
                if len(line) > 2 and len(line) < 30:
                    product_name = line.strip()
                    break
            
            structured_docs.append({
                "content": section,
                "metadata": {
                    "document_type": doc_type,
                    "product_name": product_name,
                    "source_filename": filename,
                    "section_index": idx
                }
            })
        
        if not structured_docs:
            structured_docs.append({
                "content": content,
                "metadata": {
                    "document_type": "产品文档",
                    "product_name": filename.split('.')[0],
                    "source_filename": filename,
                    "section_index": 0
                }
            })
        
        print(f"✅ 文档结构化完成，共 {len(structured_docs)} 个段落")
        return structured_docs
    
    def split_text(self, content: str) -> List[str]:
        """将长文本切分为小段"""
        chunks = self.text_splitter.split_text(content)
        return chunks
    
    def process_and_store(self, file_content: bytes, filename: str) -> Dict:
        """完整流程：读取→AI处理→切分→入库"""
        print(f"\n📄 开始处理文件: {filename}")
        
        raw_content = self.read_file(file_content, filename)
        print(f"📖 文件读取完成，长度: {len(raw_content)} 字符")
        
        structured_docs = self.process_document_with_ai(raw_content, filename)
        
        all_chunks = []
        all_metadatas = []
        
        for doc in structured_docs:
            chunks = self.split_text(doc['content'])
            
            for chunk in chunks:
                all_chunks.append(chunk)
                all_metadatas.append(doc['metadata'].copy())
        
        vector_db.initialize()
        count = vector_db.add_documents(all_chunks, all_metadatas)
        
        return {
            "success": True,
            "filename": filename,
            "total_chars": len(raw_content),
            "total_chunks": count,
            "message": f"文件 {filename} 处理完成，共入库 {count} 条"
        }


document_agent = DocumentAgent()