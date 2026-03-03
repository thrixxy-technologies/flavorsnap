from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS
import yaml
import os

def setup_swagger(app: Flask):
    """Setup Swagger UI and OpenAPI documentation"""
    
    @app.route('/docs')
    def swagger_ui():
        """Serve Swagger UI"""
        return '''
<!DOCTYPE html>
<html>
<head>
    <title>FlavorSnap API Documentation</title>
    <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@3.52.5/swagger-ui.css" />
    <style>
        html { box-sizing: border-box; overflow: -moz-scrollbars-vertical; overflow-y: scroll; }
        *, *:before, *:after { box-sizing: inherit; }
        body { margin:0; background: #fafafa; }
    </style>
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@3.52.5/swagger-ui-bundle.js"></script>
    <script src="https://unpkg.com/swagger-ui-dist@3.52.5/swagger-ui-standalone-preset.js"></script>
    <script>
        window.onload = function() {
            const ui = SwaggerUIBundle({
                url: '/openapi.yaml',
                dom_id: '#swagger-ui',
                deepLinking: true,
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIStandalonePreset
                ],
                plugins: [
                    SwaggerUIBundle.plugins.DownloadUrl
                ],
                layout: "StandaloneLayout"
            });
        };
    </script>
</body>
</html>
        '''
    
    @app.route('/openapi.yaml')
    def openapi_spec():
        """Serve OpenAPI specification"""
        try:
            with open('openapi.yaml', 'r') as f:
                return yaml.safe_load(f), 200, {'Content-Type': 'application/x-yaml'}
        except FileNotFoundError:
            return jsonify({'error': 'OpenAPI specification not found'}), 404
    
    @app.route('/openapi.json')
    def openapi_json():
        """Serve OpenAPI specification as JSON"""
        try:
            with open('openapi.yaml', 'r') as f:
                spec = yaml.safe_load(f)
                return jsonify(spec)
        except FileNotFoundError:
            return jsonify({'error': 'OpenAPI specification not found'}), 404
    
    @app.route('/redoc')
    def redoc_ui():
        """Serve ReDoc documentation"""
        return '''
<!DOCTYPE html>
<html>
<head>
    <title>FlavorSnap API Documentation - ReDoc</title>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700" rel="stylesheet">
    <style>
        body { margin: 0; padding: 0; }
    </style>
</head>
<body>
    <redoc spec-url='/openapi.json'></redoc>
    <script src="https://cdn.jsdelivr.net/npm/redoc@2.0.0/bundles/redoc.standalone.js"></script>
</body>
</html>
        '''
    
    return app
