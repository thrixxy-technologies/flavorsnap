"""
Batch Processing API Endpoints for FlavorSnap
RESTful endpoints for batch image processing functionality
"""

from flask import Flask, request, jsonify, send_file
from werkzeug.utils import secure_filename
import os
import uuid
from datetime import datetime
from batch_processor import BatchProcessor
from security_config import InputValidator, validate_json_input


def register_batch_endpoints(app: Flask, batch_processor: BatchProcessor):
    """Register batch processing endpoints"""
    
    # Allowed file extensions
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}
    MAX_FILES_PER_BATCH = 50
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    
    def allowed_file(filename):
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    
    @app.route('/api/batch/upload', methods=['POST'])
    def create_batch_job():
        """Create a new batch processing job"""
        try:
            # Validate and sanitize JSON input if present
            if request.is_json:
                json_data = request.get_json()
                is_valid, error_msg = validate_json_input(json_data)
                if not is_valid:
                    return jsonify({'error': error_msg}), 400

            # Check if files are present
            if 'files' not in request.files:
                return jsonify({'error': 'No files provided'}), 400
            
            files = request.files.getlist('files')
            if not files or files[0].filename == '':
                return jsonify({'error': 'No files selected'}), 400
            
            # Validate and sanitize files
            valid_files = []
            errors = []
            
            for i, file in enumerate(files):
                if file and allowed_file(file.filename):
                    # Sanitize filename
                    if file.filename:
                        file.filename = InputValidator.sanitize_filename(file.filename)
                    
                    # Check file size
                    file.seek(0, os.SEEK_END)
                    file_size = file.tell()
                    file.seek(0)
                    
                    if file_size > MAX_FILE_SIZE:
                        errors.append({
                            'file_index': i,
                            'filename': file.filename,
                            'error': f'File size exceeds {MAX_FILE_SIZE // (1024*1024)}MB limit'
                        })
                    else:
                        valid_files.append(file)
                else:
                    errors.append({
                        'file_index': i,
                        'filename': file.filename,
                        'error': 'Invalid file type. Allowed: png, jpg, jpeg, webp, gif'
                    })
            
            if len(valid_files) == 0:
                return jsonify({
                    'error': 'No valid files to process',
                    'errors': errors
                }), 400
            
            if len(valid_files) > MAX_FILES_PER_BATCH:
                return jsonify({
                    'error': f'Too many files. Maximum {MAX_FILES_PER_BATCH} files per batch',
                    'provided_files': len(valid_files)
                }), 400
            
            # Sanitize any additional form data
            batch_params = {}
            for key, value in request.form.items():
                if key not in ['files']:  # Skip file fields
                    sanitized_key = InputValidator.sanitize_string(key, max_length=100)
                    sanitized_value = InputValidator.sanitize_string(str(value), max_length=500)
                    if sanitized_key:
                        batch_params[sanitized_key] = sanitized_value
            
            # Create batch job
            job_id = batch_processor.create_batch_job(valid_files, batch_params)
            
            return jsonify({
                'job_id': job_id,
                'status': 'pending',
                'total_files': len(valid_files),
                'message': f'Batch job created with {len(valid_files)} files',
                'errors': errors if errors else None,
                'params': batch_params
            }), 201
            
        except Exception as e:
            return jsonify({'error': f'Failed to create batch job: {str(e)}'}), 500
    
    @app.route('/api/batch/status/<job_id>', methods=['GET'])
    def get_batch_status(job_id):
        """Get status of a batch job"""
        try:
            job = batch_processor.get_job_status(job_id)
            if not job:
                return jsonify({'error': 'Job not found'}), 404
            
            # Convert job to dict for JSON response
            job_dict = {
                'job_id': job.job_id,
                'status': job.status,
                'created_at': job.created_at.isoformat(),
                'started_at': job.started_at.isoformat() if job.started_at else None,
                'completed_at': job.completed_at.isoformat() if job.completed_at else None,
                'total_files': job.total_files,
                'processed_files': job.processed_files,
                'failed_files': job.failed_files,
                'progress_percentage': round(job.progress_percentage, 2),
                'errors_count': len(job.errors)
            }
            
            return jsonify(job_dict)
            
        except Exception as e:
            return jsonify({'error': f'Failed to get job status: {str(e)}'}), 500
    
    @app.route('/api/batch/results/<job_id>', methods=['GET'])
    def get_batch_results(job_id):
        """Get detailed results for a batch job"""
        try:
            job = batch_processor.get_job_status(job_id)
            if not job:
                return jsonify({'error': 'Job not found'}), 404
            
            if job.status not in ['completed', 'failed']:
                return jsonify({'error': 'Job not completed yet'}), 400
            
            return jsonify({
                'job_id': job_id,
                'status': job.status,
                'summary': batch_processor.get_job_summary(job_id),
                'results': job.results,
                'errors': job.errors
            })
            
        except Exception as e:
            return jsonify({'error': f'Failed to get job results: {str(e)}'}), 500
    
    @app.route('/api/batch/summary/<job_id>', methods=['GET'])
    def get_batch_summary(job_id):
        """Get summary statistics for a batch job"""
        try:
            summary = batch_processor.get_job_summary(job_id)
            if not summary:
                job = batch_processor.get_job_status(job_id)
                if not job:
                    return jsonify({'error': 'Job not found'}), 404
                else:
                    return jsonify({'error': 'Job not completed yet'}), 400
            
            return jsonify(summary)
            
        except Exception as e:
            return jsonify({'error': f'Failed to get job summary: {str(e)}'}), 500
    
    @app.route('/api/batch/export/<job_id>', methods=['GET'])
    def export_batch_results(job_id):
        """Export batch job results"""
        try:
            format_type = request.args.get('format', 'json').lower()
            if format_type not in ['json', 'csv']:
                return jsonify({'error': 'Invalid format. Supported: json, csv'}), 400
            
            filepath = batch_processor.export_results(job_id, format_type)
            if not filepath:
                job = batch_processor.get_job_status(job_id)
                if not job:
                    return jsonify({'error': 'Job not found'}), 404
                else:
                    return jsonify({'error': 'Job not completed yet'}), 400
            
            return send_file(
                filepath,
                as_attachment=True,
                download_name=os.path.basename(filepath),
                mimetype='application/json' if format_type == 'json' else 'text/csv'
            )
            
        except Exception as e:
            return jsonify({'error': f'Failed to export results: {str(e)}'}), 500
    
    @app.route('/api/batch/cancel/<job_id>', methods=['POST'])
    def cancel_batch_job(job_id):
        """Cancel a batch job"""
        try:
            success = batch_processor.cancel_job(job_id)
            if not success:
                job = batch_processor.get_job_status(job_id)
                if not job:
                    return jsonify({'error': 'Job not found'}), 404
                else:
                    return jsonify({'error': 'Job cannot be cancelled'}), 400
            
            return jsonify({
                'job_id': job_id,
                'status': 'cancelled',
                'message': 'Batch job cancelled successfully'
            })
            
        except Exception as e:
            return jsonify({'error': f'Failed to cancel job: {str(e)}'}), 500
    
    @app.route('/api/batch/jobs', methods=['GET'])
    def list_batch_jobs():
        """List all batch jobs"""
        try:
            jobs = batch_processor.get_all_jobs()
            
            # Sort by creation time (newest first)
            jobs.sort(key=lambda x: x.created_at, reverse=True)
            
            jobs_list = []
            for job in jobs:
                jobs_list.append({
                    'job_id': job.job_id,
                    'status': job.status,
                    'created_at': job.created_at.isoformat(),
                    'completed_at': job.completed_at.isoformat() if job.completed_at else None,
                    'total_files': job.total_files,
                    'processed_files': job.processed_files,
                    'failed_files': job.failed_files,
                    'progress_percentage': round(job.progress_percentage, 2)
                })
            
            return jsonify({
                'jobs': jobs_list,
                'total_count': len(jobs_list)
            })
            
        except Exception as e:
            return jsonify({'error': f'Failed to list jobs: {str(e)}'}), 500
    
    @app.route('/api/batch/health', methods=['GET'])
    def batch_health_check():
        """Health check for batch processing service"""
        try:
            current_job = batch_processor.current_job_id
            queue_size = batch_processor.processing_queue.qsize()
            
            return jsonify({
                'status': 'healthy',
                'current_job_id': current_job,
                'queue_size': queue_size,
                'total_jobs': len(batch_processor.jobs),
                'processing_thread_alive': batch_processor.processing_thread.is_alive(),
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            return jsonify({'error': f'Health check failed: {str(e)}'}), 500
