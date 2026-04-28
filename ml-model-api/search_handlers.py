"""
Advanced Search Handlers
Provides full-text search, filtering, and relevance ranking for food recognition results
"""

import re
import math
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from flask import request, jsonify
import logging

try:
    from db_config import get_connection
except Exception:
    get_connection = lambda: None

logger = logging.getLogger(__name__)

@dataclass
class SearchQuery:
    """Search query with filters"""
    text: str
    filters: Dict[str, Any]
    sort: Dict[str, str]
    page: int
    limit: int
    user_id: Optional[str] = None

@dataclass
class SearchResult:
    """Search result item"""
    id: str
    title: str
    description: str
    image_url: str
    thumbnail_url: str
    score: float
    metadata: Dict[str, Any]
    highlights: Dict[str, List[str]]

@dataclass
class SearchResponse:
    """Complete search response"""
    results: List[SearchResult]
    total: int
    page: int
    limit: int
    has_more: bool
    facets: Dict[str, Dict[str, int]]
    suggestions: List[str]
    search_time: float

class SearchIndexer:
    """Manages search indexing and retrieval"""
    
    def __init__(self):
        self.index = {}
        self.reverse_index = {}
        self.document_frequency = {}
        self.total_documents = 0
        
    def index_document(self, doc_id: str, title: str, description: str, 
                     metadata: Dict[str, Any]) -> None:
        """Index a document for search"""
        # Combine text fields
        full_text = f"{title} {description}".lower()
        
        # Tokenize and clean
        tokens = self._tokenize(full_text)
        
        # Forward index
        self.index[doc_id] = {
            'title': title,
            'description': description,
            'metadata': metadata,
            'tokens': tokens,
            'indexed_at': datetime.now()
        }
        
        # Reverse index
        for token in tokens:
            if token not in self.reverse_index:
                self.reverse_index[token] = []
            if doc_id not in self.reverse_index[token]:
                self.reverse_index[token].append(doc_id)
        
        # Document frequency
        for token in set(tokens):
            self.document_frequency[token] = self.document_frequency.get(token, 0) + 1
        
        self.total_documents += 1
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize and clean text"""
        # Convert to lowercase and extract words
        words = re.findall(r'\b\w+\b', text.lower())
        
        # Remove common stop words
        stop_words = {
            'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from',
            'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that',
            'the', 'to', 'was', 'were', 'will', 'with', 'the', 'this', 'those'
        }
        
        return [word for word in words if len(word) > 2 and word not in stop_words]
    
    def search(self, query: SearchQuery) -> SearchResponse:
        """Perform search with ranking"""
        start_time = datetime.now()
        
        # Parse query
        query_tokens = self._tokenize(query.text)
        
        if not query_tokens:
            return SearchResponse(
                results=[],
                total=0,
                page=query.page,
                limit=query.limit,
                has_more=False,
                facets={},
                suggestions=[],
                search_time=0
            )
        
        # Find matching documents
        matching_docs = set()
        token_scores = {}
        
        for token in query_tokens:
            if token in self.reverse_index:
                for doc_id in self.reverse_index[token]:
                    matching_docs.add(doc_id)
                    
                    # Calculate TF-IDF score
                    tf = self.reverse_index[token].count(doc_id)
                    df = self.document_frequency.get(token, 1)
                    idf = math.log(self.total_documents / df)
                    tfidf = tf * idf
                    
                    if doc_id not in token_scores:
                        token_scores[doc_id] = 0
                    token_scores[doc_id] += tfidf
        
        # Filter and sort results
        filtered_results = []
        for doc_id in matching_docs:
            if doc_id in self.index:
                doc = self.index[doc_id]
                
                # Apply filters
                if not self._passes_filters(doc['metadata'], query.filters):
                    continue
                
                # Calculate final score
                score = self._calculate_relevance_score(
                    doc, query_tokens, token_scores.get(doc_id, 0)
                )
                
                # Generate highlights
                highlights = self._generate_highlights(
                    doc, query_tokens
                )
                
                result = SearchResult(
                    id=doc_id,
                    title=doc['title'],
                    description=doc['description'],
                    image_url=doc['metadata'].get('image_url', ''),
                    thumbnail_url=doc['metadata'].get('thumbnail_url', ''),
                    score=score,
                    metadata=doc['metadata'],
                    highlights=highlights
                )
                
                filtered_results.append(result)
        
        # Sort results
        filtered_results.sort(key=lambda x: x.score, reverse=True)
        
        # Apply sorting preferences
        if query.sort.get('field') == 'date':
            filtered_results.sort(
                key=lambda x: x.metadata.get('uploaded_at', datetime.min),
                reverse=query.sort.get('order') == 'desc'
            )
        elif query.sort.get('field') == 'confidence':
            filtered_results.sort(
                key=lambda x: x.metadata.get('confidence', 0),
                reverse=query.sort.get('order') == 'desc'
            )
        
        # Pagination
        total = len(filtered_results)
        start_idx = (query.page - 1) * query.limit
        end_idx = start_idx + query.limit
        paginated_results = filtered_results[start_idx:end_idx]
        
        # Generate facets
        facets = self._generate_facets(filtered_results)
        
        # Generate suggestions
        suggestions = self._generate_suggestions(query.text)
        
        search_time = (datetime.now() - start_time).total_seconds()
        
        return SearchResponse(
            results=paginated_results,
            total=total,
            page=query.page,
            limit=query.limit,
            has_more=end_idx < total,
            facets=facets,
            suggestions=suggestions,
            search_time=search_time
        )
    
    def _passes_filters(self, metadata: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Check if document passes all filters"""
        if not filters:
            return True
        
        # Category filter
        if 'categories' in filters and filters['categories']:
            if metadata.get('category') not in filters['categories']:
                return False
        
        # Tags filter
        if 'tags' in filters and filters['tags']:
            doc_tags = set(metadata.get('tags', []))
            filter_tags = set(filters['tags'])
            if not filter_tags.intersection(doc_tags):
                return False
        
        # Date range filter
        if 'dateRange' in filters and filters['dateRange']:
            uploaded_at = metadata.get('uploaded_at')
            if uploaded_at:
                start_date = filters['dateRange'].get('start')
                end_date = filters['dateRange'].get('end')
                if start_date and uploaded_at < start_date:
                    return False
                if end_date and uploaded_at > end_date:
                    return False
        
        # Size range filter
        if 'sizeRange' in filters and filters['sizeRange']:
            file_size = metadata.get('file_size', 0)
            min_size = filters['sizeRange'].get('min', 0)
            max_size = filters['sizeRange'].get('max', float('inf'))
            if file_size < min_size or file_size > max_size:
                return False
        
        # Format filter
        if 'format' in filters and filters['format']:
            if metadata.get('format') not in filters['format']:
                return False
        
        # Confidence filter
        if 'confidence' in filters and filters['confidence']:
            confidence = metadata.get('confidence', 0)
            min_conf = filters['confidence'].get('min', 0)
            max_conf = filters['confidence'].get('max', 1)
            if confidence < min_conf or confidence > max_conf:
                return False
        
        return True
    
    def _calculate_relevance_score(self, doc: Dict[str, Any], 
                                query_tokens: List[str], base_score: float) -> float:
        """Calculate relevance score using multiple factors"""
        score = base_score
        
        # Title boost
        title_text = doc['title'].lower()
        for token in query_tokens:
            if token in title_text:
                score *= 1.5
        
        # Freshness boost (newer documents get higher score)
        indexed_at = doc.get('indexed_at', datetime.now())
        days_old = (datetime.now() - indexed_at).days
        freshness_boost = max(0.8, 1.0 - (days_old / 365))
        score *= freshness_boost
        
        # Confidence boost
        confidence = doc['metadata'].get('confidence', 0)
        confidence_boost = 1.0 + (confidence * 0.5)
        score *= confidence_boost
        
        return score
    
    def _generate_highlights(self, doc: Dict[str, Any], 
                          query_tokens: List[str]) -> Dict[str, List[str]]:
        """Generate search highlights"""
        highlights = {}
        
        # Highlight in title
        title_text = doc['title']
        title_highlights = []
        for token in query_tokens:
            if token.lower() in title_text.lower():
                # Find all occurrences
                pattern = re.compile(re.escape(token), re.IGNORECASE)
                matches = pattern.finditer(title_text)
                for match in matches:
                    title_highlights.append({
                        'text': match.group(),
                        'start': match.start(),
                        'end': match.end()
                    })
        
        if title_highlights:
            highlights['title'] = [h['text'] for h in title_highlights]
        
        # Highlight in description
        desc_text = doc['description']
        desc_highlights = []
        for token in query_tokens:
            if token.lower() in desc_text.lower():
                pattern = re.compile(re.escape(token), re.IGNORECASE)
                matches = pattern.finditer(desc_text)
                for match in matches:
                    desc_highlights.append({
                        'text': match.group(),
                        'start': match.start(),
                        'end': match.end()
                    })
        
        if desc_highlights:
            highlights['description'] = [h['text'] for h in desc_highlights]
        
        # Highlight in tags
        tags = doc['metadata'].get('tags', [])
        tag_highlights = []
        for token in query_tokens:
            for tag in tags:
                if token.lower() in tag.lower():
                    tag_highlights.append(tag)
        
        if tag_highlights:
            highlights['tags'] = tag_highlights
        
        return highlights
    
    def _generate_facets(self, results: List[SearchResult]) -> Dict[str, Dict[str, int]]:
        """Generate search facets from results"""
        facets = {
            'categories': {},
            'tags': {},
            'formats': {}
        }
        
        for result in results:
            # Category facet
            category = result.metadata.get('category', 'unknown')
            facets['categories'][category] = facets['categories'].get(category, 0) + 1
            
            # Tags facet
            tags = result.metadata.get('tags', [])
            for tag in tags:
                facets['tags'][tag] = facets['tags'].get(tag, 0) + 1
            
            # Format facet
            format_type = result.metadata.get('format', 'unknown')
            facets['formats'][format_type] = facets['formats'].get(format_type, 0) + 1
        
        return facets
    
    def _generate_suggestions(self, query: str) -> List[str]:
        """Generate search suggestions"""
        suggestions = []
        query_lower = query.lower()
        
        # Find similar terms in reverse index
        for token in self.reverse_index.keys():
            if token.startswith(query_lower) and token != query_lower:
                suggestions.append(token)
        
        # Limit suggestions and sort by frequency
        suggestions.sort(key=lambda x: self.document_frequency.get(x, 0), reverse=True)
        return suggestions[:5]

class SearchAnalytics:
    """Tracks and analyzes search performance"""
    
    def __init__(self):
        self.search_history = []
        self.popular_queries = {}
        self.no_result_queries = []
    
    def track_search(self, query: SearchQuery, response: SearchResponse) -> None:
        """Track search for analytics"""
        search_record = {
            'query': query.text,
            'filters': query.filters,
            'sort': query.sort,
            'results_count': response.total,
            'search_time': response.search_time,
            'timestamp': datetime.now(),
            'user_id': query.user_id
        }
        
        self.search_history.append(search_record)
        
        # Track popular queries
        if query.text:
            self.popular_queries[query.text] = self.popular_queries.get(query.text, 0) + 1
        
        # Track no-result queries
        if response.total == 0:
            self.no_result_queries.append(query.text)
        
        # Keep only recent history
        if len(self.search_history) > 10000:
            self.search_history = self.search_history[-5000:]
    
    def get_search_stats(self, days: int = 30) -> Dict[str, Any]:
        """Get search statistics"""
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_searches = [
            s for s in self.search_history 
            if s['timestamp'] > cutoff_date
        ]
        
        if not recent_searches:
            return {
                'total_searches': 0,
                'unique_queries': 0,
                'average_results': 0,
                'average_search_time': 0,
                'no_result_rate': 0,
                'popular_queries': []
            }
        
        total_searches = len(recent_searches)
        unique_queries = len(set(s['query'] for s in recent_searches if s['query']))
        average_results = sum(s['results_count'] for s in recent_searches) / total_searches
        average_search_time = sum(s['search_time'] for s in recent_searches) / total_searches
        no_result_rate = len([s for s in recent_searches if s['results_count'] == 0]) / total_searches
        
        # Get top popular queries
        recent_popular = {
            q: count for q, count in self.popular_queries.items()
            if q in set(s['query'] for s in recent_searches if s['query'])
        }
        top_queries = sorted(recent_popular.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            'total_searches': total_searches,
            'unique_queries': unique_queries,
            'average_results': average_results,
            'average_search_time': average_search_time,
            'no_result_rate': no_result_rate,
            'popular_queries': top_queries
        }

# Global instances
search_indexer = SearchIndexer()
search_analytics = SearchAnalytics()

def register_search_endpoints(app):
    """Register search endpoints"""
    
    @app.route('/api/search', methods=['GET'])
    def search():
        """Advanced search endpoint"""
        try:
            # Parse query parameters
            query_text = request.args.get('q', '').strip()
            page = int(request.args.get('page', 1))
            limit = min(int(request.args.get('limit', 20)), 100)
            
            # Parse filters
            filters = {}
            
            # Category filter
            categories = request.args.getlist('categories')
            if categories:
                filters['categories'] = categories
            
            # Tags filter
            tags = request.args.getlist('tags')
            if tags:
                filters['tags'] = tags
            
            # Date range filter
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            if start_date or end_date:
                filters['dateRange'] = {}
                if start_date:
                    try:
                        filters['dateRange']['start'] = datetime.fromisoformat(start_date)
                    except ValueError:
                        pass
                if end_date:
                    try:
                        filters['dateRange']['end'] = datetime.fromisoformat(end_date)
                    except ValueError:
                        pass
            
            # Size range filter
            min_size = request.args.get('min_size', type=int)
            max_size = request.args.get('max_size', type=int)
            if min_size is not None or max_size is not None:
                filters['sizeRange'] = {
                    'min': min_size or 0,
                    'max': max_size or float('inf')
                }
            
            # Format filter
            formats = request.args.getlist('formats')
            if formats:
                filters['format'] = formats
            
            # Confidence filter
            min_confidence = request.args.get('min_confidence', type=float)
            max_confidence = request.args.get('max_confidence', type=float)
            if min_confidence is not None or max_confidence is not None:
                filters['confidence'] = {
                    'min': min_confidence or 0,
                    'max': max_confidence or 1
                }
            
            # Parse sort
            sort_field = request.args.get('sort', 'relevance')
            sort_order = request.args.get('order', 'desc')
            sort = {'field': sort_field, 'order': sort_order}
            
            # User ID for analytics
            user_id = request.args.get('user_id')
            
            # Create search query
            search_query = SearchQuery(
                text=query_text,
                filters=filters,
                sort=sort,
                page=page,
                limit=limit,
                user_id=user_id
            )
            
            # Perform search
            response = search_indexer.search(search_query)
            
            # Track analytics
            search_analytics.track_search(search_query, response)
            
            return jsonify({
                'results': [
                    {
                        'id': r.id,
                        'title': r.title,
                        'description': r.description,
                        'imageUrl': r.image_url,
                        'thumbnailUrl': r.thumbnail_url,
                        'score': r.score,
                        'metadata': r.metadata,
                        'highlights': r.highlights
                    }
                    for r in response.results
                ],
                'total': response.total,
                'page': response.page,
                'limit': response.limit,
                'hasMore': response.has_more,
                'facets': response.facets,
                'suggestions': response.suggestions,
                'searchTime': response.search_time
            })
            
        except Exception as e:
            logger.error(f"Search error: {str(e)}")
            return jsonify({'error': 'Search failed', 'details': str(e)}), 500
    
    @app.route('/api/search/suggestions', methods=['GET'])
    def search_suggestions():
        """Get auto-complete suggestions"""
        try:
            query = request.args.get('q', '').strip()
            limit = min(int(request.args.get('limit', 10)), 20)
            
            if not query or len(query) < 2:
                return jsonify({'suggestions': []})
            
            suggestions = search_indexer._generate_suggestions(query)
            return jsonify({'suggestions': suggestions[:limit]})
            
        except Exception as e:
            logger.error(f"Suggestions error: {str(e)}")
            return jsonify({'error': 'Failed to get suggestions', 'details': str(e)}), 500
    
    @app.route('/api/search/analytics', methods=['GET'])
    def search_analytics_endpoint():
        """Get search analytics"""
        try:
            days = int(request.args.get('days', 30))
            stats = search_analytics.get_search_stats(days)
            return jsonify(stats)
            
        except Exception as e:
            logger.error(f"Analytics error: {str(e)}")
            return jsonify({'error': 'Failed to get analytics', 'details': str(e)}), 500
    
    @app.route('/api/search/popular', methods=['GET'])
    def popular_searches():
        """Get popular searches"""
        try:
            limit = min(int(request.args.get('limit', 20)), 50)
            popular = search_analytics.popular_queries
            sorted_popular = sorted(popular.items(), key=lambda x: x[1], reverse=True)
            return jsonify({'popular_searches': sorted_popular[:limit]})
            
        except Exception as e:
            logger.error(f"Popular searches error: {str(e)}")
            return jsonify({'error': 'Failed to get popular searches', 'details': str(e)}), 500

def index_database_documents():
    """Index existing documents from database"""
    try:
        conn = get_connection()
        if not conn:
            return
        
        with conn:
            with conn.cursor() as cur:
                # Get recent prediction history
                cur.execute("""
                    SELECT id::text, image_filename, label, confidence, created_at
                    FROM prediction_history
                    WHERE success = true
                    ORDER BY created_at DESC
                    LIMIT 1000
                """)
                
                rows = cur.fetchall() or []
                
                for row in rows:
                    doc_id, filename, label, confidence, created_at = row
                    
                    metadata = {
                        'image_url': f"/uploads/{filename}",
                        'thumbnail_url': f"/thumbnails/{filename}",
                        'confidence': confidence,
                        'category': label,
                        'uploaded_at': created_at,
                        'file_size': 0,  # Would need additional query
                        'format': 'unknown',  # Would need file extension parsing
                        'tags': [label]  # Use label as tag
                    }
                    
                    # Index document
                    search_indexer.index_document(
                        doc_id=doc_id,
                        title=f"Food: {label}",
                        description=f"Classification result with {confidence:.2f} confidence",
                        metadata=metadata
                    )
        
        logger.info(f"Indexed {len(rows)} documents for search")
        
    except Exception as e:
        logger.error(f"Failed to index database documents: {str(e)}")
