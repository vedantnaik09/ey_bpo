# app.py
import streamlit as st
from database import DatabaseManager
from ai_analyzer import ComplaintAnalyzer
import plotly.graph_objects as go
import pandas as pd
import time
from styles import load_css
from call_agent import resolve
from datetime import datetime, timedelta
import calendar

st.set_page_config(
    page_title="Resolvr",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown(load_css(), unsafe_allow_html=True)

# Initialize database and analyzer
db = DatabaseManager()
analyzer = ComplaintAnalyzer()

def calendar_view():
    st.markdown("### Callback Calendar")
    
    # Date selection
    selected_date = st.date_input("Select Date", datetime.now().date())
    
    # Get callbacks for selected date
    callbacks_df = db.get_scheduled_callbacks(selected_date.strftime('%Y-%m-%d'))
    
    if not callbacks_df.empty:
        # Create time slots
        time_slots = pd.date_range(
            start=f"{selected_date} 09:00",
            end=f"{selected_date} 17:00",
            freq='30min'
        )
        
        # Create calendar grid
        st.markdown("""
            <style>
            .calendar-slot {
                padding: 10px;
                margin: 5px;
                border-radius: 5px;
                background-color: #f0f2f6;
            }
            .calendar-slot.busy {
                background-color: #ff4b4b;
                color: white;
            }
            </style>
        """, unsafe_allow_html=True)
        
        for slot in time_slots:
            slot_time = slot.strftime('%H:%M')
            slot_callbacks = callbacks_df[
                callbacks_df['scheduled_callback'].dt.strftime('%H:%M') == slot_time
            ]
            
            if not slot_callbacks.empty:
                for _, callback in slot_callbacks.iterrows():
                    st.markdown(f"""
                        <div class="calendar-slot busy">
                            {slot_time} - {callback['customer_name']}
                            <br>Phone: {callback['customer_phone_number']}
                            <br>Priority: {callback['priority_score']:.2f}
                        </div>
                    """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                    <div class="calendar-slot">
                        {slot_time} - Available
                    </div>
                """, unsafe_allow_html=True)
    else:
        st.info("No callbacks scheduled for this date.")

def client_interface():
    col1, col2 = st.columns([5, 5])

    with col1:
        st.markdown(f"""
            <div class="form-container">
                <div class="logo-header">
                    <img src="resolvr.jpg" class="company-logo" style="width: 100%; height: auto;">
                </div>
                <div class="form-title">Submit Your Complaint</div>
            </div>
        """, unsafe_allow_html=True)

        with st.form("complaint_form", clear_on_submit=True):
            name = st.text_input("Full Name", placeholder="Enter your name")
            phone = st.text_input("Phone Number", placeholder="Enter your phone number")
            description = st.text_area(
                "Complaint Description",
                height=150,
                placeholder="Please describe your issue in detail..."
            )
            
            submitted = st.form_submit_button("Submit Complaint")

            if submitted:
                if name and phone and description:
                    with st.spinner("Analyzing your complaint..."):
                        sentiment, urgency, politeness, priority = analyzer.analyze_complaint(description)
                        
                        success = db.submit_complaint(
                            name, phone, description,
                            sentiment, urgency, politeness, priority
                        )

                        if success:
                            st.balloons()
                            st.success("Thank you! Your complaint has been registered successfully!")
                            st.info("We will call you back based on the priority of your complaint.")
                        else:
                            st.error("There was an error submitting your complaint. Please try again.")
                else:
                    st.error("Please fill in all required fields.")

def admin_interface():
    st.markdown("""
        <div class="admin-header">
            <h1>Admin Dashboard</h1>
        </div>
    """, unsafe_allow_html=True)

    # Dashboard Metrics
    total, pending, avg_priority = db.get_dashboard_metrics()
    
    
    if st.button("Schedule All Unscheduled Complaints"):
     with st.spinner("Scheduling complaints..."):
        if db.schedule_existing_complaints():
            st.success("Successfully scheduled all unscheduled complaints!")
            time.sleep(1)
            st.experimental_rerun()
        else:
            st.error("Error scheduling complaints. Please try again.")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">Total Cases</div>
                <div class="metric-value">{total}</div>
            </div>
        """, unsafe_allow_html=True)

    with c2:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">Pending Cases</div>
                <div class="metric-value">{pending}</div>
            </div>
        """, unsafe_allow_html=True)

    with c3:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">Avg Priority</div>
                <div class="metric-value">{avg_priority:.2f}</div>
            </div>
        """, unsafe_allow_html=True)

    # Add tabs for different views
    tab1, tab2 = st.tabs(["Complaints", "Calendar"])
    
    with tab1:
        # Filters
        col1, col2, col3 = st.columns(3)
        with col1:
            status_filter = st.selectbox("Status", ["All", "Pending", "Resolved"])
        with col2:
            priority_filter = st.selectbox("Priority", ["All", "High", "Medium", "Low"])
        with col3:
            search = st.text_input("Search", placeholder="Search by name or description...")

        # Get complaints from database
        df = db.get_complaints()

        # Apply filters
        if status_filter != "All":
            df = df[df['status'].str.lower() == status_filter.lower()]

        if priority_filter != "All":
            if priority_filter == "High":
                df = df[df['priority_score'] >= 0.7]
            elif priority_filter == "Medium":
                df = df[(df['priority_score'] >= 0.4) & (df['priority_score'] < 0.7)]
            else:
                df = df[df['priority_score'] < 0.4]

        if search:
            df = df[
                df['customer_name'].str.contains(search, case=False) |
                df['complaint_description'].str.contains(search, case=False)
            ]

        # Display complaints
        for _, row in df.iterrows():
            with st.expander(
                f"#{row['complaint_id']} - {row['customer_name']} "
                f"(Priority: {row['priority_score']:.2f})"
            ):
                st.markdown(f"""
                    **Phone:** {row['customer_phone_number']}  
                    **Status:** {row['status']}  
                    **Description:** {row['complaint_description']}  
                    **Created:** {row['created_at']}
                    **Scheduled Callback:** {row['scheduled_callback'] if pd.notna(row['scheduled_callback']) else 'Not scheduled'}
                """)

                col1, col2 = st.columns(2)
                with col1:
                    if row['status'] != 'resolved':
                        if st.button("Resolve", key=f"resolve_{row['complaint_id']}"):
                            resolve(row['customer_phone_number'],row['complaint_description'])
                            if db.resolve_complaint(row['complaint_id']):
                                st.success("Complaint resolved successfully!")
                                time.sleep(1)
                                st.experimental_rerun()
                
                with col2:
                    if row['status'] != 'resolved':
                        callback_time = st.time_input("Schedule Callback", key=f"time_{row['complaint_id']}")
                        callback_date = st.date_input("Date", key=f"date_{row['complaint_id']}")
                        if st.button("Schedule", key=f"schedule_{row['complaint_id']}"):
                            scheduled_datetime = datetime.combine(callback_date, callback_time)
                            if db.reschedule_callback(row['complaint_id'], scheduled_datetime):
                                st.success("Callback scheduled successfully!")
                                time.sleep(1)
                                st.experimental_rerun()
                            else:
                                st.error("This time slot is already taken. Please choose another time.")

        # Analytics and graphs
        st.markdown("### Analytics")
        priority_distribution = df['priority_score'].value_counts(bins=3, sort=False)
        fig = go.Figure(
            go.Bar(
                x=["Low", "Medium", "High"],
                y=priority_distribution.values,
                marker_color=['green', 'orange', 'red']
            )
        )
        fig.update_layout(
            title="Priority Distribution",
            xaxis_title="Priority",
            yaxis_title="Count",
            template="plotly_white"
        )
        st.plotly_chart(fig, use_container_width=True)

        resolved_status = df['status'].value_counts()
        pie_chart = go.Figure(
            go.Pie(
                labels=resolved_status.index,
                values=resolved_status.values,
                hole=0.4
            )
        )
        pie_chart.update_layout(title="Status Distribution", template="plotly_white")
        st.plotly_chart(pie_chart, use_container_width=True)
    
    with tab2:
        calendar_view()

def main():
    role = st.sidebar.radio("Select Role", ["Client", "Admin"])

    if role == "Client":
        client_interface()
    else:
        admin_interface()

if __name__ == "__main__":
    main()