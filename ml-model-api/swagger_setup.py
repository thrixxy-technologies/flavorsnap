from flask import Flask, jsonify, Response
import os
import re
import yaml


DOC_ENDPOINTS = {"/docs", "/openapi.yaml", "/openapi.json", "/redoc"}


def _spec_file_path() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "openapi.yaml")


def _to_openapi_path(flask_route: str) -> str:
    # Convert Flask route vars (<id>, <path:filename>) to OpenAPI style ({id}, {filename})
    return re.sub(r"<(?:[^:>]+:)?([^>]+)>", r"{\1}", flask_route)


def _load_and_enrich_spec(app: Flask):
    with open(_spec_file_path(), "r", encoding="utf-8") as f:
        spec = yaml.safe_load(f) or {}

    paths = spec.setdefault("paths", {})

    for rule in app.url_map.iter_rules():
        if rule.endpoint == "static":
            continue

        route_path = _to_openapi_path(rule.rule)
        if route_path in DOC_ENDPOINTS:
            continue

        methods = sorted(m for m in rule.methods if m not in {"HEAD", "OPTIONS"})
        if not methods:
            continue

        path_item = paths.setdefault(route_path, {})
        view_func = app.view_functions.get(rule.endpoint)
        summary = ""
        if view_func and view_func.__doc__:
            summary = view_func.__doc__.strip().splitlines()[0]

        for method in methods:
            method_key = method.lower()
            if method_key in path_item:
                continue

            path_item[method_key] = {
                "summary": summary or f"{method} {route_path}",
                "responses": {
                    "200": {"description": "Successful response"}
                }
            }

    return spec

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
            spec = _load_and_enrich_spec(app)
            yaml_content = yaml.safe_dump(spec, sort_keys=False, allow_unicode=True)
            return Response(yaml_content, mimetype='application/x-yaml')
        except FileNotFoundError:
            return jsonify({'error': 'OpenAPI specification not found'}), 404
    
    @app.route('/openapi.json')
    def openapi_json():
        """Serve OpenAPI specification as JSON"""
        try:
            spec = _load_and_enrich_spec(app)
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
