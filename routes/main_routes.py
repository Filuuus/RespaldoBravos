from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app
)
# Ensure all necessary models are imported
from models import Documento, Usuario, Categoria, Carpeta, ActividadUsuario 
from extensions import db
# Ensure utils are imported (especially login_required and log_activity)
from utils import login_required, log_activity 
from sqlalchemy import desc, or_, asc, func as sql_func
from datetime import datetime, timedelta, timezone
from werkzeug.utils import secure_filename # For download filename

main_bp = Blueprint('main_bp', __name__)

@main_bp.route('/')
@login_required
def index_redirect():
    return redirect(url_for('.home_dashboard')) # Use . for same blueprint

@main_bp.route('/home')
@login_required
def home_dashboard():
    user_id = session.get('user_id')
    local_s3_client = current_app.s3_client 

    # Fetch Recent Folders
    try:
        recent_folders = Carpeta.query.filter_by(id_usuario=user_id)\
            .order_by(desc(Carpeta.fecha_modificacion))\
            .limit(6).all() 
    except Exception as e:
        current_app.logger.error(f"Error fetching recent folders for home dashboard: {e}")
        recent_folders = []

    favorite_documents_raw = Documento.query.filter_by(id_usuario=user_id, favorito=True).order_by(Documento.fecha_modificacion.desc()).limit(6).all()
    recent_documents_raw = Documento.query.filter_by(id_usuario=user_id).order_by(Documento.fecha_modificacion.desc()).limit(12).all()
    
    def process_docs_for_preview_and_actions(docs_list):
        processed_docs = []
        for doc in docs_list:
            doc_data = {
                "id_documento": doc.id_documento, 
                "titulo_original": doc.titulo_original,
                "mime_type": doc.mime_type, 
                "file_size": doc.file_size, 
                "favorito": doc.favorito,
                "fecha_modificacion": doc.fecha_modificacion, 
                "categoria": doc.categoria, 
                "id_categoria": doc.id_categoria, 
                "id_carpeta": doc.id_carpeta,
                "periodo_inicio": doc.periodo_inicio, 
                "periodo_fin": doc.periodo_fin,
                "descripcion": doc.descripcion, 
                "s3_bucket": doc.s3_bucket, 
                "s3_object_key": doc.s3_object_key,
                "preview_url": None
            }
            if doc.mime_type and (doc.mime_type.startswith('image/') or doc.mime_type == 'application/pdf') and local_s3_client:
                try:
                    preview_s3_url = local_s3_client.generate_presigned_url(
                        'get_object',
                        Params={'Bucket': doc.s3_bucket, 'Key': doc.s3_object_key},
                        ExpiresIn=300 
                    )
                    doc_data["preview_url"] = preview_s3_url
                except Exception as e:
                    current_app.logger.error(f"Error generating presigned URL for {doc.s3_object_key} in home_dashboard: {e}")
            processed_docs.append(doc_data)
        return processed_docs

    favorite_documents = process_docs_for_preview_and_actions(favorite_documents_raw)
    recent_documents = process_docs_for_preview_and_actions(recent_documents_raw)
    
    active_filters_default = {
        'category_name': 'Any', 'mime_type_name': 'Any', 
        'modified_name': 'Any time', 'period_year_name': 'Any'
    }
    return render_template(
        'home_dashboard.html',
        recent_folders=recent_folders, 
        favorite_documents=favorite_documents,
        recent_documents=recent_documents,
        current_page='home',
        current_folder_id=None,
        active_filters=active_filters_default
    )

@main_bp.route('/files', defaults={'folder_id': None}, methods=['GET'])
@main_bp.route('/files/<int:folder_id>', methods=['GET'])
@login_required
def list_files(folder_id):
    user_id = session.get('user_id')
    local_s3_client = current_app.s3_client

    sort_by = request.args.get('sort_by', 'name')
    sort_dir_param = request.args.get('sort_dir', 'asc')
    
    filter_category_id_str = request.args.get('filter_category', '')
    filter_mime_type_str = request.args.get('filter_mime', '')
    filter_modified_str = request.args.get('filter_modified', '')
    filter_period_year_str = request.args.get('filter_period_year', '')

    active_filters = {
        'category_name': 'Any', 'mime_type_name': 'Any',
        'modified_name': 'Any time', 'period_year_name': 'Any'
    }
    sort_order_func = desc if sort_dir_param == 'desc' else asc
    
    folder_query = Carpeta.query.filter_by(id_usuario=user_id, id_carpeta_padre=folder_id)
    doc_query = Documento.query.filter_by(id_usuario=user_id, id_carpeta=folder_id)\
                         .outerjoin(Categoria, Documento.id_categoria == Categoria.id_categoria)

    if filter_category_id_str and filter_category_id_str != 'all' and filter_category_id_str.isdigit():
        filter_category_id = int(filter_category_id_str)
        doc_query = doc_query.filter(Documento.id_categoria == filter_category_id)
        cat_obj = db.session.get(Categoria, filter_category_id)
        if cat_obj: active_filters['category_name'] = cat_obj.nombre
    
    if filter_mime_type_str and filter_mime_type_str != 'all':
        doc_query = doc_query.filter(Documento.mime_type == filter_mime_type_str) # Exact match for MIME type filter
        if 'pdf' in filter_mime_type_str: active_filters['mime_type_name'] = 'PDF'
        elif 'jpeg' in filter_mime_type_str: active_filters['mime_type_name'] = 'JPEG'
        elif 'png' in filter_mime_type_str: active_filters['mime_type_name'] = 'PNG'
        elif 'text/plain' in filter_mime_type_str: active_filters['mime_type_name'] = 'Text'
        elif 'msword' in filter_mime_type_str or 'wordprocessingml' in filter_mime_type_str: active_filters['mime_type_name'] = 'Word Document'
        elif 'excel' in filter_mime_type_str or 'spreadsheetml' in filter_mime_type_str: active_filters['mime_type_name'] = 'Excel Spreadsheet'
        elif 'powerpoint' in filter_mime_type_str or 'presentationml' in filter_mime_type_str: active_filters['mime_type_name'] = 'PowerPoint'
        elif filter_mime_type_str.startswith('image/'): active_filters['mime_type_name'] = f'Image ({filter_mime_type_str.split("/")[-1].upper()})'
        elif filter_mime_type_str.startswith('video/'): active_filters['mime_type_name'] = f'Video ({filter_mime_type_str.split("/")[-1].upper()})'
        elif filter_mime_type_str.startswith('audio/'): active_filters['mime_type_name'] = f'Audio ({filter_mime_type_str.split("/")[-1].upper()})'
        else: 
            name_part = filter_mime_type_str.split('/')[-1]
            active_filters['mime_type_name'] = name_part.upper() if name_part else filter_mime_type_str.upper()

    if filter_modified_str and filter_modified_str != 'any':
        now_utc = datetime.now(timezone.utc)
        if filter_modified_str == 'today': active_filters['modified_name'] = 'Today'
        elif filter_modified_str == 'yesterday': active_filters['modified_name'] = 'Yesterday'
        elif filter_modified_str == 'last7days': active_filters['modified_name'] = 'Last 7 days'
        elif filter_modified_str == 'last30days': active_filters['modified_name'] = 'Last 30 days'
        
        if filter_modified_str == 'today':
            start_date = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
            doc_query = doc_query.filter(Documento.fecha_modificacion >= start_date)
        elif filter_modified_str == 'yesterday':
            start_date = (now_utc - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
            doc_query = doc_query.filter(Documento.fecha_modificacion >= start_date, Documento.fecha_modificacion < end_date)
        elif filter_modified_str == 'last7days':
            start_date = (now_utc - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
            doc_query = doc_query.filter(Documento.fecha_modificacion >= start_date)
        elif filter_modified_str == 'last30days':
            start_date = (now_utc - timedelta(days=30)).replace(hour=0, minute=0, second=0, microsecond=0)
            doc_query = doc_query.filter(Documento.fecha_modificacion >= start_date)

    if filter_period_year_str and filter_period_year_str != 'all' and filter_period_year_str.isdigit():
        year_to_filter = int(filter_period_year_str)
        doc_query = doc_query.filter(
            or_(
                sql_func.extract('year', Documento.periodo_inicio) == year_to_filter,
                sql_func.extract('year', Documento.periodo_fin) == year_to_filter
            )
        )
        active_filters['period_year_name'] = str(year_to_filter)

    if sort_by == 'name':
        folder_query = folder_query.order_by(sort_order_func(Carpeta.nombre))
        doc_query = doc_query.order_by(sort_order_func(Documento.titulo_original))
    elif sort_by == 'date':
        folder_query = folder_query.order_by(sort_order_func(Carpeta.fecha_modificacion))
        doc_query = doc_query.order_by(sort_order_func(Documento.fecha_modificacion))
    elif sort_by == 'type':
        folder_query = folder_query.order_by(asc(Carpeta.nombre))
        doc_query = doc_query.order_by(sort_order_func(Categoria.nombre), asc(Documento.titulo_original))
    elif sort_by == 'size':
        folder_query = folder_query.order_by(asc(Carpeta.nombre))
        doc_query = doc_query.order_by(sort_order_func(Documento.file_size).nullslast())
    else: 
        folder_query = folder_query.order_by(asc(Carpeta.nombre))
        doc_query = doc_query.order_by(asc(Documento.titulo_original))

    sub_folders = folder_query.all()
    documents_in_folder_raw = doc_query.all()

    documents_for_template = []
    for doc in documents_in_folder_raw:
        doc_data = {
            "id_documento": doc.id_documento, "titulo_original": doc.titulo_original,
            "descripcion": doc.descripcion, "s3_bucket": doc.s3_bucket,
            "s3_object_key": doc.s3_object_key, "mime_type": doc.mime_type,
            "file_size": doc.file_size, "fecha_carga": doc.fecha_carga,
            "fecha_modificacion": doc.fecha_modificacion, "id_usuario": doc.id_usuario,
            "id_carpeta": doc.id_carpeta, "id_categoria": doc.id_categoria,
            "categoria": doc.categoria, "periodo_inicio": doc.periodo_inicio,
            "periodo_fin": doc.periodo_fin, "favorito": doc.favorito,
            "preview_url": None 
        }
        if doc.mime_type and (doc.mime_type.startswith('image/') or doc.mime_type == 'application/pdf') and local_s3_client:
            try:
                preview_s3_url = local_s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': doc.s3_bucket, 'Key': doc.s3_object_key},
                    ExpiresIn=300
                )
                doc_data["preview_url"] = preview_s3_url
            except Exception as e:
                current_app.logger.error(f"Error generating presigned URL for preview {doc.s3_object_key} in list_files: {e}")
        documents_for_template.append(doc_data)

    current_folder_name = "My Files"
    breadcrumbs = []
    if folder_id:
        current_f = db.session.get(Carpeta, folder_id)
        if current_f and current_f.id_usuario == user_id:
            current_folder_name = current_f.nombre
            path_to_root = []
            temp_f = current_f
            while temp_f:
                path_to_root.insert(0, {'id': temp_f.id_carpeta, 'nombre': temp_f.nombre})
                if temp_f.id_carpeta_padre:
                    parent_f = db.session.get(Carpeta, temp_f.id_carpeta_padre)
                    if not parent_f or parent_f.id_usuario != user_id: temp_f = None 
                    else: temp_f = parent_f
                else: temp_f = None 
            breadcrumbs = path_to_root
        else:
            flash("Folder not found or access denied.", "warning")
            return redirect(url_for('.list_files', folder_id=None)) # Use . for same blueprint

    all_available_categories = Categoria.query.order_by(Categoria.nombre).all()
    
    distinct_mime_types_query = db.session.query(Documento.mime_type, sql_func.count(Documento.id_documento).label('count'))\
        .filter(Documento.id_usuario == user_id, Documento.mime_type != None, Documento.mime_type != '')\
        .group_by(Documento.mime_type)\
        .order_by(Documento.mime_type).all()
    
    all_available_mime_types = []
    for mime, count in distinct_mime_types_query:
        name = mime 
        if mime == 'application/pdf': name = f'PDF ({count})'
        elif mime == 'image/jpeg': name = f'JPEG Image ({count})'
        elif mime == 'image/png': name = f'PNG Image ({count})'
        elif mime == 'text/plain': name = f'Text File ({count})'
        elif 'wordprocessingml' in mime or mime == 'application/msword': name = f'Word Document ({count})'
        elif 'spreadsheetml' in mime or mime == 'application/vnd.ms-excel': name = f'Excel Spreadsheet ({count})'
        elif 'presentationml' in mime or mime == 'application/vnd.ms-powerpoint': name = f'PowerPoint ({count})'
        elif mime.startswith('image/'): name = f'Image ({mime.split("/")[-1].upper()}) ({count})'
        elif mime.startswith('video/'): name = f'Video ({mime.split("/")[-1].upper()}) ({count})'
        elif mime.startswith('audio/'): name = f'Audio ({mime.split("/")[-1].upper()}) ({count})'
        elif 'zip' in mime: name = f'ZIP Archive ({count})'
        else:
            name_part = mime.split('/')[-1]
            name = f'{name_part.upper() if name_part else mime.upper()} ({count})'
        all_available_mime_types.append({'value': mime, 'name': name})
        
    distinct_years_query = db.session.query(sql_func.distinct(sql_func.extract('year', Documento.periodo_inicio)))\
        .filter(Documento.id_usuario == user_id, Documento.periodo_inicio != None)\
        .order_by(sql_func.extract('year', Documento.periodo_inicio).desc()).all()
    all_available_period_years = [int(year[0]) for year in distinct_years_query if year[0] is not None]

    sort_by_display_name = "Name"
    if sort_by == 'date': sort_by_display_name = "Date Modified"
    elif sort_by == 'type': sort_by_display_name = "Type"
    elif sort_by == 'size': sort_by_display_name = "Size"

    return render_template(
        'drive_home.html',
        folders=sub_folders,
        documents=documents_for_template,
        current_folder_id=folder_id,
        current_folder_name=current_folder_name,
        breadcrumbs=breadcrumbs,
        sort_by=sort_by,
        sort_dir=sort_dir_param,
        all_available_categories=all_available_categories,
        all_available_mime_types=all_available_mime_types,
        all_available_period_years=all_available_period_years,
        active_filters=active_filters,
        sort_by_display_name=sort_by_display_name,
        current_page='my_files'
    )

@main_bp.route('/activity_log')
@login_required
def activity_log():
    user_id = session.get('user_id')
    page = request.args.get('page', 1, type=int)
    log_pagination = ActividadUsuario.query.filter_by(id_usuario=user_id)\
        .order_by(ActividadUsuario.fecha.desc())\
        .paginate(page=page, per_page=current_app.config.get('ITEMS_PER_PAGE', 20), error_out=False)
    
    active_filters_default = {'category_name': 'Any', 'mime_type_name': 'Any', 
                              'modified_name': 'Any time', 'period_year_name': 'Any'}
    return render_template(
        'activity_log.html',
        log_pagination=log_pagination,
        current_page='activity_log',
        current_folder_id=None,
        active_filters=active_filters_default
    )


@main_bp.route('/search', methods=['GET'])
@login_required
def global_search_route():
    user_id = session.get('user_id')
    search_term = request.args.get('q_global', '').strip()
    found_documents_raw = [] # Initialize
    found_folders = [] # Initialize
    
    local_s3_client = current_app.s3_client 

    if search_term:
        search_like = f"%{search_term}%"
        found_documents_query = Documento.query.filter(
            Documento.id_usuario == user_id,
            or_(
                Documento.titulo_original.ilike(search_like),
                Documento.descripcion.ilike(search_like)
            )
        ).order_by(desc(Documento.fecha_modificacion)).all()
        
        found_folders = Carpeta.query.filter(
            Carpeta.id_usuario == user_id,
            Carpeta.nombre.ilike(search_like)
        ).order_by(asc(Carpeta.nombre)).all()
        
        log_activity(user_id=user_id, activity_type='GLOBAL_SEARCH', 
                     ip_address=request.remote_addr, details=f"Searched: '{search_term}'")

        processed_documents = []
        for doc in found_documents_query: # Iterate over the actual query results
            doc_data = {
                "id_documento": doc.id_documento, "titulo_original": doc.titulo_original,
                "mime_type": doc.mime_type, "file_size": doc.file_size, "favorito": doc.favorito,
                "fecha_modificacion": doc.fecha_modificacion, "categoria": doc.categoria,
                "id_categoria": doc.id_categoria, "id_carpeta": doc.id_carpeta,
                "periodo_inicio": doc.periodo_inicio, "periodo_fin": doc.periodo_fin,
                "descripcion": doc.descripcion, "s3_bucket": doc.s3_bucket, 
                "s3_object_key": doc.s3_object_key,
                "preview_url": None
            }
            if doc.mime_type and (doc.mime_type.startswith('image/') or doc.mime_type == 'application/pdf') and local_s3_client:
                try:
                    preview_s3_url = local_s3_client.generate_presigned_url(
                        'get_object',
                        Params={'Bucket': doc.s3_bucket, 'Key': doc.s3_object_key},
                        ExpiresIn=300
                    )
                    doc_data["preview_url"] = preview_s3_url
                except Exception as e:
                    current_app.logger.error(f"Error generating preview for search result {doc.s3_object_key}: {e}")
            processed_documents.append(doc_data)
        found_documents = processed_documents # Assign processed list


    active_filters_default = {'category_name': 'Any', 'mime_type_name': 'Any', 
                              'modified_name': 'Any time', 'period_year_name': 'Any'}
    return render_template(
        'search_results.html',
        search_term=search_term,
        documents=found_documents, 
        folders=found_folders,
        current_page='search_results', 
        current_folder_id=None,
        active_filters=active_filters_default
    )

# --- NEW: Recent Files Page Route ---
@main_bp.route('/recents')
@login_required
def recent_files_page():
    user_id = session.get('user_id')
    local_s3_client = current_app.s3_client
    page = request.args.get('page', 1, type=int)

    try:
        # Fetch all documents, ordered by most recently modified, with pagination
        documents_pagination = Documento.query.filter_by(id_usuario=user_id)\
            .order_by(desc(Documento.fecha_modificacion))\
            .paginate(page=page, per_page=current_app.config.get('ITEMS_PER_PAGE_GRID', 18), error_out=False)
            # ITEMS_PER_PAGE_GRID can be a new config, e.g., 3 rows of 6 items = 18

        processed_page_documents = []
        for doc in documents_pagination.items:
            doc_data = {
                "id_documento": doc.id_documento, "titulo_original": doc.titulo_original,
                "mime_type": doc.mime_type, "file_size": doc.file_size, "favorito": doc.favorito,
                "fecha_modificacion": doc.fecha_modificacion, "categoria": doc.categoria,
                "id_categoria": doc.id_categoria, "id_carpeta": doc.id_carpeta,
                "periodo_inicio": doc.periodo_inicio, "periodo_fin": doc.periodo_fin,
                "descripcion": doc.descripcion, "s3_bucket": doc.s3_bucket, 
                "s3_object_key": doc.s3_object_key,
                "preview_url": None
            }
            if doc.mime_type and (doc.mime_type.startswith('image/') or doc.mime_type == 'application/pdf') and local_s3_client:
                try:
                    preview_s3_url = local_s3_client.generate_presigned_url(
                        'get_object',
                        Params={'Bucket': doc.s3_bucket, 'Key': doc.s3_object_key},
                        ExpiresIn=300
                    )
                    doc_data["preview_url"] = preview_s3_url
                except Exception as e:
                    current_app.logger.error(f"Error generating presigned URL for recent file {doc.s3_object_key}: {e}")
            processed_page_documents.append(doc_data)
        
    except Exception as e:
        current_app.logger.error(f"Error fetching recent files: {e}")
        flash("Could not load recent files.", "error")
        documents_pagination = None
        processed_page_documents = []
        
    active_filters_default = {
        'category_name': 'Any', 'mime_type_name': 'Any', 
        'modified_name': 'Any time', 'period_year_name': 'Any'
    }

    return render_template(
        'recent_files.html',
        documents_pagination=documents_pagination, # For pagination links
        page_documents=processed_page_documents,    # For displaying items
        current_page='recents', # For sidebar active state
        current_folder_id=None, # No specific folder context
        active_filters=active_filters_default # For base layout consistency
    )
# --- End Recent Files Page Route ---

# --- NEW: Favorites Page Route ---
@main_bp.route('/favorites')
@login_required
def favorite_files_page():
    user_id = session.get('user_id')
    local_s3_client = current_app.s3_client
    page = request.args.get('page', 1, type=int)
    processed_page_documents = [] 
    documents_pagination_raw = None 

    try:
        documents_pagination_raw = Documento.query.filter_by(id_usuario=user_id, favorito=True)\
            .order_by(desc(Documento.fecha_modificacion))\
            .paginate(page=page, per_page=current_app.config.get('ITEMS_PER_PAGE_GRID', 18), error_out=False)
        
        if documents_pagination_raw and documents_pagination_raw.items: 
            for doc in documents_pagination_raw.items:
                doc_data = {
                    "id_documento": doc.id_documento, "titulo_original": doc.titulo_original,
                    "mime_type": doc.mime_type, "file_size": doc.file_size, "favorito": doc.favorito,
                    "fecha_modificacion": doc.fecha_modificacion, "fecha_carga": doc.fecha_carga,
                    "categoria": doc.categoria, "id_categoria": doc.id_categoria, 
                    "id_carpeta": doc.id_carpeta, "periodo_inicio": doc.periodo_inicio, 
                    "periodo_fin": doc.periodo_fin, "descripcion": doc.descripcion, 
                    "s3_bucket": doc.s3_bucket, "s3_object_key": doc.s3_object_key,
                    "preview_url": None
                }
                if doc.mime_type and (doc.mime_type.startswith('image/') or doc.mime_type == 'application/pdf') and local_s3_client:
                    try:
                        preview_s3_url = local_s3_client.generate_presigned_url(
                            'get_object',
                            Params={'Bucket': doc.s3_bucket, 'Key': doc.s3_object_key},
                            ExpiresIn=300
                        )
                        doc_data["preview_url"] = preview_s3_url
                    except Exception as e:
                        current_app.logger.error(f"Error generating presigned URL for favorite file {doc.s3_object_key}: {e}")
                processed_page_documents.append(doc_data)
    except Exception as e:
        current_app.logger.error(f"Error fetching favorite files: {e}")
        flash("Could not load favorite files.", "error")
        
    active_filters_default = {
        'category_name': 'Any', 'mime_type_name': 'Any', 
        'modified_name': 'Any time', 'period_year_name': 'Any'
    }
    return render_template(
        'favorite_files.html', 
        documents_pagination=documents_pagination_raw, 
        page_documents=processed_page_documents,    
        current_page='favorites', 
        current_folder_id=None, 
        active_filters=active_filters_default 
    )

@main_bp.route('/trash')
def trash_page():
    return render_template('trash.html', current_page='trash', current_folder_id=None)