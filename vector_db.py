import os

class VectorDatabase:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
            cls._instance._documents = []
            cls._metadatas = []
            cls._ids = []
        return cls._instance
    
    def initialize(self, persist_directory: str = None):
        if self._initialized:
            return
        
        if persist_directory is None:
            persist_directory = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "chromadb_data"
            )
        
        os.makedirs(persist_directory, exist_ok=True)
        
        self._initialized = True
        print("✅ 向量数据库初始化完成（使用内存存储）")
    
    def get_collection(self):
        if not self._initialized:
            self.initialize()
        return self
    
    def add_documents(self, documents: list, metadatas: list = None, ids: list = None):
        if metadatas is None:
            metadatas = [{} for _ in documents]
        
        if ids is None:
            ids = [f"doc_{i}_{hash(doc) % 1000000}" for i, doc in enumerate(documents)]
        
        self._documents.extend(documents)
        self._metadatas.extend(metadatas)
        self._ids.extend(ids)
        
        print(f"✅ 成功添加 {len(documents)} 条文档到向量库")
        return len(documents)
    
    def query(self, query_text: str, n_results: int = 5):
        results = []
        keywords = query_text.replace(' ', '')
        
        for i, doc in enumerate(self._documents):
            doc_text = doc.replace(' ', '')
            score = 0
            for kw in keywords:
                if kw in doc_text:
                    score += 1
            
            if score > 0:
                results.append({
                    'index': i,
                    'score': score,
                    'content': self._documents[i],
                    'metadata': self._metadatas[i],
                    'id': self._ids[i]
                })
        
        results.sort(key=lambda x: x['score'], reverse=True)
        top_results = results[:n_results]
        
        return {
            'documents': [[r['content'] for r in top_results]] if top_results else [[]],
            'metadatas': [[r['metadata'] for r in top_results]] if top_results else [[]],
            'distances': [[1 - r['score'] / len(keywords) for r in top_results]] if top_results and keywords else [[0] * len(top_results)],
            'ids': [[r['id'] for r in top_results]] if top_results else [[]]
        }
    
    def get_all_documents(self):
        return {
            'documents': self._documents,
            'metadatas': self._metadatas,
            'ids': self._ids
        }
    
    def count(self):
        return len(self._documents)


vector_db = VectorDatabase()