CREATE TABLE IF NOT EXISTS schema_version (
        version INTEGER PRIMARY KEY
    );

    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        email TEXT DEFAULT '',
        password_hash TEXT DEFAULT '',
        avatar_url TEXT DEFAULT '',
        area TEXT DEFAULT '',
        department_id TEXT DEFAULT '',
        manager_id TEXT DEFAULT '',
        role TEXT DEFAULT 'usuario',
        is_active INTEGER DEFAULT 1,
        last_login TEXT DEFAULT '',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        created_by TEXT DEFAULT '',
        updated_by TEXT DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS departments (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        code TEXT UNIQUE NOT NULL,
        parent_id TEXT DEFAULT '',
        manager_id TEXT DEFAULT '',
        description TEXT DEFAULT '',
        is_active INTEGER DEFAULT 1,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        created_by TEXT DEFAULT '',
        updated_by TEXT DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS roles (
        id TEXT PRIMARY KEY,
        name TEXT UNIQUE NOT NULL,
        display_name TEXT NOT NULL,
        description TEXT DEFAULT '',
        is_active INTEGER DEFAULT 1,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS permissions (
        id TEXT PRIMARY KEY,
        name TEXT UNIQUE NOT NULL,
        module TEXT NOT NULL,
        action TEXT NOT NULL,
        description TEXT DEFAULT '',
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS role_permissions (
        role_id TEXT NOT NULL,
        permission_id TEXT NOT NULL,
        created_at TEXT NOT NULL,
        PRIMARY KEY (role_id, permission_id),
        FOREIGN KEY (role_id) REFERENCES roles(id),
        FOREIGN KEY (permission_id) REFERENCES permissions(id)
    );

    CREATE TABLE IF NOT EXISTS user_roles (
        user_id TEXT NOT NULL,
        role_id TEXT NOT NULL,
        assigned_at TEXT NOT NULL,
        assigned_by TEXT DEFAULT '',
        PRIMARY KEY (user_id, role_id),
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (role_id) REFERENCES roles(id)
    );

    CREATE TABLE IF NOT EXISTS sessions (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        token TEXT UNIQUE NOT NULL,
        ip_address TEXT DEFAULT '',
        user_agent TEXT DEFAULT '',
        expires_at TEXT NOT NULL,
        created_at TEXT NOT NULL,
        is_active INTEGER DEFAULT 1,
        FOREIGN KEY (user_id) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS projects (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT DEFAULT '',
        status TEXT DEFAULT 'planeacion',
        priority TEXT DEFAULT 'media',
        owner_id TEXT DEFAULT '',
        department_id TEXT DEFAULT '',
        start_date TEXT DEFAULT '',
        end_date TEXT DEFAULT '',
        progress INTEGER DEFAULT 0,
        tags TEXT DEFAULT '',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        created_by TEXT DEFAULT '',
        updated_by TEXT DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS tasks (
        id TEXT PRIMARY KEY,
        project_id TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT DEFAULT '',
        status TEXT DEFAULT 'pendiente',
        priority TEXT DEFAULT 'media',
        assignee_id TEXT DEFAULT '',
        due_date TEXT DEFAULT '',
        estimated_hours REAL DEFAULT 0,
        actual_hours REAL DEFAULT 0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        created_by TEXT DEFAULT '',
        updated_by TEXT DEFAULT '',
        FOREIGN KEY (project_id) REFERENCES projects(id)
    );

    CREATE TABLE IF NOT EXISTS requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        request_type TEXT NOT NULL,
        title TEXT DEFAULT '',
        description TEXT DEFAULT '',
        area TEXT DEFAULT '',
        priority TEXT DEFAULT 'media',
        status TEXT DEFAULT 'enviada',
        assigned_to TEXT DEFAULT '',
        workflow_state TEXT DEFAULT 'nueva',
        frequency TEXT DEFAULT '',
        tools_used TEXT DEFAULT '',
        steps TEXT DEFAULT '',
        resolution_notes TEXT DEFAULT '',
        resolved_at TEXT DEFAULT '',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        created_by TEXT DEFAULT '',
        updated_by TEXT DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_type TEXT NOT NULL,
        entity_id TEXT NOT NULL,
        user_id TEXT NOT NULL,
        content TEXT NOT NULL,
        parent_id INTEGER DEFAULT 0,
        is_deleted INTEGER DEFAULT 0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        created_by TEXT DEFAULT '',
        updated_by TEXT DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS knowledge_articles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content TEXT DEFAULT '',
        summary TEXT DEFAULT '',
        category TEXT DEFAULT '',
        tags TEXT DEFAULT '',
        status TEXT DEFAULT 'publicado',
        version INTEGER DEFAULT 1,
        author TEXT DEFAULT '',
        plugin_id TEXT DEFAULT '',
        view_count INTEGER DEFAULT 0,
        helpful_count INTEGER DEFAULT 0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        created_by TEXT DEFAULT '',
        updated_by TEXT DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        notification_type TEXT NOT NULL,
        title TEXT NOT NULL,
        message TEXT DEFAULT '',
        action_url TEXT DEFAULT '',
        channel TEXT DEFAULT 'in_app',
        priority TEXT DEFAULT 'normal',
        related_entity_type TEXT DEFAULT '',
        related_entity_id TEXT DEFAULT '',
        read INTEGER DEFAULT 0,
        read_at TEXT DEFAULT '',
        created_at TEXT NOT NULL,
        created_by TEXT DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS executions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plugin_id TEXT NOT NULL,
        user_id TEXT DEFAULT 'default',
        status TEXT DEFAULT 'exito',
        started_at TEXT DEFAULT '',
        finished_at TEXT DEFAULT '',
        duration_seconds REAL DEFAULT 0,
        output_summary TEXT DEFAULT '',
        error_message TEXT DEFAULT '',
        ip_address TEXT DEFAULT '',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS ratings (
        plugin_id TEXT NOT NULL,
        user_id TEXT NOT NULL,
        helpful INTEGER DEFAULT 1,
        time_saved_minutes INTEGER DEFAULT 0,
        comment TEXT DEFAULT '',
        created_at TEXT NOT NULL,
        PRIMARY KEY (plugin_id, user_id)
    );

    CREATE TABLE IF NOT EXISTS favorites (
        user_id TEXT NOT NULL,
        plugin_id TEXT NOT NULL,
        created_at TEXT NOT NULL,
        PRIMARY KEY (user_id, plugin_id)
    );

    CREATE TABLE IF NOT EXISTS recent_usage (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        plugin_id TEXT NOT NULL,
        used_at TEXT NOT NULL,
        duration_seconds REAL DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS searches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        query TEXT NOT NULL,
        results_count INTEGER DEFAULT 0,
        user_id TEXT DEFAULT 'default',
        session_id TEXT DEFAULT '',
        latency_ms REAL DEFAULT 0,
        searched_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS search_opportunities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        query TEXT NOT NULL,
        results_count INTEGER DEFAULT 0,
        user_id TEXT DEFAULT 'default',
        searched_at TEXT NOT NULL,
        acknowledged INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        action TEXT NOT NULL,
        module TEXT NOT NULL,
        entity_type TEXT DEFAULT '',
        entity_id TEXT DEFAULT '',
        entity_name TEXT DEFAULT '',
        details TEXT DEFAULT '',
        ip_address TEXT DEFAULT '',
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS integrations (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        integration_type TEXT NOT NULL,
        status TEXT DEFAULT 'inactivo',
        config TEXT DEFAULT '',
        description TEXT DEFAULT '',
        last_sync_at TEXT DEFAULT '',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        created_by TEXT DEFAULT '',
        updated_by TEXT DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS tags (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        color TEXT DEFAULT '#FF5503',
        usage_count INTEGER DEFAULT 0,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        title TEXT DEFAULT '',
        content TEXT NOT NULL,
        visibility TEXT DEFAULT 'publico',
        post_type TEXT DEFAULT 'general',
        tags TEXT DEFAULT '',
        likes_count INTEGER DEFAULT 0,
        comments_count INTEGER DEFAULT 0,
        is_pinned INTEGER DEFAULT 0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        created_by TEXT DEFAULT '',
        updated_by TEXT DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS post_likes (
        post_id INTEGER NOT NULL,
        user_id TEXT NOT NULL,
        created_at TEXT NOT NULL,
        PRIMARY KEY (post_id, user_id),
        FOREIGN KEY (post_id) REFERENCES posts(id)
    );

    CREATE TABLE IF NOT EXISTS sla_policies (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        priority TEXT NOT NULL,
        response_hours INTEGER DEFAULT 24,
        resolution_hours INTEGER DEFAULT 72,
        is_active INTEGER DEFAULT 1,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS incidents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT DEFAULT '',
        severity TEXT DEFAULT 'media',
        status TEXT DEFAULT 'abierto',
        reporter_id TEXT DEFAULT '',
        assignee_id TEXT DEFAULT '',
        related_plugin_id TEXT DEFAULT '',
        related_request_id INTEGER DEFAULT 0,
        resolution TEXT DEFAULT '',
        resolved_at TEXT DEFAULT '',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        created_by TEXT DEFAULT '',
        updated_by TEXT DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS metrics_daily (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        metric_name TEXT NOT NULL,
        metric_value REAL DEFAULT 0,
        dimension TEXT DEFAULT '',
        created_at TEXT NOT NULL,
        UNIQUE(date, metric_name, dimension)
    );

    CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        plugin_id TEXT DEFAULT '',
        user_id TEXT NOT NULL,
        status TEXT DEFAULT 'exitoso',
        report_type TEXT DEFAULT 'general',
        period_start TEXT DEFAULT '',
        period_end TEXT DEFAULT '',
        records_count INTEGER DEFAULT 0,
        result_summary TEXT DEFAULT '',
        observations TEXT DEFAULT '',
        file_path TEXT DEFAULT '',
        file_name TEXT DEFAULT '',
        file_size INTEGER DEFAULT 0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        created_by TEXT DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS app_states (
        plugin_id TEXT PRIMARY KEY,
        state TEXT DEFAULT 'activo',
        failure_count INTEGER DEFAULT 0,
        last_execution_at TEXT DEFAULT '',
        last_update_at TEXT DEFAULT '',
        last_user_id TEXT DEFAULT '',
        paused_by TEXT DEFAULT '',
        paused_at TEXT DEFAULT '',
        pause_reason TEXT DEFAULT '',
        maintenance_message TEXT DEFAULT '',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS failed_executions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plugin_id TEXT NOT NULL,
        user_id TEXT DEFAULT '',
        error_type TEXT DEFAULT '',
        error_message TEXT DEFAULT '',
        severity TEXT DEFAULT 'media',
        status TEXT DEFAULT 'abierto',
        assignee_id TEXT DEFAULT '',
        resolution TEXT DEFAULT '',
        resolved_at TEXT DEFAULT '',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS user_favorites (
        user_id TEXT NOT NULL,
        plugin_id TEXT NOT NULL,
        sort_order INTEGER DEFAULT 0,
        created_at TEXT NOT NULL,
        PRIMARY KEY (user_id, plugin_id)
    );

    CREATE TABLE IF NOT EXISTS recent_plugins (
        user_id TEXT NOT NULL,
        plugin_id TEXT NOT NULL,
        accessed_at TEXT NOT NULL,
        access_count INTEGER DEFAULT 1,
        PRIMARY KEY (user_id, plugin_id)
    );