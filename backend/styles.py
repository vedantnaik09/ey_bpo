# styles.py
def load_css():
    return """
    <style>
        /* Main theme colors */
        :root {
            --primary-color: #00C853;
            --secondary-color: #1E88E5;
            --background-color: #F5F6FA;
            --text-color: #2C3E50;
            --success-color: #00C853;
            --warning-color: #FFA000;
            --danger-color: #D32F2F;
        }

        /* Global styles */
        .stApp {
            background-color: var(--background-color);
        }

        /* Logo and header */
        .logo-header {
            text-align: center;
            margin-bottom: 2rem;
        }

        .company-logo {
            max-width: 200px;
            margin-bottom: 1rem;
        }

        /* Form styling */
        .form-container {
            background: white;
            padding: 2rem;
            border-radius: 15px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }

        .form-title {
            font-size: 1.5rem;
            color: var(--text-color);
            margin-bottom: 1.5rem;
            text-align: center;
            font-weight: 600;
        }

        /* Metric cards */
        .metric-card {
            background: white;
            padding: 1.5rem;
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            text-align: center;
            transition: transform 0.2s;
        }

        .metric-card:hover {
            transform: translateY(-5px);
        }

        .metric-title {
            font-size: 0.9rem;
            color: #666;
            margin-bottom: 0.5rem;
        }

        .metric-value {
            font-size: 1.8rem;
            font-weight: bold;
            color: var(--text-color);
            margin-bottom: 0.5rem;
        }

        .metric-trend {
            font-size: 0.8rem;
            padding: 4px 8px;
            border-radius: 12px;
        }

        .metric-trend.positive {
            background: #E8F5E9;
            color: var(--success-color);
        }

        .metric-trend.negative {
            background: #FEFEFE;
            color: var(--secondary-color);
        }

        /* Admin dashboard */
        .admin-header {
            background: white;
            padding: 1.5rem;
            border-radius: 12px;
            margin-bottom: 2rem;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }

        /* Button styling */
        .stButton button {
            background: linear-gradient(45deg, var(--primary-color), var(--secondary-color));
            color: white;
            border-radius: 25px;
            padding: 0.5rem 2rem;
            border: none;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            transition: transform 0.2s;
        }

        .stButton button:hover {
            transform: translateY(-2px);
        }

        /* Input fields */
        .stTextInput input, .stTextArea textarea {
            border-radius: 8px;
            border: 1px solid #E0E0E0;
            padding: 0.5rem;
            transition: border-color 0.2s;
        }

        .stTextInput input:focus, .stTextArea textarea:focus {
            border-color: var(--primary-color);
            box-shadow: 0 0 0 2px rgba(0,200,83,0.1);
        }
    </style>
    """
