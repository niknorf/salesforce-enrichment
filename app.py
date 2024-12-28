import requests
from simple_salesforce import Salesforce
import streamlit as st

# Move credentials to session state and frontend input
def initialize_credentials():
    if 'sf' not in st.session_state:
        st.session_state.sf = None
    if 'profinder_api_key' not in st.session_state:
        st.session_state.profinder_api_key = None
    if 'profinder_url' not in st.session_state:
        st.session_state.profinder_url = "https://b2b-api-trial.profinder.fi/api/1.0/company/"
    if 'selected_fields' not in st.session_state:
        # Default required fields to be pre-selected
        default_fields = {
            'Name', 'Phone', 'Yhteyshenkilo__c', 'Employee_Count__c', 'AnnualRevenue', 
            'NumberOfEmployees', 'Industry', 'Kasvuluokka__c', 'Website', 'Email__c', 
            'Account_Marketing_Name__c'
        }
        st.session_state.selected_fields = default_fields
    if 'field_mappings' not in st.session_state:
        # Default field mappings
        st.session_state.field_mappings = {
            'Name': 'basic.name',
            'Phone': 'basic.phoneNumber',
            'Yhteyshenkilo__c': 'people.ceo.fullName',
            'Employee_Count__c': 'basic.staffCategory',
            'AnnualRevenue': 'financials.latest.turnover',
            'NumberOfEmployees': 'people.count',
            'Industry': 'basic.industry',
            'Kasvuluokka__c': 'basic.growthClass',
            'Website': 'basic.www',
            'Email__c': 'basic.email',
            'Account_Marketing_Name__c': 'basic.marketingName'
        }
    if 'selected_people' not in st.session_state:
        st.session_state.selected_people = {}
    if 'show_apply_button' not in st.session_state:
        st.session_state.show_apply_button = False

def get_account_fields():
    try:
        # Get field descriptions from Salesforce Account object
        account_desc = st.session_state.sf.Account.describe()
        # Get all field names
        fields = {field['name'] for field in account_desc['fields']}
        return fields
    except Exception as e:
        st.error(f"Failed to fetch fields from Salesforce: {str(e)}")
        return set()

def get_profinder_fields():
    """Get all available Profinder API fields in a hierarchical structure"""
    return {
        'basic': {
            'name': 'Company Name',
            'marketingName': 'Marketing Name',
            'businessId': 'Business ID',
            'businessForm': 'Business Form',
            'founded': 'Founded Date',
            'phoneNumber': 'Phone Number',
            'email': 'Email',
            'www': 'Website',
            'PO_street': 'Street Address',
            'PO_postalCode': 'Postal Code',
            'PO_postalCodeName': 'City',
            'industry': 'Industry',
            'tol2008': 'Industry Code (TOL2008)',
            'turnoverCategory': 'Turnover Category',
            'staffCategory': 'Staff Category',
            'riskClass': 'Risk Class',
            'growthClass': 'Growth Class',
            'address': 'Full Address',
            'authorizationToSign': 'Authorization to Sign',
            'hometown': 'Hometown'
        },
        'financials': {
            'latest.turnover': 'Latest Turnover',
            'latest.turnoverChange': 'Latest Turnover Change %',
            'latest.operatingMargin': 'Latest Operating Margin',
            'latest.operatingProfit': 'Latest Operating Profit',
            'latest.profit': 'Latest Profit',
            'latest.quickRatio': 'Latest Quick Ratio',
            'latest.currentRatio': 'Latest Current Ratio',
            'latest.equity': 'Latest Equity',
            'latest.balanceSheetTotal': 'Latest Balance Sheet Total',
            'latest.staff': 'Latest Staff Count',
            'latest.staffChange': 'Latest Staff Change %',
            'latest.turnoverPerPerson': 'Latest Turnover per Person'
        },
        'offices': {
            'first.name': 'Office Name',
            'first.marketingName': 'Office Marketing Name',
            'first.city': 'Office City'
        },
        'people': {
            'count': 'Number of Employees',
            'ceo.fullName': 'CEO Name',
            'ceo.title': 'CEO Title',
            'ceo.phoneNumberExists': 'CEO Has Phone'
        },
        'eAddresses': {
            'first.id': 'E-invoice ID',
            'first.idType': 'E-invoice ID Type',
            'first.serviceID': 'E-invoice Service ID'
        }
    }

# Function to setup Salesforce connection
def setup_salesforce(username, password, security_token):
    try:
        sf = Salesforce(username=username, password=password, security_token=security_token)
        st.session_state.sf = sf
        return True
    except Exception as e:
        st.error(f"Failed to connect to Salesforce: {str(e)}")
        return False

# Streamlit UI - Main title
st.title("Salesforce Account Data Enrichment")

# Initialize session state
initialize_credentials()

# Credentials input section
with st.sidebar:
    st.header("Credentials")
    
    # Salesforce credentials
    st.subheader("Salesforce Credentials")
    sf_username = st.text_input("Salesforce Username")
    sf_password = st.text_input("Salesforce Password", type="password")
    sf_token = st.text_input("Salesforce Security Token", type="password")
    
    # Profinder credentials and environment
    st.subheader("Profinder Credentials")
    profinder_env = st.selectbox(
        "Environment",
        options=["trial", "production"],
        format_func=lambda x: x.capitalize(),
        key="profinder_env"
    )
    
    # Set Profinder URL based on environment
    profinder_urls = {
        "trial": "https://b2b-api-trial.profinder.fi/api/1.0/company/",
        "production": "https://b2b.profinder.fi/api/1.0/company/"
    }
    st.session_state.profinder_url = profinder_urls[profinder_env]
    
    profinder_key = st.text_input("Profinder API Key")
    
    if st.button("Connect"):
        if sf_username and sf_password and sf_token:
            if setup_salesforce(sf_username, sf_password, sf_token):
                st.session_state.profinder_api_key = profinder_key
                st.success("Successfully connected to Salesforce!")
        else:
            st.error("Please fill in all Salesforce credentials")

# Rest of the application logic
if st.session_state.sf and st.session_state.profinder_api_key:
    # Field selection section
    st.header("Field Selection")
    available_fields = get_account_fields()
    
    if available_fields:
        st.write("Select fields to check and enrich:")
        cols = st.columns(3)
        field_checkboxes = {}
        
        for i, field in enumerate(sorted(available_fields)):
            col_idx = i % 3
            with cols[col_idx]:
                # Check if field was previously selected or is in default fields
                is_selected = field in st.session_state.selected_fields
                field_checkboxes[field] = st.checkbox(
                    field, 
                    value=is_selected,
                    key=f"field_{field}"
                )
        
        # Update selected fields based on checkboxes
        st.session_state.selected_fields = {
            field for field, selected in field_checkboxes.items() if selected
        }
        
        if not st.session_state.selected_fields:
            st.warning("Please select at least one field to check.")
            
        # Field mapping section
        if st.session_state.selected_fields:
            st.header("Field Mapping")
            st.write("Map Salesforce fields to Profinder API fields:")
            
            profinder_fields = get_profinder_fields()
            
            # Create two columns for the mapping interface
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.subheader("Salesforce Field")
            with col2:
                st.subheader("Profinder Category")
            with col3:
                st.subheader("Profinder Field")
            
            # Create mapping interface for each selected field
            for sf_field in sorted(st.session_state.selected_fields):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.write(sf_field)
                
                # Get current mapping if exists
                current_mapping = st.session_state.field_mappings.get(sf_field, "")
                current_category = ""
                if current_mapping:
                    current_category = current_mapping.split('.')[0]
                
                with col2:
                    # Category selector with unique key
                    categories = [""] + list(profinder_fields.keys())
                    selected_category = st.selectbox(
                        "Category",
                        options=categories,
                        key=f"category_select_{sf_field}",  # Make key unique with field name
                        index=categories.index(current_category) if current_category in categories else 0,
                        label_visibility="collapsed"
                    )
                
                with col3:
                    # Field selector based on category with unique key
                    if selected_category:
                        category_fields = profinder_fields[selected_category]
                        field_options = [""] + [f"{selected_category}.{field}" for field in category_fields.keys()]
                        field_labels = {f"{selected_category}.{k}": v for k, v in category_fields.items()}
                        field_labels[""] = "Select a field..."
                        
                        selected_field = st.selectbox(
                            "Field",
                            options=field_options,
                            format_func=lambda x: field_labels.get(x, x),
                            key=f"field_select_{sf_field}",  # Make key unique with field name
                            index=field_options.index(current_mapping) if current_mapping in field_options else 0,
                            label_visibility="collapsed"
                        )
                        
                        if selected_field:
                            st.session_state.field_mappings[sf_field] = selected_field
                        elif sf_field in st.session_state.field_mappings:
                            del st.session_state.field_mappings[sf_field]
                    else:
                        st.selectbox(
                            "Field",
                            options=[""],
                            key=f"field_disabled_{sf_field}",  # Already unique
                            disabled=True,
                            label_visibility="collapsed"
                        )

    # Update fetch_accounts_with_missing_data to use dynamic fields
    def fetch_accounts_with_missing_data():
        if not st.session_state.selected_fields:
            return []
            
        # Build dynamic query
        fields_str = ", ".join(st.session_state.selected_fields)
        query = f"SELECT Id, {fields_str}, VatNumber__c FROM Account WHERE VatNumber__c != null"
        
        accounts = st.session_state.sf.query(query)
        accounts_with_missing_data = []
        
        for account in accounts['records']:
            missing_fields = [
                field for field in st.session_state.selected_fields 
                if not account.get(field)
            ]
            if missing_fields:
                accounts_with_missing_data.append({
                    'Id': account['Id'],
                    'Name': account.get('Name', ''),
                    'VatNumber__c': account.get('VatNumber__c', ''),
                    'Missing Fields': missing_fields
                })
                
        return accounts_with_missing_data

    def fetch_profinder_data(vat_number):
        try:
            response = requests.get(
                f'{st.session_state.profinder_url}{vat_number}', 
                headers={'User': st.session_state.profinder_api_key}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Error fetching data from Profinder: {str(e)}")
            return None

    def show_person_selector(account_id, vat_number, sf_field, people_data):
        # Create a unique key for this account and field combination
        selection_key = f"{account_id}_{sf_field}"
        
        # Get the list of people
        people_options = [(p['fullName'], p) for p in people_data]
        
        # Try to find CEO automatically
        ceo = next((p for p in people_data if p['title'].lower() == 'toimitusjohtaja'), None)
        
        if ceo:
            st.success(f"Found CEO automatically: {ceo['fullName']}")
            st.session_state.selected_people[selection_key] = ceo
            st.session_state.show_apply_button = True
            return True
        else:
            st.warning("Could not automatically detect CEO. Please select a person:")
            people_names = [p['fullName'] for p in people_data]
            
            # Get current selection if exists
            current_selection = st.session_state.selected_people.get(selection_key)
            default_index = 0
            if current_selection:
                try:
                    default_index = people_names.index(current_selection['fullName'])
                except ValueError:
                    pass
            
            selected_name = st.selectbox(
                "Select person",
                options=people_names,
                key=f"person_select_{selection_key}",
                index=default_index
            )
            
            # Always show current selection if it exists
            if selected_name:
                selected_person = next(p for p in people_data if p['fullName'] == selected_name)
                st.session_state.selected_people[selection_key] = selected_person
                st.session_state.show_apply_button = True
                
                # Show the current selection
                st.info(f"Currently selected: {selected_name}")
                return True
            
            return False

    def enrich_data(account_ids):
        logs = []
        
        # Initialize enrichment state if not exists
        if 'enrichment_started' not in st.session_state:
            st.session_state.enrichment_started = False
            st.session_state.person_selection_state = {}
            st.session_state.selected_accounts = account_ids
        
        # Set enrichment started when the function is called
        if not st.session_state.enrichment_started:
            st.session_state.enrichment_started = True
            st.session_state.selected_accounts = account_ids
        
        # First pass: Show person selectors
        person_selection_needed = False
        all_selections_complete = True
        
        # Create a container for person selectors
        selector_container = st.container()
        
        # Fetch and store all data first
        with selector_container:
            for account_id in st.session_state.selected_accounts:
                account = st.session_state.sf.Account.get(account_id)
                vat_number = account.get('VatNumber__c')
                
                if not vat_number:
                    logs.append(f"No VAT number found for account {account['Name']}")
                    continue
                
                # Only fetch data if not already in session state
                selection_key = f"{account_id}"
                if selection_key not in st.session_state.person_selection_state:
                    data = fetch_profinder_data(vat_number)
                    if not data or not data.get('success'):
                        logs.append(f"Failed to fetch data for account {account['Name']}")
                        continue
                    st.session_state.person_selection_state[selection_key] = {
                        'people_data': data.get('people', []),
                        'account_name': account['Name'],
                        'data': data
                    }
                
                data = st.session_state.person_selection_state[selection_key]['data']
                
                # Check if any field needs CEO selection
                for sf_field, profinder_path in st.session_state.field_mappings.items():
                    if sf_field in st.session_state.selected_fields:
                        parts = profinder_path.split('.', 1)
                        if len(parts) != 2:
                            continue
                            
                        category, field_path = parts
                        if category == 'people' and field_path.startswith('ceo.'):
                            person_selection_needed = True
                            
                            # Show account name as a header
                            st.subheader(f"Select person for {account['Name']}")
                            
                            selection_made = show_person_selector(
                                account_id, 
                                vat_number, 
                                sf_field, 
                                st.session_state.person_selection_state[selection_key]['people_data']
                            )
                            all_selections_complete = all_selections_complete and selection_made
        
        # Show apply button in a separate container
        button_container = st.container()
        with button_container:
            # Show apply button if either no person selection is needed or all selections are complete
            if (not person_selection_needed) or (person_selection_needed and all_selections_complete and st.session_state.show_apply_button):
                st.info("Click 'Apply Enrichment' to update Salesforce.")
                perform_update = st.button("Apply Enrichment", type="primary", key="apply_enrichment_button")
            else:
                perform_update = False
        
        # Only proceed with update if button was clicked
        if perform_update:
            for account_id in st.session_state.selected_accounts:
                account = st.session_state.sf.Account.get(account_id)
                selection_key = f"{account_id}"
                
                if selection_key not in st.session_state.person_selection_state:
                    continue
                    
                data = st.session_state.person_selection_state[selection_key]['data']
                update_data = {}
                
                for sf_field, profinder_path in st.session_state.field_mappings.items():
                    if sf_field not in st.session_state.selected_fields:
                        continue
                        
                    try:
                        parts = profinder_path.split('.', 1)
                        if len(parts) != 2:
                            continue
                            
                        category, field_path = parts
                        value = None
                        
                        if category == 'people':
                            if field_path == 'count':
                                value = len(data.get('people', []))
                            elif field_path.startswith('ceo.'):
                                selection_key = f"{account_id}_{sf_field}"
                                selected_person = st.session_state.selected_people.get(selection_key)
                                if selected_person:
                                    ceo_field = field_path.split('.')[1]
                                    value = selected_person.get(ceo_field)
                        elif category == 'basic':
                            value = data.get('basic', {}).get(field_path)
                        elif category == 'financials' and field_path.startswith('latest.'):
                            if data.get('financials'):
                                latest_year = max(data['financials'].keys(), key=int)
                                financial_field = field_path.split('.')[1]
                                value = data['financials'][latest_year].get(financial_field)
                        elif category == 'offices' and field_path.startswith('first.'):
                            if data.get('offices') and len(data['offices']) > 0:
                                office_field = field_path.split('.')[1]
                                value = data['offices'][0].get(office_field)
                        elif category == 'eAddresses' and field_path.startswith('first.'):
                            if data.get('eAddresses') and len(data['eAddresses']) > 0:
                                eaddress_field = field_path.split('.')[1]
                                value = data['eAddresses'][0].get(eaddress_field)
                        
                        if value is not None:
                            update_data[sf_field] = value
                            
                    except Exception as e:
                        st.error(f"Error extracting {profinder_path}: {str(e)}")
                        continue
                
                if update_data:
                    try:
                        st.session_state.sf.Account.update(account_id, update_data)
                        logs.append(f"Updated Account Name {account['Name']} with data from Profinder.")
                        st.success(f"Successfully updated {account['Name']}")
                        st.write("Updated fields:", update_data)
                    except Exception as e:
                        logs.append(f"Error updating {account['Name']}: {str(e)}")
                        st.error(f"Failed to update {account['Name']}: {str(e)}")
                else:
                    logs.append(f"No matching data found in Profinder for Account {account['Name']}")
            
            # Reset state after successful update
            st.session_state.enrichment_started = False
            st.session_state.person_selection_state = {}
            st.session_state.selected_people = {}
            st.session_state.show_apply_button = False
            st.session_state.selected_accounts = []
        
        return logs

    # Callback function to select all accounts
    def select_all_accounts():
        for account in st.session_state['accounts_with_missing_data']:
            st.session_state[account['Id']] = True

    if st.button("Identify accounts with missing data"):
        accounts_with_missing_data = fetch_accounts_with_missing_data()
        st.session_state['accounts_with_missing_data'] = accounts_with_missing_data

    if 'accounts_with_missing_data' in st.session_state:
        accounts_with_missing_data = st.session_state['accounts_with_missing_data']
        if accounts_with_missing_data:
            st.write("Accounts with missing data:")
            for account in accounts_with_missing_data:
                st.write(f"Account Name: {account['Name']}, Missing Fields: {', '.join(account['Missing Fields'])}")
                account['Select'] = st.checkbox("Select", key=account['Id'])
            
            if st.button("Select All", on_click=select_all_accounts):
                pass
            
            selected_accounts = [account['Id'] for account in accounts_with_missing_data if st.session_state.get(account['Id'])]
            
            # Initialize enrichment state if not exists
            if 'enrichment_in_progress' not in st.session_state:
                st.session_state.enrichment_in_progress = False
            
            if selected_accounts:
                # Show either the start button or the enrichment interface
                if not st.session_state.enrichment_in_progress:
                    if st.button("Enrich from Profinder"):
                        st.session_state.enrichment_in_progress = True
                        st.session_state.selected_accounts = selected_accounts
                        st.rerun()
                
                # If enrichment is in progress, show the enrichment interface
                if st.session_state.enrichment_in_progress:
                    # Add a cancel button
                    col1, col2 = st.columns([1, 6])
                    with col1:
                        if st.button("← Back"):
                            st.session_state.enrichment_in_progress = False
                            st.session_state.person_selection_state = {}
                            st.session_state.selected_people = {}
                            st.session_state.show_apply_button = False
                            st.rerun()
                    
                    # Call enrich_data with the stored selected accounts
                    enrich_data(st.session_state.selected_accounts)
        else:
            st.write("No accounts with missing data found.")

else:
    st.warning("Please enter your credentials in the sidebar and connect before proceeding.")
