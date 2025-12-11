import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date
import uuid
import base64
from io import BytesIO, StringIO

# Database Setup
def init_db():
    conn = sqlite3.connect('sales_erp.db', check_same_thread=False)
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        contact_person TEXT,
        address TEXT,
        phone TEXT,
        gstin TEXT,
        email TEXT,
        status TEXT DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        hsn_code TEXT,
        price REAL NOT NULL,
        status TEXT DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        doc_type TEXT NOT NULL,
        doc_number TEXT UNIQUE NOT NULL,
        doc_date DATE,
        customer_id INTEGER,
        customer_name TEXT,
        customer_contact TEXT,
        customer_address TEXT,
        customer_phone TEXT,
        customer_gstin TEXT,
        items_data TEXT,
        subtotal REAL,
        cgst REAL,
        sgst REAL,
        igst REAL,
        total REAL,
        terms_conditions TEXT,
        created_by TEXT,
        status TEXT DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        modified_at TIMESTAMP,
        FOREIGN KEY (customer_id) REFERENCES customers (id)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        doc_id INTEGER,
        doc_number TEXT,
        transaction_type TEXT,
        amount REAL,
        payment_mode TEXT,
        payment_date DATE,
        remarks TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (doc_id) REFERENCES documents (id)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )''')
    
    conn.commit()
    return conn

def get_setting(conn, key, default=''):
    try:
        result = pd.read_sql(f"SELECT value FROM settings WHERE key='{key}'", conn)
        return result.iloc[0]['value'] if not result.empty else default
    except:
        return default

def set_setting(conn, key, value):
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()

if 'conn' not in st.session_state:
    st.session_state.conn = init_db()

conn = st.session_state.conn

# Load company info from database
def load_company_info():
    return {
        'name': get_setting(conn, 'company_name', 'Your Company Name'),
        'address': get_setting(conn, 'company_address', 'Company Address'),
        'phone': get_setting(conn, 'company_phone', '1234567890'),
        'gstin': get_setting(conn, 'company_gstin', '00XXXXX0000X0XX'),
        'invoice_prefix': get_setting(conn, 'invoice_prefix', 'INV'),
        'quotation_prefix': get_setting(conn, 'quotation_prefix', 'QUO'),
        'po_prefix': get_setting(conn, 'po_prefix', 'PO'),
        'created_by': get_setting(conn, 'created_by', 'Admin'),
        'logo': get_setting(conn, 'company_logo', ''),
        'terms': get_setting(conn, 'general_terms', 'Payment due within 30 days.\nGoods once sold will not be taken back.')
    }

# Helper Functions
def get_customers(status='active'):
    return pd.read_sql(f"SELECT * FROM customers WHERE status='{status}' ORDER BY name", conn)

def get_items(status='active'):
    return pd.read_sql(f"SELECT * FROM items WHERE status='{status}' ORDER BY name", conn)

def get_documents(doc_type=None):
    query = "SELECT * FROM documents WHERE status!='deleted'"
    if doc_type:
        query += f" AND doc_type='{doc_type}'"
    query += " ORDER BY created_at DESC"
    return pd.read_sql(query, conn)

def get_payments():
    return pd.read_sql("SELECT * FROM payments ORDER BY payment_date DESC", conn)

def save_customer(name, contact, address, phone, gstin, email):
    c = conn.cursor()
    c.execute("INSERT INTO customers (name, contact_person, address, phone, gstin, email) VALUES (?, ?, ?, ?, ?, ?)",
              (name, contact, address, phone, gstin, email))
    conn.commit()

def update_customer(cid, name, contact, address, phone, gstin, email, status):
    c = conn.cursor()
    c.execute("UPDATE customers SET name=?, contact_person=?, address=?, phone=?, gstin=?, email=?, status=? WHERE id=?",
              (name, contact, address, phone, gstin, email, status, cid))
    conn.commit()

def save_item(name, desc, hsn, price):
    c = conn.cursor()
    c.execute("INSERT INTO items (name, description, hsn_code, price) VALUES (?, ?, ?, ?)",
              (name, desc, hsn, price))
    conn.commit()

def update_item(iid, name, desc, hsn, price, status):
    c = conn.cursor()
    c.execute("UPDATE items SET name=?, description=?, hsn_code=?, price=?, status=? WHERE id=?",
              (name, desc, hsn, price, status, iid))
    conn.commit()

def save_document(doc_type, doc_number, doc_date, customer_id, customer_name, customer_contact,
                  customer_address, customer_phone, customer_gstin, items_data, subtotal, 
                  cgst, sgst, igst, total, terms, created_by):
    c = conn.cursor()
    c.execute("""INSERT INTO documents (doc_type, doc_number, doc_date, customer_id, customer_name, 
                 customer_contact, customer_address, customer_phone, customer_gstin, items_data, 
                 subtotal, cgst, sgst, igst, total, terms_conditions, created_by) 
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
              (doc_type, doc_number, doc_date, customer_id, customer_name, customer_contact,
               customer_address, customer_phone, customer_gstin, items_data, subtotal, 
               cgst, sgst, igst, total, terms, created_by))
    conn.commit()
    return c.lastrowid

def update_document_status(doc_id, status):
    c = conn.cursor()
    c.execute("UPDATE documents SET status=?, modified_at=CURRENT_TIMESTAMP WHERE id=?", 
              (status, doc_id))
    conn.commit()

def delete_document(doc_id):
    c = conn.cursor()
    c.execute("UPDATE documents SET status='deleted' WHERE id=?", (doc_id,))
    conn.commit()

def save_payment(doc_id, doc_number, trans_type, amount, mode, pay_date, remarks):
    c = conn.cursor()
    c.execute("""INSERT INTO payments (doc_id, doc_number, transaction_type, amount, 
                 payment_mode, payment_date, remarks) VALUES (?, ?, ?, ?, ?, ?, ?)""",
              (doc_id, doc_number, trans_type, amount, mode, pay_date, remarks))
    conn.commit()

def generate_doc_html(doc_type, doc_number, doc_date, company_info, customer_info, items, 
                      subtotal, cgst, sgst, igst, total, terms, general_terms):
    rows = ""
    for item in items:
        rows += f"""<tr>
            <td>{item['name']}<br><small style="color:#666;">{item['description']}</small></td>
            <td>{item['hsn']}</td>
            <td>{item['qty']}</td>
            <td>₹{item['price']:.2f}</td>
            <td>₹{item['total']:.2f}</td>
        </tr>"""
    
    gst_rows = ""
    if cgst > 0:
        gst_rows = f"""
        <tr><td colspan="4" align="right"><strong>CGST (9%):</strong></td><td>₹{cgst:.2f}</td></tr>
        <tr><td colspan="4" align="right"><strong>SGST (9%):</strong></td><td>₹{sgst:.2f}</td></tr>
        """
    else:
        gst_rows = f"""
        <tr><td colspan="4" align="right"><strong>IGST (18%):</strong></td><td>₹{igst:.2f}</td></tr>
        """
    
    logo_html = f'<img src="{company_info["logo"]}" style="max-height:80px; max-width:150px;">' if company_info.get('logo') else ""
    
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 30px; line-height: 1.4; }}
            .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 3px solid #333; padding-bottom: 15px; }}
            .company {{ font-size: 26px; font-weight: bold; color: #333; }}
            .company-details {{ font-size: 13px; color: #555; margin-top: 5px; }}
            .doc-type {{ font-size: 22px; color: #0066cc; margin: 15px 0; font-weight: bold; }}
            .info-section {{ margin-top: 20px; display: flex; justify-content: space-between; }}
            .box {{ width: 48%; border: 1px solid #ddd; padding: 12px; background: #f9f9f9; }}
            .box strong {{ color: #333; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th, td {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
            th {{ background: #4CAF50; color: white; font-weight: bold; }}
            .total-row {{ background: #e8f5e9; font-weight: bold; font-size: 16px; }}
            .terms {{ margin-top: 25px; padding: 15px; background: #fffbf0; border: 1px solid #f0e68c; }}
            .terms h4 {{ margin: 0 0 10px 0; color: #333; }}
            .footer {{ margin-top: 30px; text-align: center; font-size: 12px; color: #777; padding-top: 15px; border-top: 1px solid #ddd; }}
            .signature {{ margin-top: 40px; text-align: right; }}
        </style>
    </head>
    <body>
        <div class="header">
            <div>
                <div class="company">{company_info['name']}</div>
                <div class="company-details">
                    {company_info['address'].replace(chr(10), '<br>')}<br>
                    GSTIN: {company_info['gstin']} | Phone: {company_info['phone']}
                </div>
            </div>
            <div>{logo_html}</div>
        </div>
        
        <div class="doc-type">{doc_type}</div>
        
        <div style="margin: 15px 0;">
            <strong>{doc_type} No:</strong> {doc_number} | <strong>Date:</strong> {doc_date} | <strong>Created By:</strong> {company_info['created_by']}
        </div>
        
        <div class="info-section">
            <div class="box">
                <strong>Bill To:</strong><br>
                <strong>{customer_info['name']}</strong><br>
                {f"Attn: {customer_info['contact']}<br>" if customer_info.get('contact') else ""}
                {customer_info['address'].replace(chr(10), '<br>')}<br>
                Phone: {customer_info['phone']}<br>
                GSTIN: {customer_info['gstin']}
            </div>
            <div class="box">
                <strong>Terms & Conditions:</strong><br>
                {terms.replace(chr(10), '<br>')}
            </div>
        </div>
        
        <table>
            <thead>
                <tr>
                    <th>Item & Description</th>
                    <th>HSN/SAC</th>
                    <th>Qty</th>
                    <th>Rate</th>
                    <th>Amount</th>
                </tr>
            </thead>
            <tbody>
                {rows}
                <tr><td colspan="4" align="right"><strong>Subtotal:</strong></td><td>₹{subtotal:.2f}</td></tr>
                {gst_rows}
                <tr class="total-row"><td colspan="4" align="right"><strong>Grand Total:</strong></td><td>₹{total:.2f}</td></tr>
            </tbody>
        </table>
        
        <div class="terms">
            <h4>General Terms & Conditions:</h4>
            {general_terms.replace(chr(10), '<br>')}
        </div>
        
        <div class="signature">
            <p style="margin-bottom: 50px;">For <strong>{company_info['name']}</strong></p>
            <p style="border-top: 1px solid #000; display: inline-block; padding-top: 5px; min-width: 200px;">Authorized Signatory</p>
        </div>
        
        <div class="footer">
            <p>This is a computer-generated document.</p>
            <p><strong>Powered by Sales Pipeline ERP System</strong></p>
        </div>
    </body>
    </html>
    """
    return html

def html_to_pdf_download(html_content, filename):
    try:
        from weasyprint import HTML
        pdf = HTML(string=html_content).write_pdf()
        return pdf
    except:
        st.error("PDF generation requires WeasyPrint. Install: pip install weasyprint")
        return None

# Page Configuration
st.set_page_config(page_title="Sales Pipeline ERP", layout="wide", initial_sidebar_state="expanded")

# Sidebar Navigation
st.sidebar.title("📊 Sales ERP System")
menu = st.sidebar.radio("Navigation", [
    "🏠 Dashboard",
    "📝 Create Document",
    "👥 Customer Register",
    "📦 Item Register",
    "💰 Payment Entry",
    "📋 Document Reports",
    "💳 Payment Reports",
    "⚙️ Settings"
])

# Settings
if menu == "⚙️ Settings":
    st.title("⚙️ Company Settings")
    
    company_info = load_company_info()
    
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("Company Name*", company_info['name'])
        address = st.text_area("Address*", company_info['address'])
        phone = st.text_input("Phone*", company_info['phone'])
        gstin = st.text_input("GSTIN*", company_info['gstin'])
    
    with col2:
        created_by = st.text_input("Default Created By", company_info['created_by'])
        invoice_prefix = st.text_input("Invoice Prefix", company_info['invoice_prefix'])
        quotation_prefix = st.text_input("Quotation Prefix", company_info['quotation_prefix'])
        po_prefix = st.text_input("Purchase Order Prefix", company_info['po_prefix'])
    
    st.subheader("Company Logo")
    logo_file = st.file_uploader("Upload Logo (PNG/JPG)", type=['png', 'jpg', 'jpeg'])
    if logo_file:
        logo_bytes = logo_file.read()
        logo_b64 = base64.b64encode(logo_bytes).decode()
        logo_url = f"data:image/png;base64,{logo_b64}"
        st.image(logo_url, width=150)
    else:
        logo_url = company_info['logo']
        if logo_url:
            st.image(logo_url, width=150)
    
    st.subheader("General Terms & Conditions")
    terms = st.text_area("Terms (shown at bottom of all documents)", company_info['terms'], height=100)
    
    if st.button("💾 Save Settings", type="primary"):
        set_setting(conn, 'company_name', name)
        set_setting(conn, 'company_address', address)
        set_setting(conn, 'company_phone', phone)
        set_setting(conn, 'company_gstin', gstin)
        set_setting(conn, 'created_by', created_by)
        set_setting(conn, 'invoice_prefix', invoice_prefix)
        set_setting(conn, 'quotation_prefix', quotation_prefix)
        set_setting(conn, 'po_prefix', po_prefix)
        set_setting(conn, 'general_terms', terms)
        if logo_file:
            set_setting(conn, 'company_logo', logo_url)
        st.success("✅ Settings saved successfully!")
        st.rerun()

# Dashboard
elif menu == "🏠 Dashboard":
    st.title("🏠 Dashboard")
    
    company_info = load_company_info()
    if company_info['name'] == 'Your Company Name':
        st.warning("⚠️ Please configure company settings first!")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        customer_count = pd.read_sql("SELECT COUNT(*) as count FROM customers WHERE status='active'", conn).iloc[0]['count']
        st.metric("Active Customers", customer_count)
    
    with col2:
        item_count = pd.read_sql("SELECT COUNT(*) as count FROM items WHERE status='active'", conn).iloc[0]['count']
        st.metric("Active Items", item_count)
    
    with col3:
        invoice_count = pd.read_sql("SELECT COUNT(*) as count FROM documents WHERE doc_type='Invoice' AND status='active'", conn).iloc[0]['count']
        st.metric("Invoices", invoice_count)
    
    with col4:
        total_revenue = pd.read_sql("SELECT COALESCE(SUM(total), 0) as total FROM documents WHERE doc_type='Invoice' AND status='active'", conn).iloc[0]['total']
        st.metric("Total Revenue", f"₹{total_revenue:,.2f}")
    
    st.subheader("Recent Documents")
    recent_docs = get_documents()
    if not recent_docs.empty:
        st.dataframe(recent_docs[['doc_type', 'doc_number', 'doc_date', 'customer_name', 'total', 'status']].head(10), use_container_width=True)

# Customer Register
elif menu == "👥 Customer Register":
    st.title("👥 Customer Register")
    
    tab1, tab2, tab3 = st.tabs(["📋 View Customers", "➕ Add/Edit Customer", "📥 Import/Export"])
    
    with tab1:
        customers = get_customers()
        if not customers.empty:
            st.dataframe(customers, use_container_width=True)
        else:
            st.info("No customers found.")
    
    with tab2:
        action = st.radio("Action", ["Add New", "Edit Existing"])
        
        if action == "Add New":
            with st.form("add_customer"):
                name = st.text_input("Customer Name*")
                contact = st.text_input("Contact Person Name")
                address = st.text_area("Address")
                phone = st.text_input("Phone")
                gstin = st.text_input("GSTIN")
                email = st.text_input("Email")
                
                if st.form_submit_button("💾 Save Customer"):
                    if name:
                        save_customer(name, contact, address, phone, gstin, email)
                        st.success(f"✅ Customer '{name}' added!")
                        st.rerun()
                    else:
                        st.error("Customer name is required!")
        else:
            customers = get_customers(status='active')
            if not customers.empty:
                selected = st.selectbox("Select Customer", customers['name'].tolist())
                customer = customers[customers['name'] == selected].iloc[0]
                
                with st.form("edit_customer"):
                    name = st.text_input("Customer Name*", customer['name'])
                    contact = st.text_input("Contact Person Name", customer['contact_person'] or '')
                    address = st.text_area("Address", customer['address'] or '')
                    phone = st.text_input("Phone", customer['phone'] or '')
                    gstin = st.text_input("GSTIN", customer['gstin'] or '')
                    email = st.text_input("Email", customer['email'] or '')
                    status = st.selectbox("Status", ["active", "inactive"], index=0 if customer['status']=='active' else 1)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.form_submit_button("💾 Update"):
                            update_customer(customer['id'], name, contact, address, phone, gstin, email, status)
                            st.success("✅ Customer updated!")
                            st.rerun()
                    with col2:
                        if st.form_submit_button("🗑️ Delete"):
                            update_customer(customer['id'], name, contact, address, phone, gstin, email, 'deleted')
                            st.success("✅ Customer deleted!")
                            st.rerun()
    
    with tab3:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("📥 Export")
            customers = pd.read_sql("SELECT * FROM customers WHERE status!='deleted'", conn)
            if not customers.empty:
                csv = customers.to_csv(index=False)
                st.download_button("📥 Download CSV", csv, "customers.csv", "text/csv")
        
        with col2:
            st.subheader("📤 Import")
            uploaded = st.file_uploader("Upload CSV", type=['csv'])
            if uploaded:
                try:
                    df = pd.read_csv(uploaded)
                    c = conn.cursor()
                    for _, row in df.iterrows():
                        try:
                            c.execute("""INSERT INTO customers (name, contact_person, address, phone, gstin, email, status) 
                                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                                    (row.get('name'), row.get('contact_person'), row.get('address'), 
                                     row.get('phone'), row.get('gstin'), row.get('email'), 
                                     row.get('status', 'active')))
                        except:
                            continue
                    conn.commit()
                    st.success(f"✅ Imported {len(df)} customers!")
                    st.dataframe(df)
                except Exception as e:
                    st.error(f"Error: {e}")

# Item Register
elif menu == "📦 Item Register":
    st.title("📦 Item Register")
    
    tab1, tab2, tab3 = st.tabs(["📋 View Items", "➕ Add/Edit Item", "📥 Import/Export"])
    
    with tab1:
        items = get_items()
        if not items.empty:
            st.dataframe(items, use_container_width=True)
    
    with tab2:
        action = st.radio("Action", ["Add New", "Edit Existing"])
        
        if action == "Add New":
            with st.form("add_item"):
                name = st.text_input("Item Name*")
                desc = st.text_area("Description")
                hsn = st.text_input("HSN/SAC Code")
                price = st.number_input("Price*", min_value=0.01, step=0.01)
                
                if st.form_submit_button("💾 Save Item"):
                    if name:
                        save_item(name, desc, hsn, price)
                        st.success(f"✅ Item '{name}' added!")
                        st.rerun()
        else:
            items = get_items(status='active')
            if not items.empty:
                selected = st.selectbox("Select Item", items['name'].tolist())
                item = items[items['name'] == selected].iloc[0]
                
                with st.form("edit_item"):
                    name = st.text_input("Item Name*", item['name'])
                    desc = st.text_area("Description", item['description'] or '')
                    hsn = st.text_input("HSN/SAC Code", item['hsn_code'] or '')
                    price = st.number_input("Price*", min_value=0.01, step=0.01, value=float(item['price']))
                    status = st.selectbox("Status", ["active", "inactive"], index=0 if item['status']=='active' else 1)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.form_submit_button("💾 Update"):
                            update_item(item['id'], name, desc, hsn, price, status)
                            st.success("✅ Item updated!")
                            st.rerun()
                    with col2:
                        if st.form_submit_button("🗑️ Delete"):
                            update_item(item['id'], name, desc, hsn, price, 'deleted')
                            st.success("✅ Item deleted!")
                            st.rerun()
    
    with tab3:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("📥 Export")
            items = pd.read_sql("SELECT * FROM items WHERE status!='deleted'", conn)
            if not items.empty:
                csv = items.to_csv(index=False)
                st.download_button("📥 Download CSV", csv, "items.csv", "text/csv")
        
        with col2:
            st.subheader("📤 Import")
            uploaded = st.file_uploader("Upload CSV", type=['csv'])
            if uploaded:
                try:
                    df = pd.read_csv(uploaded)
                    c = conn.cursor()
                    for _, row in df.iterrows():
                        try:
                            c.execute("""INSERT INTO items (name, description, hsn_code, price, status) 
                                       VALUES (?, ?, ?, ?, ?)""",
                                    (row.get('name'), row.get('description'), row.get('hsn_code'), 
                                     row.get('price'), row.get('status', 'active')))
                        except:
                            continue
                    conn.commit()
                    st.success(f"✅ Imported {len(df)} items!")
                    st.dataframe(df)
                except Exception as e:
                    st.error(f"Error: {e}")

# Create Document
elif menu == "📝 Create Document":
    st.title("📝 Create Document")
    
    company_info = load_company_info()
    if company_info['name'] == 'Your Company Name':
        st.error("❌ Please configure company settings first!")
        st.stop()
    
    doc_type = st.selectbox("Document Type", ["Invoice", "Quotation", "Purchase Order"])
    doc_date = st.date_input("Document Date", date.today())
    
    customers = get_customers()
    if customers.empty:
        st.error("❌ Please add customers first!")
        st.stop()
    
    customer_name = st.selectbox("Select Customer", customers['name'].tolist())
    customer = customers[customers['name'] == customer_name].iloc[0]
    
    col1, col2 = st.columns(2)
    with col1:
        cust_address = st.text_area("Customer Address", customer['address'] or '', height=80)
        cust_phone = st.text_input("Customer Phone", customer['phone'] or '')
    with col2:
        cust_contact = st.text_input("Contact Person", customer['contact_person'] or '')
        cust_gstin = st.text_input("Customer GSTIN", customer['gstin'] or '')
    
    terms_conditions = st.text_area("Terms & Conditions", "Payment due in 30 days", height=80)
    
    st.subheader("📦 Add Items")
    
    items_data = get_items()
    if items_data.empty:
        st.error("❌ Please add items first!")
        st.stop()
    
    if 'doc_items' not in st.session_state:
        st.session_state.doc_items = []
    
    if 'adding_item' not in st.session_state:
        st.session_state.adding_item = True
    
    if st.session_state.adding_item:
        with st.form("add_item_form", clear_on_submit=True):
            col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
            with col1:
                item_name = st.selectbox("Select Item", items_data['name'].tolist())
                item = items_data[items_data['name'] == item_name].iloc[0]
            with col2:
                qty = st.number_input("Quantity", min_value=1, value=1)
            with col3:
                price = st.number_input("Rate", min_value=0.01, step=0.01, value=float(item['price']))
            with col4:
                st.write("")
                st.write("")
                add_btn = st.form_submit_button("➕ Add", use_container_width=True)
            
            item_desc = st.text_area("Description", item['description'] or '', height=60)
            
            if add_btn:
                st.session_state.doc_items.append({
                    'name': item['name'],
                    'description': item_desc,
                    'hsn': item['hsn_code'] or '',
                    'price': price,
                    'qty': qty,
                    'total': price * qty
                })
                st.rerun()
    
    if st.session_state.doc_items:
        st.subheader("📋 Items in Document")
        for idx, item in enumerate(st.session_state.doc_items):
            col1, col2 = st.columns([5, 1])
            with col1:
                st.write(f"**{item['name']}** | HSN: {item['hsn']} | Qty: {item['qty']} × ₹{item['price']:.2f} = ₹{item['total']:.2f}")
                st.caption(item['description'])
            with col2:
                if st.button("🗑️", key=f"del_{idx}"):
                    st.session_state.doc_items.pop(idx)
                    st.rerun()
        
        subtotal = sum(item['total'] for item in st.session_state.doc_items)
        
        gst_type = st.radio("GST Type", ["CGST/SGST (9% + 9%)", "IGST (18%)"])
        
        if "CGST" in gst_type:
            cgst = sgst = subtotal * 0.09
            igst = 0
            total = subtotal + cgst + sgst
        else:
            igst = subtotal * 0.18
            cgst = sgst = 0
            total = subtotal + igst
        
        st.write("---")
        col1, col2 = st.columns([3, 1])
        with col2:
            st.write(f"**Subtotal:** ₹{subtotal:.2f}")
            if "CGST" in gst_type:
                st.write(f"**CGST (9%):** ₹{cgst:.2f}")
                st.write(f"**SGST (9%):** ₹{sgst:.2f}")
            else:
                st.write(f"**IGST (18%):** ₹{igst:.2f}")
            st.write(f"### **Total:** ₹{total:.2f}")
        
        if st.button("🚀 Generate Document", type="primary", use_container_width=True):
            prefix_key = f"{doc_type.lower().replace(' ', '_')}_prefix"
            prefix = company_info.get(prefix_key, "DOC")
            doc_number = f"{prefix}-{uuid.uuid4().hex[:8].upper()}"
            
            items_json = str(st.session_state.doc_items)
            
            doc_id = save_document(
                doc_type, doc_number, doc_date, customer['id'], customer['name'], cust_contact,
                cust_address, cust_phone, cust_gstin, items_json, subtotal, 
                cgst, sgst, igst, total, terms_conditions, company_info['created_by']
            )
            
            if doc_type == "Invoice":
                save_payment(doc_id, doc_number, 'debit', total, 'Invoice', doc_date, 'Invoice generated')
            
            html = generate_doc_html(
                doc_type, doc_number, doc_date, company_info,
                {'name': customer['name'], 'contact': cust_contact, 'address': cust_address, 
                 'phone': cust_phone, 'gstin': cust_gstin},
                st.session_state.doc_items, subtotal, cgst, sgst, igst, total, 
                terms_conditions, company_info['terms']
            )
            
            st.success(f"✅ {doc_type} {doc_number} created successfully!")
            
            col1, col2 = st.columns(2)
            with col1:
                st.download_button("📥 Download HTML", html, f"{doc_number}.html", "text/html", use_container_width=True)
            with col2:
                try:
                    from weasyprint import HTML as WPHTML
                    pdf = WPHTML(string=html).write_pdf()
                    st.download_button("📥 Download PDF", pdf, f"{doc_number}.pdf", "application/pdf", use_container_width=True)
                except:
                    st.info("PDF generation requires: pip install weasyprint")
            
            with st.expander("👁️ Preview Document"):
                st.components.v1.html(html, height=800, scrolling=True)
            
            st.session_state.doc_items = []
            st.session_state.adding_item = True
    else:
        st.info("Add items to create document.")

# Payment Entry
elif menu == "💰 Payment Entry":
    st.title("💰 Payment Entry")
    
    invoices = get_documents("Invoice")
    if invoices.empty:
        st.info("No invoices found for payment entry.")
        st.stop()
    
    tab1, tab2 = st.tabs(["➕ Add Payment", "📋 Payment History"])
    
    with tab1:
        with st.form("payment_entry"):
            doc_number = st.selectbox("Select Invoice", invoices['doc_number'].tolist())
            invoice = invoices[invoices['doc_number'] == doc_number].iloc[0]
            
            st.write(f"**Customer:** {invoice['customer_name']}")
            st.write(f"**Total:** ₹{invoice['total']:.2f}")
            
            trans_type = st.selectbox("Transaction Type", ["credit", "debit"])
            amount = st.number_input("Amount", min_value=0.01, step=0.01)
            mode = st.selectbox("Payment Mode", ["Cash", "Bank Transfer", "Cheque", "UPI", "Card", "Other"])
            pay_date = st.date_input("Payment Date", date.today())
            remarks = st.text_area("Remarks")
            
            if st.form_submit_button("💾 Save Payment"):
                save_payment(invoice['id'], doc_number, trans_type, amount, mode, pay_date, remarks)
                st.success(f"✅ Payment of ₹{amount:.2f} recorded!")
                st.rerun()
    
    with tab2:
        payments = get_payments()
        if not payments.empty:
            st.dataframe(payments, use_container_width=True)
            
            total_debit = payments[payments['transaction_type']=='debit']['amount'].sum()
            total_credit = payments[payments['transaction_type']=='credit']['amount'].sum()
            balance = total_debit - total_credit
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Debit", f"₹{total_debit:,.2f}")
            col2.metric("Total Credit", f"₹{total_credit:,.2f}")
            col3.metric("Outstanding", f"₹{balance:,.2f}")

# Document Reports
elif menu == "📋 Document Reports":
    st.title("📋 Document Reports")
    
    tab1, tab2, tab3 = st.tabs(["📊 All Documents", "🔍 Manage Documents", "📥 Import/Export"])
    
    with tab1:
        doc_filter = st.selectbox("Filter by Type", ["All", "Invoice", "Quotation", "Purchase Order"])
        docs = get_documents() if doc_filter == "All" else get_documents(doc_filter)
        
        if not docs.empty:
            st.dataframe(docs[['id', 'doc_type', 'doc_number', 'doc_date', 'customer_name', 'total', 'status', 'created_by']], use_container_width=True)
    
    with tab2:
        docs = get_documents()
        if not docs.empty:
            doc_number = st.selectbox("Select Document", docs['doc_number'].tolist())
            doc = docs[docs['doc_number'] == doc_number].iloc[0]
            
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Type:** {doc['doc_type']}")
                st.write(f"**Date:** {doc['doc_date']}")
                st.write(f"**Customer:** {doc['customer_name']}")
            with col2:
                st.write(f"**Total:** ₹{doc['total']:.2f}")
                st.write(f"**Status:** {doc['status']}")
                st.write(f"**Created By:** {doc['created_by']}")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                if st.button("🖨️ Reprint", use_container_width=True):
                    company_info = load_company_info()
                    items = eval(doc['items_data'])
                    html = generate_doc_html(
                        doc['doc_type'], doc['doc_number'], doc['doc_date'], company_info,
                        {'name': doc['customer_name'], 'contact': doc['customer_contact'],
                         'address': doc['customer_address'], 'phone': doc['customer_phone'], 
                         'gstin': doc['customer_gstin']},
                        items, doc['subtotal'], doc['cgst'], doc['sgst'], doc['igst'], 
                        doc['total'], doc['terms_conditions'], company_info['terms']
                    )
                    st.download_button("📥 Download HTML", html, f"{doc['doc_number']}.html", "text/html")
            
            with col2:
                if st.button("❌ Cancel", use_container_width=True):
                    update_document_status(doc['id'], 'cancelled')
                    st.success("✅ Document cancelled!")
                    st.rerun()
            
            with col3:
                if st.button("🔄 Revise", use_container_width=True):
                    st.info("Create a new document based on this one")
            
            with col4:
                if st.button("🗑️ Delete", use_container_width=True):
                    delete_document(doc['id'])
                    st.success("✅ Document deleted!")
                    st.rerun()
    
    with tab3:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("📥 Export")
            docs = get_documents()
            if not docs.empty:
                csv = docs.to_csv(index=False)
                st.download_button("📥 Download CSV", csv, "documents.csv", "text/csv")
        
        with col2:
            st.subheader("📤 Import")
            st.info("Document import requires careful data mapping. Use export format as template.")

# Payment Reports
elif menu == "💳 Payment Reports":
    st.title("💳 Payment Reports")
    
    tab1, tab2 = st.tabs(["📊 Payment Summary", "📥 Export"])
    
    with tab1:
        payments = get_payments()
        if not payments.empty:
            st.dataframe(payments, use_container_width=True)
            
            col1, col2, col3 = st.columns(3)
            total_debit = payments[payments['transaction_type']=='debit']['amount'].sum()
            total_credit = payments[payments['transaction_type']=='credit']['amount'].sum()
            balance = total_debit - total_credit
            
            col1.metric("Total Debit", f"₹{total_debit:,.2f}")
            col2.metric("Total Credit", f"₹{total_credit:,.2f}")
            col3.metric("Outstanding", f"₹{balance:,.2f}")
    
    with tab2:
        payments = get_payments()
        if not payments.empty:
            csv = payments.to_csv(index=False)
            st.download_button("📥 Download CSV", csv, "payments.csv", "text/csv")