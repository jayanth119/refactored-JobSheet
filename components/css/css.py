CSS = """
<style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Global Styles */
    .main {
        font-family: 'Inter', sans-serif;
    }
    
    /* Header Styles */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        color: white;
        margin-bottom: 2rem;
        box-shadow: 0 10px 30px rgba(102, 126, 234, 0.3);
    }
    
    .main-header h1 {
        margin: 0;
        font-weight: 700;
        font-size: 2.5rem;
    }
    
    .main-header p {
        margin: 0.5rem 0 0 0;
        opacity: 0.9;
        font-size: 1.1rem;
    }
    
    /* Card Styles */
    .metric-card {
        background: white;
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 5px 15px rgba(0,0,0,0.08);
        border: 1px solid #f0f0f0;
        height: 100%;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 25px rgba(0,0,0,0.15);
    }
    
    .metric-number {
        font-size: 2.5rem;
        font-weight: 700;
        color: #2c3e50;
        margin-bottom: 0.5rem;
    }
    
    .metric-label {
        color: #7f8c8d;
        font-size: 0.9rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    /* Job Card Styles */
    .job-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 3px 10px rgba(0,0,0,0.05);
        margin-bottom: 1rem;
        border-left: 4px solid #667eea;
        transition: all 0.2s ease;
    }
    
    .job-card:hover {
        box-shadow: 0 5px 20px rgba(0,0,0,0.1);
        transform: translateX(5px);
    }
    
    .job-title {
        font-weight: 600;
        color: #2c3e50;
        font-size: 1.1rem;
        margin-bottom: 0.5rem;
    }
    
    .job-details {
        color: #7f8c8d;
        font-size: 0.9rem;
        margin-bottom: 0.3rem;
    }
    
    /* Status Styles */
    .status-new { 
        background: #fff3cd;
        color: #856404;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    
    .status-in-progress { 
        background: #d1ecf1;
        color: #0c5460;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    
    .status-completed { 
        background: #d4edda;
        color: #155724;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    
    .status-pending { 
        background: #f8d7da;
        color: #721c24;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    
    /* Sidebar Styles */
    .css-1d391kg {
        background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
    }
    
    /* Login Form Styles */
    .login-container {
        max-width: 450px;
        margin: 3rem auto;
        padding: 3rem;
        background: white;
        border-radius: 20px;
        box-shadow: 0 20px 40px rgba(0,0,0,0.1);
    }
    
    .login-header {
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .login-header h1 {
        color: #2c3e50;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }
    
    .login-header p {
        color: #7f8c8d;
        font-size: 1rem;
    }
    
    /* Button Styles */
    .stButton > button {
        width: 100%;
        border-radius: 10px;
        border: none;
        padding: 0.8rem 1.5rem;
        font-weight: 600;
        font-size: 1rem;
        transition: all 0.2s ease;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
    }
    
    /* Navigation Styles */
    .nav-item {
        padding: 0.8rem 1rem;
        margin: 0.3rem 0;
        border-radius: 10px;
        transition: all 0.2s ease;
        cursor: pointer;
    }
    
    .nav-item:hover {
        background: rgba(255,255,255,0.1);
        transform: translateX(5px);
    }
    
    .nav-item.active {
        background: rgba(255,255,255,0.2);
        border-left: 4px solid white;
    }
    
    /* Chart Container */
    .chart-container {
        background: white;
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 5px 15px rgba(0,0,0,0.08);
        margin-bottom: 1rem;
    }
    
    /* Alert Styles */
    .alert {
        padding: 1rem 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
        font-weight: 500;
    }
    
    .alert-success {
        background: #d4edda;
        color: #155724;
        border-left: 4px solid #28a745;
    }
    
    .alert-error {
        background: #f8d7da;
        color: #721c24;
        border-left: 4px solid #dc3545;
    }
    
    .alert-info {
        background: #d1ecf1;
        color: #0c5460;
        border-left: 4px solid #17a2b8;
    }
    
    /* Tab Styles */
    .stTabs [data-baseweb="tab-list"] {
        gap: 1rem;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 10px;
        padding: 0.8rem 1.5rem;
        font-weight: 600;
    }
    
    /* Form Styles */
    .stTextInput > div > div > input {
        border-radius: 10px;
        border: 2px solid #e9ecef;
        padding: 0.8rem;
        font-size: 1rem;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.2);
    }
    
    .stSelectbox > div > div > select {
        border-radius: 10px;
        border: 2px solid #e9ecef;
        padding: 0.8rem;
    }
    
    /* Professional Table Styles */
    .dataframe {
        border: none !important;
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 5px 15px rgba(0,0,0,0.08);
    }
    
    .dataframe th {
        background: #667eea !important;
        color: white !important;
        font-weight: 600 !important;
        padding: 1rem !important;
    }
    
    .dataframe td {
        padding: 0.8rem 1rem !important;
        border-bottom: 1px solid #f8f9fa !important;
    }
    
    /* Session Info */
    .session-info {
        background: #f8f9fa;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-size: 0.8rem;
        color: #6c757d;
        margin-bottom: 1rem;
    }
</style>
"""