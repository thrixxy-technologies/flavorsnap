import os
import json
import uuid
import time
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from flask import request, jsonify
from werkzeug.utils import secure_filename
import sqlite3
from dataclasses import dataclass, asdict
from enum import Enum

class CategoryStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    IN_TRAINING = "in_training"

class VoteType(Enum):
    UPVOTE = "upvote"
    DOWNVOTE = "downvote"

@dataclass
class FoodCategorySubmission:
    id: str
    name: str
    description: str
    submitted_by: str
    submitted_at: datetime
    status: CategoryStatus
    images: List[str]
    votes_up: int = 0
    votes_down: int = 0
    moderator_notes: str = ""
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None

class CategoryManager:
    def __init__(self, db_path: str = "categories.db", upload_folder: str = "uploads"):
        self.db_path = db_path
        self.upload_folder = upload_folder
        self.init_database()
        os.makedirs(upload_folder, exist_ok=True)
    
    def init_database(self):
        """Initialize the SQLite database for category management"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Categories table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS category_submissions (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                submitted_by TEXT NOT NULL,
                submitted_at TIMESTAMP NOT NULL,
                status TEXT NOT NULL,
                images TEXT NOT NULL,
                votes_up INTEGER DEFAULT 0,
                votes_down INTEGER DEFAULT 0,
                moderator_notes TEXT,
                approved_by TEXT,
                approved_at TIMESTAMP
            )
        ''')
        
        # Votes table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS category_votes (
                id TEXT PRIMARY KEY,
                category_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                vote_type TEXT NOT NULL,
                voted_at TIMESTAMP NOT NULL,
                FOREIGN KEY (category_id) REFERENCES category_submissions (id)
            )
        ''')
        
        # Training queue table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS training_queue (
                id TEXT PRIMARY KEY,
                category_id TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                error_message TEXT,
                FOREIGN KEY (category_id) REFERENCES category_submissions (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def submit_category(self, name: str, description: str, submitted_by: str, 
                      images: List[str]) -> Dict[str, Any]:
        """Submit a new food category for review"""
        category_id = str(uuid.uuid4())
        submitted_at = datetime.now(timezone.utc)
        
        submission = FoodCategorySubmission(
            id=category_id,
            name=name,
            description=description,
            submitted_by=submitted_by,
            submitted_at=submitted_at,
            status=CategoryStatus.PENDING,
            images=images
        )
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO category_submissions 
            (id, name, description, submitted_by, submitted_at, status, images, votes_up, votes_down)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            category_id, name, description, submitted_by, submitted_at,
            CategoryStatus.PENDING.value, json.dumps(images), 0, 0
        ))
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "category_id": category_id,
            "message": "Category submitted successfully for review"
        }
    
    def get_categories(self, status: Optional[CategoryStatus] = None, 
                      limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Get categories with optional status filter"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if status:
            cursor.execute('''
                SELECT * FROM category_submissions 
                WHERE status = ? 
                ORDER BY submitted_at DESC 
                LIMIT ? OFFSET ?
            ''', (status.value, limit, offset))
        else:
            cursor.execute('''
                SELECT * FROM category_submissions 
                ORDER BY submitted_at DESC 
                LIMIT ? OFFSET ?
            ''', (limit, offset))
        
        columns = [description[0] for description in cursor.description]
        rows = cursor.fetchall()
        
        categories = []
        for row in rows:
            category_dict = dict(zip(columns, row))
            category_dict['images'] = json.loads(category_dict['images'])
            categories.append(category_dict)
        
        conn.close()
        return categories
    
    def get_category(self, category_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific category by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM category_submissions WHERE id = ?', (category_id,))
        row = cursor.fetchone()
        
        if row:
            columns = [description[0] for description in cursor.description]
            category_dict = dict(zip(columns, row))
            category_dict['images'] = json.loads(category_dict['images'])
            conn.close()
            return category_dict
        
        conn.close()
        return None
    
    def vote_category(self, category_id: str, user_id: str, vote_type: VoteType) -> Dict[str, Any]:
        """Vote on a category submission"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if category exists and is pending
        cursor.execute('SELECT status FROM category_submissions WHERE id = ?', (category_id,))
        category = cursor.fetchone()
        
        if not category:
            conn.close()
            return {"success": False, "error": "Category not found"}
        
        if category[0] != CategoryStatus.PENDING.value:
            conn.close()
            return {"success": False, "error": "Category is not open for voting"}
        
        # Check if user has already voted
        cursor.execute('SELECT vote_type FROM category_votes WHERE category_id = ? AND user_id = ?', 
                     (category_id, user_id))
        existing_vote = cursor.fetchone()
        
        if existing_vote:
            # Update existing vote
            old_vote_type = existing_vote[0]
            
            # Update vote counts
            if old_vote_type == VoteType.UPVOTE.value:
                cursor.execute('UPDATE category_submissions SET votes_up = votes_up - 1 WHERE id = ?', 
                             (category_id,))
            elif old_vote_type == VoteType.DOWNVOTE.value:
                cursor.execute('UPDATE category_submissions SET votes_down = votes_down - 1 WHERE id = ?', 
                             (category_id,))
            
            # Update vote record
            cursor.execute('''
                UPDATE category_votes 
                SET vote_type = ?, voted_at = ? 
                WHERE category_id = ? AND user_id = ?
            ''', (vote_type.value, datetime.now(timezone.utc), category_id, user_id))
        else:
            # New vote
            vote_id = str(uuid.uuid4())
            cursor.execute('''
                INSERT INTO category_votes (id, category_id, user_id, vote_type, voted_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (vote_id, category_id, user_id, vote_type.value, datetime.now(timezone.utc)))
        
        # Update vote counts
        if vote_type == VoteType.UPVOTE:
            cursor.execute('UPDATE category_submissions SET votes_up = votes_up + 1 WHERE id = ?', 
                         (category_id,))
        elif vote_type == VoteType.DOWNVOTE:
            cursor.execute('UPDATE category_submissions SET votes_down = votes_down + 1 WHERE id = ?', 
                         (category_id,))
        
        conn.commit()
        conn.close()
        
        return {"success": True, "message": "Vote recorded successfully"}
    
    def moderate_category(self, category_id: str, moderator_id: str, 
                         action: str, notes: str = "") -> Dict[str, Any]:
        """Moderate a category submission (approve/reject)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if category exists and is pending
        cursor.execute('SELECT * FROM category_submissions WHERE id = ?', (category_id,))
        category = cursor.fetchone()
        
        if not category:
            conn.close()
            return {"success": False, "error": "Category not found"}
        
        if action not in ["approve", "reject"]:
            conn.close()
            return {"success": False, "error": "Invalid action"}
        
        new_status = CategoryStatus.APPROVED if action == "approve" else CategoryStatus.REJECTED
        
        cursor.execute('''
            UPDATE category_submissions 
            SET status = ?, moderator_notes = ?, approved_by = ?, approved_at = ?
            WHERE id = ?
        ''', (new_status.value, notes, moderator_id, datetime.now(timezone.utc), category_id))
        
        # If approved, add to training queue
        if action == "approve":
            training_id = str(uuid.uuid4())
            cursor.execute('''
                INSERT INTO training_queue (id, category_id, status, created_at)
                VALUES (?, ?, ?, ?)
            ''', (training_id, category_id, "queued", datetime.now(timezone.utc)))
        
        conn.commit()
        conn.close()
        
        return {
            "success": True, 
            "message": f"Category {action}d successfully",
            "status": new_status.value
        }
    
    def get_training_queue(self) -> List[Dict[str, Any]]:
        """Get the training queue for approved categories"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT tq.*, cs.name, cs.description, cs.images
            FROM training_queue tq
            JOIN category_submissions cs ON tq.category_id = cs.id
            WHERE tq.status IN ('queued', 'training')
            ORDER BY tq.created_at ASC
        ''')
        
        columns = [description[0] for description in cursor.description]
        rows = cursor.fetchall()
        
        queue_items = []
        for row in rows:
            item_dict = dict(zip(columns, row))
            item_dict['images'] = json.loads(item_dict['images'])
            queue_items.append(item_dict)
        
        conn.close()
        return queue_items
    
    def update_training_status(self, training_id: str, status: str, error_message: str = None) -> Dict[str, Any]:
        """Update the status of a training job"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        update_fields = ["status = ?"]
        params = [status]
        
        if status == "started":
            update_fields.append("started_at = ?")
            params.append(datetime.now(timezone.utc))
        elif status in ["completed", "failed"]:
            update_fields.append("completed_at = ?")
            params.append(datetime.now(timezone.utc))
            
            if error_message:
                update_fields.append("error_message = ?")
                params.append(error_message)
        
        params.append(training_id)
        
        cursor.execute(f'''
            UPDATE training_queue 
            SET {", ".join(update_fields)}
            WHERE id = ?
        ''', params)
        
        conn.commit()
        conn.close()
        
        return {"success": True, "message": f"Training status updated to {status}"}
    
    def get_popular_categories(self, min_votes: int = 10, limit: int = 20) -> List[Dict[str, Any]]:
        """Get popular categories based on votes"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT *, (votes_up - votes_down) as net_votes
            FROM category_submissions 
            WHERE status = ? AND (votes_up + votes_down) >= ?
            ORDER BY net_votes DESC, votes_up DESC
            LIMIT ?
        ''', (CategoryStatus.PENDING.value, min_votes, limit))
        
        columns = [description[0] for description in cursor.description]
        rows = cursor.fetchall()
        
        categories = []
        for row in rows:
            category_dict = dict(zip(columns, row))
            category_dict['images'] = json.loads(category_dict['images'])
            categories.append(category_dict)
        
        conn.close()
        return categories
