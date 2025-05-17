# RespaldoBravos/routes/main_routes.py
from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app
)
# Ensure all necessary models are imported
from models import Documento, Usuario, Categoria, Carpeta, ActividadUsuario 
from extensions import db
# Ensure utils are imported
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
    favorite_documents = Documento.query.filter_by(id_usuario=user_id, favorito=True).order_by(Documento.fecha_modificacion.desc()).limit(10).all()
    recent_documents = Documento.query.filter_by(id_usuario=user_id).order_by(Documento.fecha_modificacion.desc()).limit(10).all()
    
    active_filters_default = {
        'category_name': 'Any', 'mime_type_name': 'Any', 
        'modified_name': 'Any time', 'period_year_name': 'Any'
    }
    return render_template(
        'home_dashboard.html',
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
    local_s3_client = current_app.s3_client # Get S3 client from app context

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

    # Apply Category Filter
    if filter_category_id_str and filter_category_id_str != 'all' and filter_category_id_str.isdigit():
        filter_category_id = int(filter_category_id_str)
        doc_query = doc_query.filter(Documento.id_categoria == filter_category_id)
        cat_obj = db.session.get(Categoria, filter_category_id)
        if cat_obj: active_filters['category_name'] = cat_obj.nombre
    
    # Apply MIME Type Filter
    if filter_mime_type_str and filter_mime_type_str != 'all':
        doc_query = doc_query.filter(Documento.mime_type.ilike(f'%{filter_mime_type_str}%'))
        if 'pdf' in filter_mime_type_str: active_filters['mime_type_name'] = 'PDF'
        elif 'jpeg' in filter_mime_type_str: active_filters['mime_type_name'] = 'JPEG'
        elif 'png' in filter_mime_type_str: active_filters['mime_type_name'] = 'PNG'
        elif 'text/plain' in filter_mime_type_str: active_filters['mime_type_name'] = 'Text'
        elif 'word' in filter_mime_type_str: active_filters['mime_type_name'] = 'Word Document'
        elif 'excel' in filter_mime_type_str: active_filters['mime_type_name'] = 'Excel Spreadsheet'
        elif 'powerpoint' in filter_mime_type_str: active_filters['mime_type_name'] = 'PowerPoint Presentation'
        else: 
            name_part = filter_mime_type_str.split('/')[-1]
            active_filters['mime_type_name'] = name_part.upper() if name_part else filter_mime_type_str.upper()

    # Apply Modified Date Filter
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

    # Apply Period Year Filter
    if filter_period_year_str and filter_period_year_str != 'all' and filter_period_year_str.isdigit():
        year_to_filter = int(filter_period_year_str)
        doc_query = doc_query.filter(
            or_(
                sql_func.extract('year', Documento.periodo_inicio) == year_to_filter,
                sql_func.extract('year', Documento.periodo_fin) == year_to_filter
            )
        )
        active_filters['period_year_name'] = str(year_to_filter)

    # Apply Sorting
    if sort_by == 'name':
        folder_query = folder_query.order_by(sort_order_func(Carpeta.nombre))
        doc_query = doc_query.order_by(sort_order_func(Documento.titulo_original))
    elif sort_by == 'date':
        folder_query = folder_query.order_by(sort_order_func(Carpeta.fecha_modificacion))
        doc_query = doc_query.order_by(sort_order_func(Documento.fecha_modificacion))
    elif sort_by == 'type':
        folder_query = folder_query.order_by(asc(Carpeta.nombre))
        doc_query = doc_query.order_by(sort_order_func(Categoria.nombre), asc(Documento.titulo_original)) # Uses joined Categoria
    elif sort_by == 'size':
        folder_query = folder_query.order_by(asc(Carpeta.nombre))
        doc_query = doc_query.order_by(sort_order_func(Documento.file_size).nullslast())
    else: 
        folder_query = folder_query.order_by(asc(Carpeta.nombre))
        doc_query = doc_query.order_by(asc(Documento.titulo_original))

    sub_folders = folder_query.all()
    documents_in_folder_raw = doc_query.all()

    # --- Process documents to add preview_url for images ---
    documents_for_template = []
    for doc in documents_in_folder_raw:
        # Create a dictionary or augment the object for the template
        doc_data = {
            "id_documento": doc.id_documento,
            "titulo_original": doc.titulo_original,
            "descripcion": doc.descripcion,
            "s3_bucket": doc.s3_bucket,
            "s3_object_key": doc.s3_object_key,
            "mime_type": doc.mime_type,
            "file_size": doc.file_size,
            "fecha_carga": doc.fecha_carga,
            "fecha_modificacion": doc.fecha_modificacion,
            "id_usuario": doc.id_usuario,
            "id_carpeta": doc.id_carpeta,
            "id_categoria": doc.id_categoria,
            "categoria": doc.categoria, # Keep the relationship object if template uses it
            "periodo_inicio": doc.periodo_inicio,
            "periodo_fin": doc.periodo_fin,
            "favorito": doc.favorito,
            "preview_url": None # Initialize preview_url
        }
        
        if doc.mime_type and doc.mime_type.startswith('image/') and local_s3_client:
            try:
                preview_s3_url = local_s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': doc.s3_bucket, 'Key': doc.s3_object_key},
                    ExpiresIn=300  # URL valid for 5 minutes for preview
                )
                doc_data["preview_url"] = preview_s3_url
            except Exception as e:
                current_app.logger.error(f"Error generating presigned URL for preview {doc.s3_object_key}: {e}")
        
        documents_for_template.append(doc_data)
    # --- End document processing for preview ---

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
            return redirect(url_for('.list_files', folder_id=None))


    all_available_categories = Categoria.query.order_by(Categoria.nombre).all()
    
    distinct_mime_types_query = db.session.query(Documento.mime_type, sql_func.count(Documento.id_documento))\
        .filter(Documento.id_usuario == user_id, Documento.mime_type != None)\
        .group_by(Documento.mime_type)\
        .order_by(Documento.mime_type).all()
    all_available_mime_types = []
    for mime, count in distinct_mime_types_query:
        name = mime
        if 'pdf' in mime: name = f'PDF ({count})'
        elif 'jpeg' in mime: name = f'JPEG ({count})'
        elif 'png' in mime: name = f'PNG ({count})'
        elif 'text/plain' in mime: name = f'Text ({count})'
        elif 'word' in mime: name = f'Word ({count})'
        elif 'excel' in mime: name = f'Excel ({count})'
        elif 'powerpoint' in mime: name = f'PowerPoint ({count})'
        else: name = f'{mime.split("/")[-1].upper() if "/" in mime else mime.upper()} ({count})'
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
    
    active_filters_default = {'category_name': 'Any', 'mime_type_name': 'Any', 'modified_name': 'Any time', 'period_year_name': 'Any'}
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
    found_documents_raw = []
    found_folders = []
    
    local_s3_client = current_app.s3_client

    if search_term:
        search_like = f"%{search_term}%"
        found_documents_query = Documento.query.filter(
            Documento.id_usuario == user_id,
            or_(
                Documento.titulo_original.ilike(search_like),
                Documento.descripcion.ilike(search_like)
            )
        ).all()
        found_folders = Carpeta.query.filter(
            Carpeta.id_usuario == user_id,
            Carpeta.nombre.ilike(search_like)
        ).all()
        log_activity(user_id=user_id, activity_type='GLOBAL_SEARCH', ip_address=request.remote_addr, details=f"Searched: '{search_term}'")

        # Process documents for preview URLs if needed by search_results.html
        processed_documents = []
        for doc in found_documents_query:
            doc_data = { "id_documento": doc.id_documento, "titulo_original": doc.titulo_original, 
                         "mime_type": doc.mime_type, "file_size": doc.file_size, "favorito": doc.favorito,
                         "fecha_modificacion": doc.fecha_modificacion, "categoria": doc.categoria,
                         "preview_url": None } # Add other fields as needed by search_results.html
            if doc.mime_type and doc.mime_type.startswith('image/') and local_s3_client:
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
        found_documents = processed_documents


    active_filters_default = {'category_name': 'Any', 'mime_type_name': 'Any', 
                              'modified_name': 'Any time', 'period_year_name': 'Any'}
    return render_template(
        'search_results.html',
        search_term=search_term,
        documents=found_documents, # Now list of dicts, possibly with preview_url
        folders=found_folders,
        current_page='search_results', 
        current_folder_id=None,
        active_filters=active_filters_default
    )
