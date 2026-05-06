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
    </style>
</head>
<body class="bg-gray-50 text-gray-900 font-sans antialiased">
    <div class="flex h-screen overflow-hidden">
        {sidebar(active_sidebar)}
        <main id="main-content" class="flex-1 overflow-y-auto p-8">
            {content}
        </main>
    </div>
    <div id="dialog-container"></div>
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

                <div class="bg-blue-600 rounded-xl shadow-lg p-6 text-white overflow-hidden relative">
                    <div class="relative z-10">
                        <h4 class="font-bold text-lg mb-2">System Health</h4>
                        <p class="text-blue-100 text-sm mb-4">Real-time status for this tenant's SIP endpoints.</p>
                        <div class="flex items-center space-x-2">
                            <span class="w-2 h-2 rounded-full bg-green-400 animate-pulse"></span>
                            <span class="text-xs font-medium">99.9% Uptime</span>
                        </div>
                    </div>
                    <i class="fa-solid fa-chart-line absolute -right-4 -bottom-4 text-8xl text-blue-500 opacity-20"></i>
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
                <p class="text-[10px] text-gray-400 mt-0.5">Master: {r['MASTER_DESC']}</p>
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
            <td class="px-6 py-4 text-right">
                <button hx-delete="/sip-rule/{r['MAPPING_ID']}?tenant_id={tenant_id}" hx-target="#tab-content" hx-confirm="Are you sure you want to remove this rule mapping?"
                        class="text-gray-400 hover:text-red-500 p-2 rounded-lg hover:bg-red-50 transition-all">
                    <i class="fa-solid fa-trash-can"></i>
                </button>
            </td>
        </tr>
        """

    if not rules:
        rows = '<tr><td colspan="5" class="px-6 py-20 text-center text-gray-500">No SIP rules configured for this tenant.</td></tr>'

    return f"""
    <div id="sip-rule-table-wrapper" class="flex flex-col h-full">
        <div class="flex justify-between items-center p-6 bg-white sticky top-0">
            <h4 class="font-bold text-gray-900">Tenant Routing Rules</h4>
            <button hx-get="/tenant/{tenant_id}/sip-rule/add" hx-target="#dialog-container" 
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

def sip_rule_modal(tenant_id, error=None, mode="new"):
    rules = db.get_all_rules()
    services = db.get_all_services()
    
    rule_options = '<option value="">-- Select Existing Rule --</option>'
    for r in rules:
        rule_options += f'<option value="{r["RULE_ID"]}">{r["RULE_ID"]} - {r["DESCRIPTION"]}</option>'
    
    svc_options = ""
    for s in services:
        svc_options += f'<option value="{s["SERVICE_ID"]}">{s["SERVICE_TYPE"]}</option>'

    error_alert = ""
    if error:
        error_alert = f"""
        <div class="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center text-red-700 text-xs">
            <i class="fa-solid fa-triangle-exclamation mr-2 text-base"></i>
            {error}
        </div>
        """

    is_new = mode == "new"
    
    return f"""
    <div id="modal" class="fixed inset-0 z-50 overflow-y-auto" aria-labelledby="modal-title" role="dialog" aria-modal="true">
        <div class="flex items-center justify-center min-h-screen px-4 pt-4 pb-20 text-center sm:block sm:p-0">
            <div class="fixed inset-0 transition-opacity bg-black/40 backdrop-blur-sm" hx-on:click="document.getElementById('modal').remove()"></div>
            <span class="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">&#8203;</span>

            <div class="inline-block align-bottom bg-white rounded-2xl text-left overflow-hidden shadow-2xl transform transition-all sm:my-8 sm:align-middle sm:max-w-2xl sm:w-full">
                <form hx-post="/tenant/{tenant_id}/sip-rule" hx-target="#sip-rule-table-wrapper" hx-swap="outerHTML">
                    <div class="bg-white px-8 pt-8 pb-4">
                        <div class="flex justify-between items-center mb-6">
                            <h3 class="text-xl font-bold text-gray-900">Add SIP Routing Rule</h3>
                            <button type="button" hx-on:click="document.getElementById('modal').remove()" class="text-gray-400 hover:text-gray-500">
                                <i class="fa-solid fa-xmark text-xl"></i>
                            </button>
                        </div>
                        
                        {error_alert}

                        <div class="flex p-1 bg-gray-100 rounded-xl mb-6">
                            <button type="button" hx-get="/tenant/{tenant_id}/sip-rule/add?mode=new" hx-target="#modal" hx-swap="outerHTML"
                                    class="flex-1 py-2 text-sm font-bold rounded-lg transition-all {'bg-white shadow text-blue-600' if is_new else 'text-gray-500 hover:text-gray-700'}">
                                Create New Rule
                            </button>
                            <button type="button" hx-get="/tenant/{tenant_id}/sip-rule/add?mode=existing" hx-target="#modal" hx-swap="outerHTML"
                                    class="flex-1 py-2 text-sm font-bold rounded-lg transition-all {'bg-white shadow text-blue-600' if not is_new else 'text-gray-500 hover:text-gray-700'}">
                                Select Existing
                            </button>
                        </div>

                        <input type="hidden" name="form_mode" value="{mode}">

                        <div class="space-y-4">
                            {f'''
                            <div class="grid grid-cols-2 gap-4">
                                <div>
                                    <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Rule ID</label>
                                    <input type="text" name="rule_id" placeholder="e.g. 3014" required
                                           class="w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:bg-white transition-all text-sm">
                                </div>
                                <div>
                                    <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Rule Action</label>
                                    <select name="rule_action" class="w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:bg-white transition-all text-sm">
                                        <option value="ALLOW">ALLOW</option>
                                        <option value="DENY">DENY</option>
                                    </select>
                                </div>
                            </div>
                            <div>
                                <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Mapping Description</label>
                                <input type="text" name="description" placeholder="e.g. TATA MO OFFNET ROUTING" required
                                       class="w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:bg-white transition-all text-sm">
                            </div>
                            <div class="grid grid-cols-2 gap-4">
                                <div>
                                    <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Carrier Search Mode</label>
                                    <select name="carrier_search_mode" 
                                            class="w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:bg-white transition-all text-sm">
                                        <option value="DEFAULT">DEFAULT</option>
                                        <option value="BPARTY">BPARTY</option>
                                        <option value="MSRN">MSRN</option>
                                    </select>
                                </div>
                                <div>
                                    <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Recording Flag</label>
                                    <select name="recording_flag" class="w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:bg-white transition-all text-sm">
                                        <option value="0">Disabled (0)</option>
                                        <option value="1">Enabled (1)</option>
                                    </select>
                                </div>
                            </div>
                            <div id="dynamic-input-fields" class="grid grid-cols-2 gap-4 pt-2">
                                <div>
                                    <label class="block text-[10px] font-bold text-blue-600 uppercase mb-1">Default Carrier List ID</label>
                                    <input type="text" name="default_cl_id" placeholder="0" class="w-full px-3 py-2 bg-blue-50/30 border border-blue-100 rounded-lg text-sm">
                                </div>
                                <div>
                                    <label class="block text-[10px] font-bold text-blue-600 uppercase mb-1">B-Party Mapping ID</label>
                                    <input type="text" name="b_party_id" placeholder="0" class="w-full px-3 py-2 bg-blue-50/30 border border-blue-100 rounded-lg text-sm">
                                </div>
                                <div>
                                    <label class="block text-[10px] font-bold text-blue-600 uppercase mb-1">MSRN Mapping ID</label>
                                    <input type="text" name="msrn_id" placeholder="0" class="w-full px-3 py-2 bg-blue-50/30 border border-blue-100 rounded-lg text-sm">
                                </div>
                                <div>
                                    <label class="block text-[10px] font-bold text-blue-600 uppercase mb-1">Tenant Carrier Mapping ID</label>
                                    <input type="text" name="tenant_carrier_id" placeholder="0" class="w-full px-3 py-2 bg-blue-50/30 border border-blue-100 rounded-lg text-sm">
                                </div>
                            </div>
                            ''' if is_new else f'''
                            <div>
                                <label class="block text-sm font-bold text-gray-700 mb-2">Select Rule Master</label>
                                <select name="rule_id" required
                                        hx-get="/rule/details/partial" hx-target="#dynamic-details-view" hx-trigger="change"
                                        class="block w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:bg-white transition-all">
                                    {rule_options}
                                </select>
                            </div>
                            <div>
                                <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Mapping Description</label>
                                <input type="text" name="description" placeholder="e.g. TATA MO OFFNET ROUTING" required
                                       class="w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:bg-white transition-all text-sm">
                            </div>
                            <div id="dynamic-details-view" class="p-4 bg-blue-50/50 rounded-xl border border-blue-100 min-h-[80px] flex items-center justify-center">
                                <span class="text-xs text-blue-400 italic">Select a rule to preview details</span>
                            </div>
                            '''}

                            <div class="grid grid-cols-2 gap-4 pt-4 border-t border-gray-100">
                                <div>
                                    <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Call Type</label>
                                    <select name="call_type" class="block w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm">
                                        <option value="ONNET">ONNET</option>
                                        <option value="OFFNET">OFFNET</option>
                                        <option value="ALLCALL">ALLCALL</option>
                                    </select>
                                </div>
                                <div>
                                    <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Service</label>
                                    <select name="service_id" class="block w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm">
                                        {svc_options}
                                    </select>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="bg-gray-50 px-8 py-6 flex flex-row-reverse space-x-reverse space-x-3">
                        <button type="submit" class="w-full sm:w-auto bg-blue-600 hover:bg-blue-700 text-white px-8 py-3 rounded-xl font-bold shadow-lg shadow-blue-200 transition-all">
                            Save Rule Mapping
                        </button>
                        <button type="button" hx-on:click="document.getElementById('modal').remove()" class="w-full sm:w-auto px-6 py-3 bg-white border border-gray-200 text-gray-600 rounded-xl font-bold hover:bg-gray-100 transition-all">
                            Cancel
                        </button>
                    </div>
                </form>
            </div>
        </div>
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

@app.route("/tenant/<tenant_id>/sip-rule", methods=['POST'])
def tenant_sip_rule_add(tenant_id):
    form_mode = request.form.get('form_mode')
    
    if form_mode == "new":
        rule_data = {
            'rule_id': request.form.get('rule_id'),
            'description': request.form.get('description'), # This is both master and mapping desc for new rules
            'mapping_desc': request.form.get('description'),
            'rule_action': request.form.get('rule_action'),
            'carrier_search_mode': request.form.get('carrier_search_mode'),
            'b_party_id': request.form.get('b_party_id', '0'),
            'msrn_id': request.form.get('msrn_id', '0'),
            'tenant_carrier_id': request.form.get('tenant_carrier_id', '0'),
            'default_cl_id': request.form.get('default_cl_id', '0'),
            'recording_flag': int(request.form.get('recording_flag', 0))
        }
        success, error = db.create_and_map_rule(tenant_id, rule_data, request.form.get('call_type'), request.form.get('service_id'))
    else:
        rule_id = request.form.get('rule_id')
        description = request.form.get('description')
        success, error = db.add_sip_rule(tenant_id, rule_id, request.form.get('call_type'), request.form.get('service_id'), description)
    
    if success:
        return sip_rules_partial(tenant_id) + '<script>document.getElementById("modal")?.remove();</script>'
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
