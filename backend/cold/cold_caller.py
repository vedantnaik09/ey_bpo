import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from auto import run_all
# Configure the Streamlit page
st.set_page_config(
    page_title="RESOLVR Cold Calling Dashboard",
    page_icon="📞",
    layout="wide"
)

# Custom CSS to match RESOLVR's theme
st.markdown("""
    <style>
    .stApp {
        background-color: #0A0B14;
        color: white;
    }
    
    .css-10trblm {
        color: white;
        font-weight: 600;
    }
    
    .css-1d391kg {
        background-color: #0A0B14;
    }
    
    .stButton>button {
        background-color: #7C3AED;
        color: white;
        border: none;
        border-radius: 4px;
        padding: 0.5rem 1rem;
    }
    
    .stButton>button:hover {
        background-color: #6D28D9;
    }
    
    .css-1cpxqw2 {
        background-color: #1E293B;
        border: 1px solid #374151;
        border-radius: 4px;
    }
    
    [data-testid="stMetricValue"] {
        color: white;
    }

    .contact-card {
        background-color: #1E293B;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
    }

    .status-icon {
        font-size: 1.2rem;
        margin-right: 0.5rem;
    }

    .green-tick::before {
        content: '✅';
    }

    .red-cross::before {
        content: '❌';
    }

    .yellow-circle::before {
        content: '🟡';
    }
    </style>
""", unsafe_allow_html=True)

# Function to simulate calling the AI agent
def call_agent(df):
    pending_contacts = df[df['Call Status'] == 'Pending']
    if not pending_contacts.empty:
        first_pending_index = pending_contacts.index[0]
        df.at[first_pending_index, 'Call Status'] = 'In Progress'
        st.write(f"Initiating call for: {df.at[first_pending_index, 'Name']} ({df.at[first_pending_index, 'Phone Number']})")
    return df

# Header
st.title("📞 RESOLVR Cold Calling Dashboard")
st.markdown("View your contacts and call statuses managed by the AI agent")

# File upload
uploaded_file = st.file_uploader("Choose a CSV file", type="csv")

if uploaded_file is not None:
    # Read the CSV file
    df = pd.read_csv(uploaded_file)
    
    # Dashboard metrics
    st.subheader("📊 Campaign Overview")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_contacts = len(df)
        st.metric("Total Contacts", total_contacts)
        
    with col2:
        pending_calls = len(df[df['Call Status'] == 'Pending'])
        st.metric("Pending Calls", pending_calls)
        
    with col3:
        completed_calls = len(df[df['Call Status'] == 'Completed'])
        st.metric("Completed Calls", completed_calls)
        
    with col4:
        in_progress_calls = len(df[df['Call Status'] == 'In Progress'])
        st.metric("Calls In Progress", in_progress_calls)

    # Initiate Call Button
    if st.button("Initiate Calls", key="initiate_calls"):
        run_all()
        st.experimental_rerun()

    # Contact Display Section
    st.subheader("📱 Contact Information")
    
    # Filter contacts
    status_filter = st.selectbox(
        "Filter by Status",
        ['All'] + list(df['Call Status'].unique())
    )
    
    filtered_df = df if status_filter == 'All' else df[df['Call Status'] == status_filter]
    
    # Display contacts with status icons
    for _, row in filtered_df.iterrows():
        status_icon = {
            'called': 'green-tick',
            'Pending': 'red-cross',
            'In Progress': 'yellow-circle'
        }.get(row['Call Status'], '')

        st.markdown(f"""
        <div class="contact-card">
            <h3>
                <span class="status-icon {status_icon}"></span>
                {row['Name']} - {row['Phone Number']}
            </h3>
            <p><strong>Person Info:</strong> {row['Person Info']}</p>
            <p><strong>Call Status:</strong> {row['Call Status']}</p>
            <p><strong>Remarks:</strong> {row['Remarks'] if pd.notna(row['Remarks']) else 'N/A'}</p>
            <p><strong>Next Follow-up Date:</strong> {row['Next Follow-up Date'] if pd.notna(row['Next Follow-up Date']) else 'Not scheduled'}</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Visualizations
    st.subheader("📈 Campaign Analytics")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Call Status Distribution
        status_counts = df['Call Status'].value_counts()
        fig = px.pie(
            values=status_counts.values,
            names=status_counts.index,
            title="Call Status Distribution",
            template="plotly_dark",
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font_color='white'
        )
        st.plotly_chart(fig, use_container_width=True)
        
    with col2:
        # Follow-up Timeline
        if 'Next Follow-up Date' in df.columns:
            follow_up_df = df[df['Next Follow-up Date'].notna()]
            if not follow_up_df.empty:
                follow_up_df['Next Follow-up Date'] = pd.to_datetime(follow_up_df['Next Follow-up Date'])
                fig = px.timeline(
                    follow_up_df,
                    x_start='Next Follow-up Date',
                    y='Name',
                    title="Follow-up Schedule",
                    template="plotly_dark"
                )
                fig.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font_color='white'
                )
                st.plotly_chart(fig, use_container_width=True)

else:
    # Display placeholder when no file is uploaded
    st.info("👆 Upload your contacts CSV file to get started")
    
    # Show sample CSV format
    
