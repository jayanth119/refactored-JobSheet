sliderCss = """
    <style>
        /* Sidebar styling */
        .sidebar .sidebar-content {
            background: linear-gradient(180deg, #1e1e1e 0%, #2a2a2a 100%);
        }
        
        /* Header button styling - make it look like the original header */
        div[data-testid="stButton"] button[key="header_home_btn"] {
           
            color: white !important;
            border: none !important;
            border-radius: 15px !important;
            padding: 1.5rem 1rem !important;
            font-weight: 700 !important;
            font-size: 1.5rem !important;
            text-align: center !important;
            transition: all 0.3s ease !important;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3) !important;
            margin-bottom: 1.5rem !important;
            width: 100% !important;
            white-space: pre-line !important;
            line-height: 1.3 !important;
        }
        
        div[data-testid="stButton"] button[key="header_home_btn"]:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4) !important;
        }
        
        div[data-testid="stButton"] button[key="header_home_btn"]:active {
            transform: translateY(0px) !important;
        }
        
        .sidebar-header h2 {
            color: white !important; 
            margin: 0 !important; 
            font-size: 1.5rem !important;
            font-weight: 700 !important;
        }
        
        .sidebar-header p {
            color: rgba(255,255,255,0.9) !important; 
            margin: 0.5rem 0 0 0 !important; 
            font-size: 0.9rem !important;
            font-weight: 500 !important;
        }
        
        /* Menu item styling */
        .menu-item {
            display: block;
            padding: 1rem 1.2rem;
            margin: 0.5rem 0;
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            color: rgba(255,255,255,0.8) !important;
            text-decoration: none !important;
            transition: all 0.3s ease;
            border: 1px solid rgba(255,255,255,0.1);
            font-weight: 500;
            font-size: 0.95rem;
        }
        
        .menu-item:hover {
            background: rgba(255,255,255,0.1);
            color: white !important;
            transform: translateX(5px);
            border-color: rgba(255,255,255,0.2);
        }
        
        .menu-item.active {
           
            color: white !important;
            border-color: rgba(102, 126, 234, 0.5);
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
        }
        
        .menu-item.active:hover {
            transform: translateX(3px);
        }
        
        /* Role display styling */
        .role-display {
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
            padding: 1rem; 
            border-radius: 12px; 
            text-align: center;
            margin: 1rem 0;
            box-shadow: 0 4px 15px rgba(17, 153, 142, 0.3);
        }
        
        .role-display div {
            color: white !important; 
            font-weight: 600 !important; 
            font-size: 0.95rem !important;
        }
        
        /* Sign out button styling */
        .sign-out-btn {
            background: linear-gradient(135deg, #ff6b6b 0%, #ee5a52 100%) !important;
            color: white !important;
            border: none !important;
            border-radius: 12px !important;
            padding: 0.8rem 1rem !important;
            font-weight: 600 !important;
            font-size: 0.95rem !important;
            transition: all 0.3s ease !important;
            box-shadow: 0 4px 15px rgba(255, 107, 107, 0.3) !important;
        }
        
        .sign-out-btn:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 6px 20px rgba(255, 107, 107, 0.4) !important;
        }
        
        /* Home button styling */
        div[data-testid="stButton"] button[key="header_home"] {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
            color: white !important;
            border: none !important;
            border-radius: 10px !important;
            padding: 0.6rem 1rem !important;
            font-weight: 500 !important;
            font-size: 0.9rem !important;
            margin-bottom: 1rem !important;
        }
        
        /* Session info styling */
        .session-info {
            background: rgba(255,255,255,0.05);
            padding: 0.8rem;
            border-radius: 10px;
            text-align: center;
            color: rgba(255,255,255,0.7) !important;
            font-size: 0.85rem;
            margin-top: 1rem;
            border: 1px solid rgba(255,255,255,0.1);
        }
        
        /* Divider styling */
        .sidebar-divider {
            border: none;
            height: 1px;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
            margin: 1.5rem 0;
        }
    </style>
    """