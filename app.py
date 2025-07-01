from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import logging
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from databases import Database
import asyncio

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

DATABASE_URL = "sqlite:///./items.db"
database = Database(DATABASE_URL)
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class ItemDB(Base):
    __tablename__ = "items"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String)
    price = Column(Float)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app = FastAPI(title="Python API Website", version="1.0.0")

@app.on_event("startup")
async def startup():
    await database.connect()
    logger.info("Database connected successfully")

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()
    logger.info("Database disconnected")

class Item(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    price: float

async def init_sample_data():
    query = "SELECT COUNT(*) FROM items"
    count = await database.fetch_val(query)
    if count == 0:
        sample_items = [
            {'id': 1, 'name': 'Item One', 'description': 'Description for item one', 'price': 10.0},
            {'id': 2, 'name': 'Item Two', 'description': 'Description for item two', 'price': 20.0},
            {'id': 3, 'name': 'Item Three', 'description': 'Description for item three', 'price': 30.0}
        ]
        for item in sample_items:
            insert_query = "INSERT INTO items (id, name, description, price) VALUES (:id, :name, :description, :price)"
            await database.execute(insert_query, item)
        logger.info(f"Initialized database with {len(sample_items)} sample items")
    else:
        logger.info(f"Database already contains {count} items")

@app.on_event("startup")
async def startup_init_data():
    await init_sample_data()

@app.get("/")
async def root():
    logger.info("Root endpoint accessed")
    return {"message": "Welcome to Python API Website"}

@app.get("/health")
async def health_check():
    logger.info("Health check endpoint accessed")
    return {"status": "healthy"}

@app.get("/items", response_model=List[Item])
async def get_items():
    query = "SELECT * FROM items"
    items = await database.fetch_all(query)
    logger.info(f"Getting all items. Total items: {len(items)}")
    return items

@app.get("/items/{item_id}", response_model=Item)
async def get_item(item_id: int):
    logger.info(f"Getting item with ID: {item_id}")
    query = "SELECT * FROM items WHERE id = :item_id"
    item = await database.fetch_one(query, values={"item_id": item_id})
    if item:
        logger.info(f"Item found: {item['name']}")
        return item
    logger.warning(f"Item with ID {item_id} not found")
    raise HTTPException(status_code=404, detail="Item not found")

@app.post("/items", response_model=Item)
async def create_item(item: Item):
    logger.info(f"Creating new item: {item.name} (ID: {item.id})")
    query = "INSERT INTO items (id, name, description, price) VALUES (:id, :name, :description, :price)"
    await database.execute(query, item.dict())
    
    count_query = "SELECT COUNT(*) FROM items"
    total_items = await database.fetch_val(count_query)
    logger.info(f"Item created successfully. Total items: {total_items}")
    return item

@app.put("/items/{item_id}", response_model=Item)
async def update_item(item_id: int, item: Item):
    logger.info(f"Updating item with ID: {item_id}")
    
    check_query = "SELECT name FROM items WHERE id = :item_id"
    existing_item = await database.fetch_one(check_query, values={"item_id": item_id})
    
    if existing_item:
        old_name = existing_item['name']
        update_query = "UPDATE items SET name = :name, description = :description, price = :price WHERE id = :id"
        item_data = item.dict()
        item_data['id'] = item_id
        await database.execute(update_query, item_data)
        logger.info(f"Item updated: {old_name} -> {item.name}")
        return item
    
    logger.warning(f"Item with ID {item_id} not found for update")
    raise HTTPException(status_code=404, detail="Item not found")

@app.delete("/items/{item_id}")
async def delete_item(item_id: int):
    logger.info(f"Deleting item with ID: {item_id}")
    
    check_query = "SELECT name FROM items WHERE id = :item_id"
    existing_item = await database.fetch_one(check_query, values={"item_id": item_id})
    
    if existing_item:
        deleted_name = existing_item['name']
        delete_query = "DELETE FROM items WHERE id = :item_id"
        await database.execute(delete_query, values={"item_id": item_id})
        
        count_query = "SELECT COUNT(*) FROM items"
        remaining_items = await database.fetch_val(count_query)
        logger.info(f"Item deleted: {deleted_name}. Remaining items: {remaining_items}")
        return {"message": "Item deleted"}
    
    logger.warning(f"Item with ID {item_id} not found for deletion")
    raise HTTPException(status_code=404, detail="Item not found")

#if __name__ == "__main__":
#    uvicorn.run(app, host="0.0.0.0", port=8000)
