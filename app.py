from flask import Flask, request, render_template_string, jsonify
import db
import math

app = Flask(__name__)

# --- HTML COMPONENTS (NO JINJA) ---

def layout(content, title="SIP Admin Portal", active_sidebar="tenants"):
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <script src="https://unpkg.com/htmx.org@1.9.10"></script>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <style>
        .htmx-indicator {{ display: none; }}
        .htmx-request .htmx-indicator {{ display: inline; }}
        .htmx-request.htmx-indicator {{ display: inline; }}
        
        /* Custom Scrollbar */
        ::-webkit-scrollbar {{ width: 6px; }}
        ::-webkit-scrollbar-track {{ background: #f1f1f1; }}
        ::-webkit-scrollbar-thumb {{ background: #cbd5e1; border-radius: 10px; }}
        ::-webkit-scrollbar-thumb:hover {{ background: #94a3b8; }}

        /* Toast Animation */
        @keyframes slideIn {{ from {{ transform: translateX(100%); opacity: 0; }} to {{ transform: translateX(0); opacity: 1; }} }}
        .toast-enter {{ animation: slideIn 0.3s ease-out forwards; }}
    </style>
</head>
<body class="bg-gray-50 text-gray-900 font-sans antialiased">
    <div id="toast-container" class="fixed top-6 right-6 z-[100] flex flex-col gap-3 pointer-events-none"></div>

    <div class="flex h-screen overflow-hidden">
        {sidebar(active_sidebar)}
        <main id="main-content" class="flex-1 overflow-y-auto p-8">
            {content}
        </main>
    </div>
    <div id="dialog-container"></div>

    <script>
        let lastToastMsg = '';
        let lastToastTime = 0;
        function showToast(message, type = 'success') {{
            const now = Date.now();
            if (message === lastToastMsg && (now - lastToastTime) < 500) return;
            lastToastMsg = message;
            lastToastTime = now;

            const container = document.getElementById('toast-container');
            const toast = document.createElement('div');
            const icon = type === 'success' ? 'fa-circle-check' : 'fa-circle-exclamation';
            const bgColor = type === 'success' ? 'bg-green-600' : 'bg-red-600';
            
            toast.className = `pointer-events-auto flex items-center p-4 min-w-[300px] shadow-2xl rounded-xl text-white toast-enter ${{bgColor}}`;
            toast.innerHTML = `
                <i class="fa-solid ${{icon}} text-xl mr-3"></i>
                <div class="flex-1 font-bold text-sm text-white">${{message}}</div>
                <button onclick="this.parentElement.remove()" class="ml-4 opacity-70 hover:opacity-100 transition-opacity">
                    <i class="fa-solid fa-xmark"></i>
                </button>
            `;
            container.appendChild(toast);
            setTimeout(() => {{
                toast.style.opacity = '0';
                toast.style.transform = 'translateX(100%)';
                toast.style.transition = 'all 0.5s ease-in';
                setTimeout(() => toast.remove(), 500);
            }}, 4000);
        }}

        function showConfirm(message, actionUrl, targetId, tenantId) {{
            const container = document.getElementById('dialog-container');
            const dialog = document.createElement('div');
            dialog.id = 'confirm-dialog';
            dialog.className = 'fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm';
            dialog.innerHTML = `
                <div class="bg-white rounded-2xl p-8 max-w-sm w-full shadow-2xl transform transition-all scale-100">
                    <div class="flex flex-col items-center text-center">
                        <div class="w-16 h-16 bg-red-50 text-red-600 rounded-full flex items-center justify-center mb-4 text-2xl">
                            <i class="fa-solid fa-trash-can"></i>
                        </div>
                        <h3 class="text-xl font-bold text-gray-900 mb-2">Are you sure?</h3>
                        <p class="text-gray-500 text-sm mb-8">${{message}}</p>
                        <div class="flex w-full gap-3">
                            <button onclick="document.getElementById('confirm-dialog').remove()" 
                                    class="flex-1 px-4 py-3 bg-gray-100 text-gray-600 font-bold rounded-xl hover:bg-gray-200 transition-all">
                                Cancel
                            </button>
                            <button hx-delete="${{actionUrl}}?tenant_id=${{tenantId}}" hx-target="${{targetId}}" 
                                    hx-on:htmx:after-request="document.getElementById('confirm-dialog').remove(); showToast('Deleted successfully')"
                                    class="flex-1 px-4 py-3 bg-red-600 text-white font-bold rounded-xl hover:bg-red-700 shadow-lg shadow-red-200 transition-all">
                                Yes, Delete
                            </button>
                        </div>
                    </div>
                </div>
            `;
            container.appendChild(dialog);
            htmx.process(dialog);
        }}

        // Versatile Custom Select Helper (Searchable or Simple)
        function initCustomSelect(containerId, options, config = {{}}) {{
            const {{ onSelect, name, placeholder = 'Select option...', searchable = true, defaultValue = '' }} = config;
            const container = document.getElementById(containerId);
            const inputId = containerId + '-input';
            const listId = containerId + '-list';
            const hiddenId = containerId + '-hidden';
            
            // Find default text
            let defaultText = '';
            if (defaultValue) {{
                const found = options.find(o => o.id == defaultValue);
                if (found) defaultText = found.text;
            }}

            container.innerHTML = `
                <div class="relative w-full custom-select-group">
                    <div class="relative">
                        ${{searchable ? `<i class="fa-solid fa-magnifying-glass absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 text-xs"></i>` : ''}}
                        <input type="text" id="${{inputId}}" placeholder="${{placeholder}}" 
                               value="${{defaultText}}"
                               readonly="${{!searchable}}"
                               class="w-full ${{searchable ? 'pl-11' : 'pl-4'}} pr-10 py-2.5 bg-gray-50 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm cursor-pointer transition-all"
                               autocomplete="off">
                        <i class="fa-solid fa-chevron-down absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 text-[10px] pointer-events-none"></i>
                        <input type="hidden" name="${{name}}" id="${{hiddenId}}" value="${{defaultValue}}">
                    </div>
                    <div id="${{listId}}" class="hidden absolute left-0 right-0 top-full mt-1 bg-white border border-gray-200 rounded-lg shadow-xl z-[60] max-h-60 overflow-y-auto">
                        ${{options.map(o => `
                            <div class="px-4 py-2.5 hover:bg-blue-50 cursor-pointer text-sm transition-colors border-b last:border-0 border-gray-50 flex items-center group" 
                                 onclick="selectCustomOption('${{containerId}}', '${{o.id}}', '${{o.text}}', '${{onSelect}}')">
                                <span class="text-gray-700 group-hover:text-blue-700">${{o.text}}</span>
                            </div>
                        `).join('')}}
                    </div>
                </div>
            `;

            const input = document.getElementById(inputId);
            const list = document.getElementById(listId);

            const toggle = () => list.classList.toggle('hidden');
            input.addEventListener('click', toggle);
            
            if (searchable) {{
                input.addEventListener('input', (e) => {{
                    const val = e.target.value.toLowerCase();
                    const items = list.querySelectorAll('div');
                    items.forEach(item => {{
                        const text = item.innerText.toLowerCase();
                        item.style.display = text.includes(val) ? 'block' : 'none';
                    }});
                    list.classList.remove('hidden');
                }});
            }}

            document.addEventListener('click', (e) => {{
                if (!container.contains(e.target)) list.classList.add('hidden');
            }});
        }}

        function selectCustomOption(containerId, id, text, onSelect) {{
            const input = document.getElementById(containerId + '-input');
            const hidden = document.getElementById(containerId + '-hidden');
            const list = document.getElementById(containerId + '-list');
            
            input.value = text;
            hidden.value = id;
            list.classList.add('hidden');
            
            // Trigger onchange logic if it exists (like for Carrier Search Mode)
            if (hidden.name === 'carrier_search_mode') {{
                toggleCarrierFields(id);
            }}
            
            if (onSelect && onSelect !== 'undefined') {{
                htmx.ajax('GET', `${{onSelect}}?rule_id=${{id}}`, '#dynamic-details-view');
            }}
        }}

        // Listen for HTMX events to show toasts from backend (using headers)
        document.addEventListener('htmx:afterOnLoad', function(evt) {{
            const msg = evt.detail.xhr.getResponseHeader('X-Toast-Message');
            const type = evt.detail.xhr.getResponseHeader('X-Toast-Type') || 'success';
            if (msg) showToast(msg, type);
        }});
    </script>
</body>
</html>
"""

def sidebar(active="tenants"):
    items = [
        ("Dashboard", "dashboard", "fa-gauge"),
        ("Tenants", "tenants", "fa-users"),
        ("SIP Rules", "rules", "fa-route"),
        ("Services", "services", "fa-server"),
        ("Logs", "logs", "fa-list-ul"),
    ]
    
    links = ""
    for name, key, icon in items:
        is_active = active == key
        bg = "bg-blue-50 text-blue-600" if is_active else "text-gray-600 hover:bg-gray-100"
        links += f"""
        <a href="/{key}" hx-get="/{key}" hx-target="#main-content" hx-push-url="true" 
           class="flex items-center space-x-3 px-4 py-3 rounded-lg transition-colors {bg}">
            <i class="fa-solid {icon} w-5 text-center"></i>
            <span class="font-medium">{name}</span>
        </a>
        """

    return f"""
    <aside class="w-64 bg-white border-r border-gray-200 flex flex-col h-full">
        <div class="p-6">
            <h1 class="text-xl font-bold text-blue-600 flex items-center">
                <i class="fa-solid fa-signal mr-2"></i> TATA SLC
            </h1>
        </div>
        <nav class="flex-1 px-4 space-y-1">
            {links}
        </nav>
        <div class="p-4 border-t border-gray-100">
            <div class="flex items-center space-x-3 px-2">
                <div class="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center text-xs font-bold">AS</div>
                <div class="text-sm">
                    <p class="font-semibold">Admin User</p>
                    <p class="text-gray-500 text-xs">admin@telecom.net</p>
                </div>
            </div>
        </div>
    </aside>
    """

def tenant_table_partial(search="", page=1):
    per_page = 12
    tenants, total = db.get_tenants(search, page, per_page)
    total_pages = math.ceil(total / per_page)

    rows = ""
    for t in tenants:
        status_color = "bg-green-100 text-green-700" if t['STATUS'] == 'ACTIVE' else "bg-gray-100 text-gray-700"
        rows += f"""
        <tr class="hover:bg-gray-50 cursor-pointer border-b border-gray-100 last:border-0 group" 
            hx-get="/tenant/{t['TENANT_ID']}" hx-target="#main-content" hx-push-url="true">
            <td class="px-6 py-4 font-mono text-xs text-gray-500">{t['TENANT_ID']}</td>
            <td class="px-6 py-4 font-medium text-gray-900">{t['NAME']}</td>
            <td class="px-6 py-4 text-sm text-gray-600">{t['TYPE']}</td>
            <td class="px-6 py-4 text-sm text-gray-600">{t['COUNTRY']}</td>
            <td class="px-6 py-4">
                <span class="px-2 py-1 rounded text-xs font-semibold {status_color}">{t['STATUS']}</span>
            </td>
            <td class="px-6 py-4 text-sm text-gray-500">{t['CREATED_AT'][:10]}</td>
            <td class="px-6 py-4 text-right">
                <i class="fa-solid fa-chevron-right text-gray-300 group-hover:text-blue-500 transition-colors"></i>
            </td>
        </tr>
        """

    if not tenants:
        rows = '<tr><td colspan="7" class="px-6 py-12 text-center text-gray-500 italic">No tenants found matching your search.</td></tr>'

    pagination = ""
    if total_pages > 1:
        prev_disabled = "opacity-50 cursor-not-allowed" if page <= 1 else "hover:bg-gray-100"
        next_disabled = "opacity-50 cursor-not-allowed" if page >= total_pages else "hover:bg-gray-100"
        
        prev_attr = "" if page <= 1 else f'hx-get="/tenants?search={search}&page={page-1}" hx-target="#tenant-table-container"'
        next_attr = "" if page >= total_pages else f'hx-get="/tenants?search={search}&page={page+1}" hx-target="#tenant-table-container"'

        pagination = f"""
        <div class="px-6 py-4 flex items-center justify-between border-t border-gray-200 bg-gray-50/50">
            <div class="text-sm text-gray-500">
                Showing <span class="font-medium">{(page-1)*per_page + 1}</span> to <span class="font-medium">{min(page*per_page, total)}</span> of <span class="font-medium">{total}</span> results
            </div>
            <div class="flex space-x-2">
                <button {prev_attr} class="px-3 py-1 border border-gray-300 rounded text-sm font-medium {prev_disabled}">Previous</button>
                <button {next_attr} class="px-3 py-1 border border-gray-300 rounded text-sm font-medium {next_disabled}">Next</button>
            </div>
        </div>
        """

    return f"""
    <div id="tenant-table-container" class="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <table class="w-full text-left">
            <thead class="bg-gray-50 border-b border-gray-200">
                <tr>
                    <th class="px-6 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">Tenant ID</th>
                    <th class="px-6 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">Name</th>
                    <th class="px-6 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">Type</th>
                    <th class="px-6 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">Country</th>
                    <th class="px-6 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">Status</th>
                    <th class="px-6 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">Created</th>
                    <th class="px-6 py-3"></th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
        {pagination}
    </div>
    """

def tenant_list_content(search="", page=1):
    return f"""
    <div class="max-w-6xl mx-auto">
        <div class="flex justify-between items-center mb-8">
            <div>
                <h2 class="text-2xl font-bold text-gray-900">Tenants</h2>
                <p class="text-gray-500 mt-1">Manage active telecommunication routing tenants.</p>
            </div>
            <button class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-medium shadow-sm transition-all flex items-center">
                <i class="fa-solid fa-plus mr-2 text-sm"></i> New Tenant
            </button>
        </div>

        <div class="mb-6 relative">
            <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <i class="fa-solid fa-magnifying-glass text-gray-400"></i>
            </div>
            <input type="text" name="search" value="{search}" 
                   hx-get="/tenants" hx-trigger="keyup delay:500ms, search" hx-target="#tenant-table-container" hx-swap="outerHTML"
                   class="block w-full pl-10 pr-3 py-3 border border-gray-200 rounded-xl leading-5 bg-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent sm:text-sm shadow-sm" 
                   placeholder="Search by name, ID or country...">
            <div class="htmx-indicator absolute right-3 top-3">
                <i class="fa-solid fa-circle-notch fa-spin text-blue-500"></i>
            </div>
        </div>

        {tenant_table_partial(search, page)}
    </div>
    """

def tenant_details_content(tenant_id):
    t = db.get_tenant(tenant_id)
    if not t:
        return '<div class="text-center py-20 text-red-500 font-bold">Tenant not found.</div>'

    return f"""
    <div class="max-w-7xl mx-auto">
        <nav class="flex mb-6" aria-label="Breadcrumb">
            <ol class="flex items-center space-x-2 text-sm text-gray-500">
                <li><a href="/tenants" hx-get="/tenants" hx-target="#main-content" class="hover:text-blue-600 transition-colors">Tenants</a></li>
                <li><i class="fa-solid fa-chevron-right text-xs"></i></li>
                <li class="text-gray-900 font-medium">{t['NAME']}</li>
            </ol>
        </nav>

        <div class="grid grid-cols-12 gap-8">
            <!-- Left Panel: Info Card -->
            <div class="col-span-4 space-y-6">
                <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                    <div class="flex justify-between items-start mb-6">
                        <div class="w-16 h-16 rounded-lg bg-blue-50 flex items-center justify-center text-blue-600 text-2xl font-bold">
                            {t['NAME'][0]}
                        </div>
                        <button class="text-sm text-blue-600 font-semibold hover:underline">Edit Info</button>
                    </div>
                    <h3 class="text-xl font-bold text-gray-900 mb-1">{t['NAME']}</h3>
                    <p class="text-sm text-gray-500 mb-6 flex items-center font-mono uppercase">
                        <i class="fa-solid fa-hashtag mr-2 text-xs"></i> {t['TENANT_ID']}
                    </p>
                    
                    <div class="space-y-4 pt-6 border-t border-gray-100">
                        <div>
                            <label class="text-xs font-semibold text-gray-400 uppercase tracking-wider">Type</label>
                            <p class="text-sm font-medium text-gray-900 mt-0.5">{t['TYPE']}</p>
                        </div>
                        <div>
                            <label class="text-xs font-semibold text-gray-400 uppercase tracking-wider">Country</label>
                            <p class="text-sm font-medium text-gray-900 mt-0.5 flex items-center">
                                <i class="fa-solid fa-location-dot mr-2 text-gray-300"></i> {t['COUNTRY']}
                            </p>
                        </div>
                        <div>
                            <label class="text-xs font-semibold text-gray-400 uppercase tracking-wider">Status</label>
                            <div class="mt-1">
                                <span class="px-2 py-0.5 rounded text-xs font-semibold bg-green-100 text-green-700">ACTIVE</span>
                            </div>
                        </div>
                        <div>
                            <label class="text-xs font-semibold text-gray-400 uppercase tracking-wider">Onboarding Date</label>
                            <p class="text-sm font-medium text-gray-900 mt-0.5">{t['CREATED_AT']}</p>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Right Panel: Tabs -->
            <div class="col-span-8 bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden flex flex-col">
                <div class="border-b border-gray-200 bg-gray-50/50 flex px-2 pt-2">
                    <button hx-get="/tenant/{tenant_id}/sip-rules" hx-target="#tab-content" 
                            class="px-6 py-3 text-sm font-semibold border-b-2 border-blue-600 text-blue-600">
                        SIP Rules
                    </button>
                    <button hx-get="/tenant/{tenant_id}/services" hx-target="#tab-content" 
                            class="px-6 py-3 text-sm font-semibold border-b-2 border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 transition-all">
                        Cap Rules
                    </button>
            
                </div>
                <div id="tab-content" class="p-0 flex-1">
                    {sip_rules_partial(tenant_id)}
                </div>
            </div>
        </div>
    </div>
    """

def sip_rules_partial(tenant_id):
    rules = db.get_sip_rules_for_tenant(tenant_id)
    print(f"Generating table for {tenant_id}, rule count: {len(rules)}")
    rows = ""
    for r in rules:
        rec_color = "text-red-500" if r['RECORDING_FLAG'] else "text-gray-300"
        
        mode_val = "N/A"
        if r['CARRIER_SEARCH_MODE'] == 'BPARTY':
            mode_val = f"<span class='text-xs text-gray-500 block'>B-Party:</span> {r['B_PARTY_CARRIER_MAPPING_ID']}"
        elif r['CARRIER_SEARCH_MODE'] == 'MSRN':
            mode_val = f"<span class='text-xs text-gray-500 block'>MSRN:</span> {r['MSRN_CARRIER_MAPPING_ID']}"
        elif r['CARRIER_SEARCH_MODE'] == 'DEFAULT':
            mode_val = f"<span class='text-xs text-gray-500 block'>Default:</span> {r['DEFAULT_CARRIER_LIST_ID']}"

        rows += f"""
        <tr class="border-b border-gray-100 last:border-0 hover:bg-gray-50">
            <td class="px-6 py-4 font-mono text-xs font-medium text-gray-900">{r['RULE_ID']}</td>
            <td class="px-6 py-4">
                <p class="text-sm text-gray-900 font-bold">{r['MAPPING_DESC']}</p>
                <p class="text-[10px] text-gray-400 mt-0.5">Rule: {r['MASTER_DESC']}</p>
                <div class="flex space-x-2 mt-2">
                    <span class="text-[10px] uppercase font-bold bg-green-50 px-1 rounded text-green-700">{r['RULE_ACTION']}</span>
                    <span class="text-[10px] uppercase font-bold bg-gray-100 px-1 rounded text-gray-600">{r['CALL_TYPE']}</span>
                    <span class="text-[10px] uppercase font-bold bg-blue-50 px-1 rounded text-blue-600">{r['SERVICE_TYPE']}</span>
                </div>
            </td>
            <td class="px-6 py-4">
                <div class="text-sm font-medium text-gray-700">{r['CARRIER_SEARCH_MODE']}</div>
                <div class="mt-1">{mode_val}</div>
            </td>
            <td class="px-6 py-4 text-center">
                <i class="fa-solid fa-microphone-lines {rec_color} text-lg" title="{'Recording Enabled' if r['RECORDING_FLAG'] else 'Disabled'}"></i>
            </td>
            <td class="px-6 py-4 text-center">
                <div class="flex items-center justify-center space-x-3">
                    <button onclick="document.getElementById('modal')?.remove(); htmx.ajax('GET', '/tenant/{tenant_id}/sip-rule/edit/{r['MAPPING_ID']}', {{target:'body', swap:'beforeend'}})"
                            class="p-1.5 text-gray-400 hover:text-blue-600 transition-colors">
                        <i class="fa-solid fa-pen-to-square"></i>
                    </button>
                    <button onclick="showConfirm('Are you sure you want to remove this rule mapping?', '/sip-rule/{r['MAPPING_ID']}', '#tab-content', '{tenant_id}')"
                            class="p-1.5 text-gray-400 hover:text-red-600 transition-colors">
                        <i class="fa-solid fa-trash-can"></i>
                    </button>
                </div>
            </td>
        </tr>
        """

    if not rules:
        rows = '<tr><td colspan="5" class="px-6 py-20 text-center text-gray-500">No SIP rules configured for this tenant.</td></tr>'

    return f"""
    <div id="sip-rule-table-wrapper" class="flex flex-col h-full">
        <div class="flex justify-between items-center p-6 bg-white sticky top-0">
            <h4 class="font-bold text-gray-900">Tenant Routing Rules</h4>
            <button hx-get="/tenant/{tenant_id}/sip-rule/add" hx-target="body" hx-swap="beforeend" 
                    hx-on:htmx:before-request="document.getElementById('modal')?.remove()"
                    class="text-xs bg-gray-900 text-white px-3 py-2 rounded font-bold hover:bg-black transition-all">
                ADD RULE
            </button>
        </div>
        <div class="overflow-x-auto">
            <table class="w-full text-left">
                <thead class="bg-gray-50/50 border-y border-gray-100">
                    <tr>
                        <th class="px-6 py-3 text-[10px] font-bold text-gray-400 uppercase tracking-widest">Rule ID</th>
                        <th class="px-6 py-3 text-[10px] font-bold text-gray-400 uppercase tracking-widest">Description</th>
                        <th class="px-6 py-3 text-[10px] font-bold text-gray-400 uppercase tracking-widest">Carrier Mapping</th>
                        <th class="px-6 py-3 text-[10px] font-bold text-gray-400 uppercase tracking-widest text-center">Rec</th>
                        <th class="px-6 py-3"></th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
        </div>
    </div>
    """

def sip_rule_modal(tenant_id, error=None, mode="new", mapping_id=None):
    print(f"Opening Modal: Tenant={tenant_id}, Mode={mode}, MappingID={mapping_id}")
    rules = db.get_all_rules()
    services = db.get_all_services()
    
    mapping = None
    if mapping_id:
        mapping = db.get_rule_mapping(mapping_id)
        print(f"Found mapping: {mapping is not None}")
        mode = "existing"

    error_alert = ""
    if error:
        error_alert = f"""
        <div class="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center text-red-700 text-xs">
            <i class="fa-solid fa-triangle-exclamation mr-2 text-base"></i>
            {error}
        </div>
        """

    is_new = mode == "new"
    is_edit = mapping_id is not None
    
    form_action = f"/sip-rule/update/{mapping_id}?tenant_id={tenant_id}" if is_edit else f"/tenant/{tenant_id}/sip-rule"
    title = "Edit SIP Routing Rule" if is_edit else "Add SIP Routing Rule"

    return f"""
    <div id="modal" class="fixed inset-0 z-50 overflow-y-auto" aria-labelledby="modal-title" role="dialog" aria-modal="true">
        <div class="flex items-center justify-center min-h-screen px-4 pt-4 pb-20 text-center sm:block sm:p-0">
            <div class="fixed inset-0 transition-opacity bg-black/40 backdrop-blur-sm" hx-on:click="document.getElementById('modal').remove()"></div>
            <span class="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">&#8203;</span>

            <div class="inline-block align-bottom bg-white rounded-2xl text-left shadow-2xl transform transition-all sm:my-8 sm:align-middle sm:max-w-5xl sm:w-full overflow-hidden">
                <form hx-post="{form_action}" hx-target="#sip-rule-table-wrapper" hx-swap="outerHTML">
                    <div class="bg-white px-8 pt-8 pb-4 max-h-[80vh] overflow-y-auto">
                        <div class="flex justify-between items-center mb-6">
                            <h3 class="text-xl font-bold text-gray-900">{title}</h3>
                            <button type="button" hx-on:click="document.getElementById('modal').remove()" class="text-gray-400 hover:text-gray-500">
                                <i class="fa-solid fa-xmark text-xl"></i>
                            </button>
                        </div>
                        
                        {error_alert}

                        {f'''
                        <div class="flex p-1 bg-gray-100 rounded-xl mb-6 max-w-md">
                            <button type="button" hx-get="/tenant/{tenant_id}/sip-rule/add?mode=new" hx-target="#modal" hx-swap="outerHTML"
                                    class="flex-1 py-2 text-sm font-bold rounded-lg transition-all {'bg-white shadow text-blue-600' if is_new else 'text-gray-500 hover:text-gray-700'}">
                                Create New Rule
                            </button>
                            <button type="button" hx-get="/tenant/{tenant_id}/sip-rule/add?mode=existing" hx-target="#modal" hx-swap="outerHTML"
                                    class="flex-1 py-2 text-sm font-bold rounded-lg transition-all {'bg-white shadow text-blue-600' if not is_new else 'text-gray-500 hover:text-gray-700'}">
                                Select Existing
                            </button>
                        </div>
                        ''' if not is_edit else ''}

                        <input type="hidden" name="form_mode" value="{mode}">

                        <div class="space-y-6">
                            {f'''
                            <div class="grid grid-cols-2 gap-8">
                                <!-- Basic Info Section -->
                                <div class="space-y-4">
                                    <h4 class="text-xs font-bold text-gray-400 uppercase tracking-widest border-b pb-1">Master Rule Definition</h4>
                                    <div>
                                        <label class="block text-xs font-bold text-gray-700 uppercase mb-1">Rule Description</label>
                                        <input type="text" name="master_description" placeholder="Master rule description..." required
                                               class="w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:bg-white transition-all text-sm">
                                    </div>
                                    <div class="grid grid-cols-2 gap-4">
                                        <div>
                                            <label class="block text-xs font-bold text-gray-700 uppercase mb-1">Carrier Search Mode</label>
                                            <div id="carrier-search-mode-container"></div>
                                            <script>
                                                initCustomSelect('carrier-search-mode-container', [
                                                    {{id: 'DEFAULT', text: 'DEFAULT'}},
                                                    {{id: 'BPARTY', text: 'BPARTY'}},
                                                    {{id: 'MSRN', text: 'MSRN'}},
                                                    {{id: 'TENANT', text: 'TENANT'}}
                                                ], {{name: 'carrier_search_mode', searchable: false, defaultValue: 'DEFAULT'}});
                                            </script>
                                        </div>
                                        <div>
                                            <label class="block text-xs font-bold text-gray-700 uppercase mb-1">Recording Flag</label>
                                            <div class="mt-1 flex items-center">
                                                <label class="relative inline-flex items-center cursor-pointer">
                                                    <input type="checkbox" name="recording_flag_toggle" class="sr-only peer">
                                                    <div class="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                                                    <span class="ml-3 text-sm font-medium text-gray-500">Record Call</span>
                                                </label>
                                            </div>
                                        </div>
                                    </div>

                                    <div id="carrier-id-container" class="p-4 bg-gray-50 rounded-xl border border-gray-100">
                                        <div id="field-DEFAULT">
                                            <label class="block text-[10px] font-bold text-blue-600 uppercase mb-1">Default Carrier List ID</label>
                                            <input type="text" name="default_cl_id" placeholder="0" class="w-full px-3 py-2 bg-white border border-gray-200 rounded-lg text-sm">
                                        </div>
                                        <div id="field-BPARTY" class="hidden">
                                            <label class="block text-[10px] font-bold text-blue-600 uppercase mb-1">B-Party Mapping ID</label>
                                            <input type="text" name="b_party_id" placeholder="0" class="w-full px-3 py-2 bg-white border border-gray-200 rounded-lg text-sm">
                                        </div>
                                        <div id="field-MSRN" class="hidden">
                                            <label class="block text-[10px] font-bold text-blue-600 uppercase mb-1">MSRN Mapping ID</label>
                                            <input type="text" name="msrn_id" placeholder="0" class="w-full px-3 py-2 bg-white border border-gray-200 rounded-lg text-sm">
                                        </div>
                                        <div id="field-TENANT" class="hidden">
                                            <label class="block text-[10px] font-bold text-blue-600 uppercase mb-1">Tenant Carrier Mapping ID</label>
                                            <input type="text" name="tenant_carrier_id" placeholder="0" class="w-full px-3 py-2 bg-white border border-gray-200 rounded-lg text-sm">
                                        </div>
                                    </div>
                                </div>

                                <!-- Mapping Section -->
                                <div class="space-y-4 border-l pl-8">
                                    <h4 class="text-xs font-bold text-gray-400 uppercase tracking-widest border-b pb-1">Tenant Mapping Info</h4>
                                    <div>
                                        <label class="block text-xs font-bold text-gray-700 uppercase mb-1">Mapping Description</label>
                                        <input type="text" name="mapping_description" placeholder="Tenant specific name..." required
                                               class="w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm">
                                    </div>
                                    <div class="grid grid-cols-2 gap-4">
                                        <div>
                                            <label class="block text-xs font-bold text-gray-700 uppercase mb-1">Call Type</label>
                                            <div id="call-type-container"></div>
                                            <script>
                                                initCustomSelect('call-type-container', [
                                                    {{id: 'ONNET', text: 'ONNET'}},
                                                    {{id: 'OFFNET', text: 'OFFNET'}},
                                                    {{id: 'ALLCALL', text: 'ALLCALL'}}
                                                ], {{name: 'call_type', searchable: false, placeholder: 'Select type...'}});
                                            </script>
                                        </div>
                                        <div>
                                            <label class="block text-xs font-bold text-gray-700 uppercase mb-1">Service</label>
                                            <div id="service-container"></div>
                                            <script>
                                                initCustomSelect('service-container', [
                                                    {", ".join([f'{{id: "{s["SERVICE_ID"]}", text: "{s["SERVICE_TYPE"]}"}}' for s in services if s["SERVICE_TYPE"] in ["MO", "MT"]])}
                                                ], {{name: 'service_id', searchable: false, defaultValue: 'MO'}});
                                            </script>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            ''' if is_new else f'''
                            <div class="grid grid-cols-2 gap-8">
                                <div class="space-y-4">
                                    <h4 class="text-xs font-bold text-gray-400 uppercase tracking-widest border-b pb-1">Selection</h4>
                                    <div>
                                        <label class="block text-sm font-bold text-gray-700 mb-2">Search Rule Master</label>
                                        <div id="rule-search-container"></div>
                                        <script>
                                            initCustomSelect('rule-search-container', [
                                                {", ".join([f'{{id: "{r["RULE_ID"]}", text: "{r["DESCRIPTION"]}"}}' for r in rules])}
                                            ], {{
                                                name: 'rule_id', 
                                                onSelect: '/rule/details/partial', 
                                                placeholder: 'Search rule by ID or description...',
                                                defaultValue: '{mapping['RULE_ID'] if mapping else ''}'
                                            }});
                                        </script>
                                    </div>
                                    <div id="dynamic-details-view" class="p-4 bg-blue-50/50 rounded-xl border border-blue-100 min-h-[140px] flex items-center justify-center text-center">
                                        {rule_details_partial(mapping['RULE_ID']) if mapping else '<span class="text-xs text-blue-400 italic">Search and select a rule to preview configuration</span>'}
                                    </div>
                                </div>
                                <div class="space-y-4 border-l pl-8">
                                    <h4 class="text-xs font-bold text-gray-400 uppercase tracking-widest border-b pb-1">Tenant Mapping Info</h4>
                                    <div>
                                        <label class="block text-xs font-bold text-gray-700 uppercase mb-1">Mapping Description</label>
                                        <input type="text" name="mapping_description" value="{mapping['DESCRIPTION'] if mapping else ''}" placeholder="Tenant specific name..." required
                                               class="w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm">
                                    </div>
                                    <div class="grid grid-cols-2 gap-4">
                                        <div>
                                            <label class="block text-xs font-bold text-gray-700 uppercase mb-1">Call Type</label>
                                            <div id="existing-call-type-container"></div>
                                            <script>
                                                initCustomSelect('existing-call-type-container', [
                                                    {{id: 'ONNET', text: 'ONNET'}},
                                                    {{id: 'OFFNET', text: 'OFFNET'}},
                                                    {{id: 'ALLCALL', text: 'ALLCALL'}}
                                                ], {{name: 'call_type', searchable: false, placeholder: 'Select type...', defaultValue: '{mapping['CALL_TYPE'] if mapping else ''}'}});
                                            </script>
                                        </div>
                                        <div>
                                            <label class="block text-xs font-bold text-gray-700 uppercase mb-1">Service</label>
                                            <div id="existing-service-container"></div>
                                            <script>
                                                initCustomSelect('existing-service-container', [
                                                    {", ".join([f'{{id: "{s["SERVICE_ID"]}", text: "{s["SERVICE_TYPE"]}"}}' for s in services if s["SERVICE_TYPE"] in ["MO", "MT"]])}
                                                ], {{name: 'service_id', searchable: false, defaultValue: '{mapping['SERVICE_ID'] if mapping else 'MO'}'}});
                                            </script>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            '''}
                        </div>
                    </div>
                    <div class="bg-gray-50 px-8 py-6 flex flex-row-reverse space-x-reverse space-x-3">
                        <button type="submit" class="w-full sm:w-auto bg-blue-600 hover:bg-blue-700 text-white px-10 py-3 rounded-xl font-bold shadow-lg shadow-blue-200 transition-all">
                            Save Configuration
                        </button>
                        <button type="button" hx-on:click="document.getElementById('modal').remove()" class="w-full sm:w-auto px-6 py-3 bg-white border border-gray-200 text-gray-600 rounded-xl font-bold hover:bg-gray-100 transition-all">
                            Cancel
                        </button>
                    </div>
                </form>
            </div>
        </div>
        <script>
            function toggleCarrierFields(mode) {{
                const fields = ['DEFAULT', 'BPARTY', 'MSRN', 'TENANT'];
                fields.forEach(f => {{
                    const el = document.getElementById('field-' + f);
                    if (f === mode) {{
                        el.classList.remove('hidden');
                    }} else {{
                        el.classList.add('hidden');
                    }}
                }});
            }}
        </script>
    </div>
    """

def rule_details_partial(rule_id):
    if not rule_id:
        return '<span class="text-xs text-blue-400 italic">Select a rule to preview details</span>'
    
    r = db.get_rule_details(rule_id)
    if not r:
        return '<span class="text-xs text-red-500">Error: Rule details not found</span>'

    mapping_info = f"""
    <div class="mt-2 grid grid-cols-2 gap-x-4 gap-y-2">
        <div>
            <label class="block text-[10px] font-bold text-blue-600 uppercase mb-0.5">Default Carrier List</label>
            <p class="font-mono text-xs text-gray-900">{r['DEFAULT_CARRIER_LIST_ID']}</p>
        </div>
        <div>
            <label class="block text-[10px] font-bold text-blue-600 uppercase mb-0.5">B-Party Mapping</label>
            <p class="font-mono text-xs text-gray-900">{r['B_PARTY_CARRIER_MAPPING_ID']}</p>
        </div>
        <div>
            <label class="block text-[10px] font-bold text-blue-600 uppercase mb-0.5">MSRN Mapping</label>
            <p class="font-mono text-xs text-gray-900">{r['MSRN_CARRIER_MAPPING_ID']}</p>
        </div>
        <div>
            <label class="block text-[10px] font-bold text-blue-600 uppercase mb-0.5">Tenant Carrier Mapping</label>
            <p class="font-mono text-xs text-gray-900">{r['TENANT_CARRIER_MAPPING_ID']}</p>
        </div>
    </div>
    """

    rec_status = "ENABLED" if r['RECORDING_FLAG'] else "DISABLED"
    rec_color = "text-red-600" if r['RECORDING_FLAG'] else "text-gray-400"

    return f"""
    <div class="w-full text-left">
        <div class="flex justify-between items-start">
            <div class="flex-1">
                <p class="text-xs font-bold text-gray-400 uppercase mb-2">Master Rule Details</p>
                <p class="text-sm font-bold text-gray-900">{r['DESCRIPTION']}</p>
                <div class="mt-1 flex items-center space-x-3">
                    <span class="text-[10px] font-bold px-1.5 py-0.5 rounded bg-green-50 text-green-700 uppercase">{r['RULE_ACTION']}</span>
                    <span class="text-[10px] font-bold px-1.5 py-0.5 rounded bg-blue-100 text-blue-700 uppercase">{r['CARRIER_SEARCH_MODE']}</span>
                    <span class="text-[10px] font-bold flex items-center {rec_color}">
                        <i class="fa-solid fa-microphone-lines mr-1 text-xs"></i> REC: {rec_status}
                    </span>
                </div>
                {mapping_info}
            </div>
        </div>
    </div>
    """

# --- ROUTES ---

@app.route("/")
def root():
    from flask import redirect
    return redirect("/tenants")

@app.route("/dashboard")
def index():
    content = '<div class="flex flex-col items-center justify-center h-full text-gray-400 italic">Dashboard content coming soon...</div>'
    if request.headers.get('HX-Request'):
        return content
    return layout(content, "Dashboard | SIP Portal", active_sidebar="dashboard")

@app.route("/tenants")
def tenants():
    search = request.args.get('search', '')
    page = int(request.args.get('page', 1))
    
    if request.headers.get('HX-Request'):
        # If it's a pagination or search trigger for just the table
        if request.headers.get('HX-Target') == 'tenant-table-container':
            return tenant_table_partial(search, page)
        return tenant_list_content(search, page)
    
    return layout(tenant_list_content(search, page), "Tenants | SIP Portal", active_sidebar="tenants")

@app.route("/tenant/<tenant_id>")
def tenant_details(tenant_id):
    if request.headers.get('HX-Request'):
        return tenant_details_content(tenant_id)
    return layout(tenant_details_content(tenant_id), f"Tenant {tenant_id}", active_sidebar="tenants")

@app.route("/tenant/<tenant_id>/sip-rules")
def tenant_sip_rules(tenant_id):
    return sip_rules_partial(tenant_id)

@app.route("/tenant/<tenant_id>/sip-rule/add")
def tenant_sip_rule_add_modal(tenant_id):
    mode = request.args.get('mode', 'new')
    return sip_rule_modal(tenant_id, mode=mode)

@app.route("/rule/details/partial")
def rule_details_route():
    rule_id = request.args.get('rule_id')
    return rule_details_partial(rule_id)

@app.route("/tenant/<tenant_id>/sip-rule/edit/<mapping_id>")
def tenant_sip_rule_edit_modal(tenant_id, mapping_id):
    print(f"Route Hit: Edit Modal for {mapping_id}")
    return sip_rule_modal(tenant_id, mode="existing", mapping_id=int(mapping_id))

@app.route("/sip-rule/update/<mapping_id>", methods=['POST'])
def tenant_sip_rule_update(mapping_id):
    tenant_id = request.args.get('tenant_id')
    rule_id = int(request.form.get('rule_id')) if request.form.get('rule_id') else None
    description = request.form.get('mapping_description')
    call_type = request.form.get('call_type')
    service_id = int(request.form.get('service_id')) if request.form.get('service_id') else None
    
    print(f"Updating Rule: {mapping_id}, RuleID: {rule_id}, Desc: {description}, Tenant: {tenant_id}")
    
    success, error = db.update_sip_rule(int(mapping_id), rule_id, description, call_type, service_id)
    if not success: print(f"Update failed: {error}")
    
    if success:
        from flask import make_response
        resp = make_response(sip_rules_partial(tenant_id) + '<script>document.getElementById("modal")?.remove();</script>')
        resp.headers['X-Toast-Message'] = 'SIP Rule updated successfully'
        return resp
    else:
        return sip_rule_modal(tenant_id, error=error, mode="existing", mapping_id=mapping_id)

@app.route("/tenant/<tenant_id>/sip-rule", methods=['POST'])
def tenant_sip_rule_add(tenant_id):
    form_mode = request.form.get('form_mode')
    
    if form_mode == "new":
        rule_data = {
            'description': request.form.get('master_description'),
            'mapping_desc': request.form.get('mapping_description'),
            'rule_action': 'ALLOW',
            'carrier_search_mode': request.form.get('carrier_search_mode'),
            'b_party_id': request.form.get('b_party_id', '0'),
            'msrn_id': request.form.get('msrn_id', '0'),
            'tenant_carrier_id': request.form.get('tenant_carrier_id', '0'),
            'default_cl_id': request.form.get('default_cl_id', '0'),
            'recording_flag': 1 if request.form.get('recording_flag_toggle') == 'on' else 0
        }
        success, error = db.create_and_map_rule(tenant_id, rule_data, request.form.get('call_type'), request.form.get('service_id'))
    else:
        rule_id = request.form.get('rule_id')
        description = request.form.get('mapping_description')
        success, error = db.add_sip_rule(tenant_id, rule_id, request.form.get('call_type'), request.form.get('service_id'), description)
    
    if success:
        from flask import make_response
        resp = make_response(sip_rules_partial(tenant_id) + '<script>document.getElementById("modal")?.remove();</script>')
        resp.headers['X-Toast-Message'] = 'SIP Rule added successfully'
        return resp
    else:
        return sip_rule_modal(tenant_id, error=error, mode=form_mode)

@app.route("/sip-rule/<mapping_id>", methods=['DELETE'])
def tenant_sip_rule_delete(mapping_id):
    tenant_id = request.args.get('tenant_id')
    db.delete_sip_rule(mapping_id)
    return sip_rules_partial(tenant_id)

@app.route("/rules")
@app.route("/services")
@app.route("/logs")
@app.route("/tenant/<tenant_id>/services")
@app.route("/tenant/<tenant_id>/logs")
def coming_soon(tenant_id=None):
    path = request.path
    active = "tenants"
    if "/rules" in path: active = "rules"
    elif "/services" in path: active = "services"
    elif "/logs" in path: active = "logs"
    
    content = f'<div class="p-12 text-center text-gray-500 italic">This module is currently under development.</div>'
    if request.headers.get('HX-Request'):
        return content
    return layout(content, active_sidebar=active)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
